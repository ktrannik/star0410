import asyncio
import re
import random
import json
import os
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# ==========================================
# НАСТРОЙКИ (БЕРУТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ)
# ==========================================
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
MY_USER_ID = int(os.getenv("MY_USER_ID", 0))

# === ЕЖЕДНЕВКА: ВРЕМЯ ИЗ ПЕРЕМЕННОЙ ОКРУЖЕНИЯ ===
DAILY_TIME = os.getenv("DAILY_TIME", "12:55")  # формат ЧЧ:ММ
# ==========================================

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# === ФУНКЦИЯ НАЖАТИЯ КНОПКИ ===
async def click_button(chat_id, button_text):
    async for msg in client.iter_messages(chat_id, limit=10):
        if msg.buttons:
            for row in msg.buttons:
                for button in row:
                    if button_text.lower() in button.text.lower():
                        await button.click()
                        return True
    return False

# === УНИВЕРСАЛЬНАЯ ПРОВЕРКА ЭМОДЗИ-КАПЧИ ===
async def solve_emoji_captcha(bot_name):
    emoji_map = {
        'вишн': '🍒', 'яблок': '🍎', 'виноград': '🍇', 'клубник': '🍓',
        'арбуз': '🍉', 'кокос': '🥥', 'ананас': '🍍', 'банан': '🍌',
        'киви': '🥝', 'апельсин': '🍊', 'лимон': '🍋', 'груш': '🍐',
        'персик': '🍑', 'черешн': '🍒', 'малин': '🍇', 'черник': '🫐',
        'ежевик': '🫐',
    }
    try:
        async for msg in client.iter_messages(bot_name, limit=5):
            if msg.text:
                text_lower = msg.text.lower()
                for keyword, emoji in emoji_map.items():
                    if keyword in text_lower:
                        print(f"   🎯 Эмодзи-капча: '{keyword}' → жму {emoji}")
                        await click_button(bot_name, emoji)
                        await asyncio.sleep(1)
                        return True
    except Exception as e:
        print(f"   ⚠️ Ошибка в solve_emoji_captcha: {e}")
    return False

# === ОТЛОЖЕННОЕ ВЫПОЛНЕНИЕ .DAILY ===
async def schedule_daily(bot_name, reply_chat_id, delay):
    await asyncio.sleep(delay)
    daily_buttons = ["Забрать", "Получить", "Ежедневка", "Забрать награду", "Claim", "Daily", "Получить награду"]
    clicked = False
    for btn in daily_buttons:
        if await click_button(bot_name, btn):
            clicked = True
            break
    if not clicked:
        return
    await asyncio.sleep(3)
    async for msg in client.iter_messages(bot_name, limit=10):
        if msg.text and ('+' in msg.text or '-' in msg.text or '×' in msg.text or '÷' in msg.text):
            match_expr = re.search(r'(\d+)\s*([+\-×÷])\s*(\d+)\s*[=？?]', msg.text)
            if match_expr:
                num1 = int(match_expr.group(1))
                operator = match_expr.group(2)
                num2 = int(match_expr.group(3))
                if operator == '+': answer = num1 + num2
                elif operator == '-': answer = num1 - num2
                elif operator == '×': answer = num1 * num2
                elif operator == '÷': answer = num1 / num2; answer = round(answer) if isinstance(answer, float) else answer
                await click_button(bot_name, str(answer))
                break

# === ФАЙЛ ДЛЯ ХРАНЕНИЯ ЗАДЕРЖКИ ===
DELAY_FILE = "daily_delay.json"

def get_daily_delay():
    if os.path.exists(DELAY_FILE):
        with open(DELAY_FILE, 'r') as f:
            data = json.load(f)
            return data.get('delay_seconds', 0)
    return 0

def save_daily_delay(delay):
    with open(DELAY_FILE, 'w') as f:
        json.dump({'delay_seconds': delay}, f)

# === АВТОМАТИЧЕСКАЯ ЕЖЕДНЕВКА ===
async def auto_daily():
    MSK = timezone(timedelta(hours=3))
    bot_name = "@patrickstarsrobot"
    
    try:
        daily_hour, daily_minute = map(int, DAILY_TIME.split(':'))
    except Exception:
        daily_hour, daily_minute = 12, 55
        print(f"⚠️ Неверный формат DAILY_TIME='{DAILY_TIME}', использую 12:55")
    
    while True:
        current_delay = get_daily_delay()
        now = datetime.now(MSK)
        base_target = now.replace(hour=daily_hour, minute=daily_minute, second=0, microsecond=0)
        if now > base_target:
            base_target += timedelta(days=1)
        target = base_target + timedelta(seconds=current_delay)
        if current_delay > 300:
            current_delay = 0
            save_daily_delay(0)
            target = base_target
            print("🔄 Задержка сброшена (превышен лимит 5 минут)")
        delay = (target - now).total_seconds()
        if delay < 0:
            delay += timedelta(days=1).total_seconds()
        print(f"⏳ Следующий запуск daily через {delay//3600:.0f}ч {delay%3600//60:.0f}м {delay%60:.0f}с (задержка: {current_delay}с, время: {daily_hour:02d}:{daily_minute:02d})")
        await asyncio.sleep(delay)
        print("🎁 Запуск автоматической ежедневки...")
        try:
            await client.send_message(bot_name, "/start")
            await asyncio.sleep(3)
            await solve_emoji_captcha(bot_name)
            await asyncio.sleep(1)
            if not await click_button(bot_name, "Профиль"):
                await asyncio.sleep(2)
                await click_button(bot_name, "Профиль")
            await asyncio.sleep(1)
            if not await click_button(bot_name, "Ежедневка"):
                await asyncio.sleep(2)
                await click_button(bot_name, "Ежедневка")
            await asyncio.sleep(3)
            math_found = False
            async for msg in client.iter_messages(bot_name, limit=10):
                if msg.text and ('+' in msg.text or '-' in msg.text or '×' in msg.text or '÷' in msg.text):
                    match_expr = re.search(r'(\d+)\s*([+\-×÷])\s*(\d+)\s*[=？?]', msg.text)
                    if match_expr:
                        num1 = int(match_expr.group(1))
                        operator = match_expr.group(2)
                        num2 = int(match_expr.group(3))
                        if operator == '+': answer = num1 + num2
                        elif operator == '-': answer = num1 - num2
                        elif operator == '×': answer = num1 * num2
                        elif operator == '÷': answer = num1 / num2; answer = round(answer) if isinstance(answer, float) else answer
                        await click_button(bot_name, str(answer))
                        math_found = True
                        break
            if math_found:
                new_delay = current_delay + 10
                save_daily_delay(new_delay)
                print(f"   ⏳ Новая задержка: {new_delay} секунд")
            else:
                print("   ⚠️ Капча не решена, задержка не меняется")
        except Exception as e:
            print(f"   ❌ Ошибка авто-daily: {e}")

# === ОБРАБОТКА ЗАДАНИЙ ДЛЯ ПРОМОКОДА ===
async def process_promo_tasks(bot_name, promo_code):
    await client.send_message(bot_name, promo_code)
    await asyncio.sleep(3)
    await solve_emoji_captcha(bot_name)
    await asyncio.sleep(1)
    tasks_found = False
    async for msg in client.iter_messages(bot_name, limit=5):
        if msg.text and ('подпишись' in msg.text.lower() or 'запусти' in msg.text.lower() or 'выполни' in msg.text.lower()):
            tasks_found = True
            break
        if msg.buttons:
            for row in msg.buttons:
                for button in row:
                    if 'подписаться' in button.text.lower() or 'запустить' in button.text.lower():
                        tasks_found = True
                        break
                if tasks_found:
                    break
        if tasks_found:
            break
    if not tasks_found:
        print(f"   ✅ Промокод {promo_code} успешно введён!")
        return True
    print(f"   🔍 Обнаружены задания для промокода {promo_code}. Выполняю...")
    tasks_done = 0
    async for msg in client.iter_messages(bot_name, limit=5):
        if msg.buttons:
            for row in msg.buttons:
                for button in row:
                    if 'подписаться' in button.text.lower() and button.url:
                        try:
                            if '/joinchat/' in button.url or '/+' in button.url:
                                invite_hash = button.url.split('/')[-1]
                                if invite_hash.startswith('+'):
                                    invite_hash = invite_hash[1:]
                                await client(ImportChatInviteRequest(invite_hash))
                            else:
                                channel_username = button.url.split('/')[-1]
                                await client(JoinChannelRequest(channel_username))
                            tasks_done += 1
                            print(f"      ✅ Подписался: {button.url}")
                            await asyncio.sleep(2)
                        except Exception as e:
                            print(f"      ⚠️ Ошибка подписки: {e}")
                    elif 'запустить' in button.text.lower() and button.url:
                        try:
                            if '?start=' in button.url:
                                bot_username = button.url.split('/')[-1].split('?')[0]
                                start_param = button.url.split('?start=')[-1]
                                await client.send_message(bot_username, f"/start {start_param}")
                            else:
                                bot_username = button.url.split('/')[-1]
                                await client.send_message(bot_username, "/start")
                            tasks_done += 1
                            print(f"      ✅ Запустил бота: {button.url}")
                            await asyncio.sleep(2)
                        except Exception as e:
                            print(f"      ⚠️ Ошибка запуска бота: {e}")
    if tasks_done == 0:
        print(f"   ⚠️ Не найдено кнопок для выполнения")
        return False
    await asyncio.sleep(2)
    if await click_button(bot_name, "Выполнил"):
        print(f"   ✅ Нажата кнопка 'Выполнил'")
    elif await click_button(bot_name, "Я выполнил"):
        print(f"   ✅ Нажата кнопка 'Я выполнил'")
    else:
        print(f"   ⚠️ Кнопка 'Выполнил' не найдена")
    await asyncio.sleep(3)
    await solve_emoji_captcha(bot_name)
    await asyncio.sleep(1)
    await client.send_message(bot_name, promo_code)
    await asyncio.sleep(3)
    success = False
    async for msg in client.iter_messages(bot_name, limit=3):
        if msg.text and ('принят' in msg.text.lower() or 'активирован' in msg.text.lower() or 'успешно' in msg.text.lower()):
            success = True
            break
    if success:
        print(f"   ✅ Промокод {promo_code} активирован после заданий!")
    else:
        print(f"   ⚠️ Промокод {promo_code} не активирован")
    return success

# === АВТОМАТИЧЕСКИЙ ПАРСИНГ И АКТИВАЦИЯ ПРОМО ===
async def auto_parse_and_activate():
    MSK = timezone(timedelta(hours=3))
    bot_name = "@patrickstarsrobot"
    channel = "@patrickstarsfarm"
    while True:
        try:
            now = datetime.now(MSK)
            target1 = now.replace(hour=15, minute=30, second=0, microsecond=0)
            if now > target1:
                target1 += timedelta(days=1)
            delay1 = (target1 - now).total_seconds()
            print(f"⏳ Первая проверка через {delay1//3600:.0f}ч {delay1%3600//60:.0f}м")
            await asyncio.sleep(delay1)
            print(f"🔍 Первая проверка: сканирую канал {channel}...")
            promo_found = None
            today = datetime.now(MSK).date()
            attempt = 0
            max_attempts = 90
            while attempt < max_attempts and promo_found is None:
                attempt += 1
                try:
                    async for msg in client.iter_messages(channel, limit=15):
                        msg_date = msg.date.astimezone(MSK)
                        content = msg.text or msg.caption or ''
                        if not content: continue
                        if msg_date.date() != today: continue
                        match = re.search(r':\s*([a-zA-Z][a-zA-Z0-9\-_]+)(?=\s|$)', content)
                        if match:
                            promo_found = match.group(1)
                            print(f"   ✅ Найдено промо: {promo_found}")
                            break
                    if promo_found: break
                    await asyncio.sleep(10)
                except Exception as e:
                    print(f"   ⚠️ Ошибка: {e}")
                    await asyncio.sleep(10)
            if promo_found:
                try:
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(2)
                    if not await click_button(bot_name, "Профиль"):
                        print(f"   ⚠️ Кнопка 'Профиль' не найдена")
                        continue
                    await asyncio.sleep(1)
                    if not await click_button(bot_name, "Промокод"):
                        print(f"   ⚠️ Кнопка 'Промокод' не найдена")
                        continue
                    await asyncio.sleep(1)
                    success = await process_promo_tasks(bot_name, promo_found)
                    if success:
                        print(f"   ✅ Промокод {promo_found} активирован!")
                    else:
                        print(f"   ❌ Не удалось активировать промокод {promo_found}")
                except Exception as e:
                    print(f"   ❌ Ошибка активации: {e}")
            else:
                print(f"❌ Промо не найден (первая проверка, попыток: {attempt})")
            
            now = datetime.now(MSK)
            target2 = now.replace(hour=16, minute=30, second=0, microsecond=0)
            if now > target2:
                target2 += timedelta(days=1)
            delay2 = (target2 - now).total_seconds()
            print(f"⏳ Вторая проверка через {delay2//3600:.0f}ч {delay2%3600//60:.0f}м")
            await asyncio.sleep(delay2)
            print(f"🔍 Вторая проверка: сканирую канал {channel}...")
            promo_found = None
            today = datetime.now(MSK).date()
            attempt = 0
            while attempt < max_attempts and promo_found is None:
                attempt += 1
                try:
                    async for msg in client.iter_messages(channel, limit=15):
                        msg_date = msg.date.astimezone(MSK)
                        content = msg.text or msg.caption or ''
                        if not content: continue
                        if msg_date.date() != today: continue
                        match = re.search(r':\s*([a-zA-Z][a-zA-Z0-9\-_]+)(?=\s|$)', content)
                        if match:
                            promo_found = match.group(1)
                            print(f"   ✅ Найдено промо: {promo_found}")
                            break
                    if promo_found: break
                    await asyncio.sleep(10)
                except Exception as e:
                    print(f"   ⚠️ Ошибка: {e}")
                    await asyncio.sleep(10)
            if promo_found:
                try:
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(2)
                    if not await click_button(bot_name, "Профиль"):
                        print(f"   ⚠️ Кнопка 'Профиль' не найдена")
                        continue
                    await asyncio.sleep(1)
                    if not await click_button(bot_name, "Промокод"):
                        print(f"   ⚠️ Кнопка 'Промокод' не найдена")
                        continue
                    await asyncio.sleep(1)
                    success = await process_promo_tasks(bot_name, promo_found)
                    if success:
                        print(f"   ✅ Промокод {promo_found} активирован!")
                    else:
                        print(f"   ❌ Не удалось активировать промокод {promo_found}")
                except Exception as e:
                    print(f"   ❌ Ошибка активации: {e}")
            else:
                print(f"❌ Промо не найден (вторая проверка, попыток: {attempt})")
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            await asyncio.sleep(60)

# === ВЫПОЛНЕНИЕ ЗАДАНИЙ ДЛЯ ОДНОГО БОТА (ФОНОВАЯ) ===
async def execute_tasks_once(bot_name, current_success, max_success):
    from telethon.errors import FloodWaitError
    processed_messages = set()
    local_success = 0
    failed_attempts = 0
    total_attempts = 0
    max_attempts = 30
    max_tasks = max_success - current_success
    webapp_skipped = 0
    try:
        await client.send_message(bot_name, "/start")
        await asyncio.sleep(3)
        await solve_emoji_captcha(bot_name)
        await asyncio.sleep(1)
        if not await click_button(bot_name, "Задания"):
            print(f"❌ Кнопка 'Задания' не найдена")
            return current_success + local_success
        print(f"✅ Нажата кнопка: Задания")
        await asyncio.sleep(3)
        await solve_emoji_captcha(bot_name)
        await asyncio.sleep(1)
        print(f"✅ Иду в цикл выполнения заданий...")
        while local_success < max_tasks and total_attempts < max_attempts:
            total_attempts += 1
            print(f"🔄 Попытка {total_attempts} (успешно: {local_success})...")
            invite_url = None
            current_msg_id = None
            async for msg in client.iter_messages(bot_name, limit=5):
                if msg.buttons:
                    for row in msg.buttons:
                        for button in row:
                            if ('перейти' in button.text.lower() or 'выполнить' in button.text.lower() or 'подписаться' in button.text.lower() or 'запустить' in button.text.lower() or 'открыть' in button.text.lower()) and button.url:
                                invite_url = button.url
                                current_msg_id = msg.id
                                break
                    if invite_url: break
            if not invite_url:
                failed_attempts += 1
                print(f"   ⚠️ Ссылка не читается ({failed_attempts}/5)")
                await client.send_message(bot_name, "/start")
                await asyncio.sleep(2)
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(3)
                if failed_attempts >= 5: break
                continue
            if current_msg_id in processed_messages:
                await asyncio.sleep(1)
                continue
            else:
                processed_messages.add(current_msg_id)
            failed_attempts = 0
            url_lower = invite_url.lower()
            is_webapp = False
            if any(marker in url_lower for marker in ['/app', '?startapp=', 'webapp', 'miniapp', '/web', 'tg://']):
                if '?start=' in url_lower and '/app' not in url_lower and 'webapp' not in url_lower:
                    is_webapp = False
                else:
                    is_webapp = True
            if is_webapp:
                webapp_skipped += 1
                print(f"   🌐 WebApp, пропускаю (всего: {webapp_skipped})")
                await client.send_message(bot_name, "/start")
                await asyncio.sleep(2)
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(3)
                continue
            clicked_subscribe = False
            for btn_text in ["Подписаться", "Запустить бота", "Запустить", "Перейти", "Выполнить", "Начать", "Открыть"]:
                if await click_button(bot_name, btn_text):
                    clicked_subscribe = True
                    print(f"   ✅ Нажата кнопка: {btn_text}")
                    break
            if not clicked_subscribe:
                failed_attempts += 1
                print(f"   ⚠️ Кнопка не найдена ({failed_attempts}/5)")
                if failed_attempts >= 5: break
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(3)
            await solve_emoji_captcha(bot_name)
            await asyncio.sleep(1)
            try:
                if '?start=' in invite_url or '&start=' in invite_url or '?startgroup=' in invite_url:
                    bot_username = None
                    match = re.search(r't\.me/([a-zA-Z0-9_]+)', invite_url)
                    if match: bot_username = match.group(1)
                    if not bot_username:
                        match = re.search(r'domain=([a-zA-Z0-9_]+)', invite_url)
                        if match: bot_username = match.group(1)
                    if not bot_username:
                        print(f"   ⚠️ Не удалось извлечь имя бота из {invite_url}")
                        await client.send_message(bot_name, "/start")
                        await asyncio.sleep(2)
                        await click_button(bot_name, "Пропустить")
                        await asyncio.sleep(3)
                        continue
                    if '?startgroup=' in invite_url: start_param = invite_url.split('?startgroup=')[-1].split('&')[0]
                    elif '?start=' in invite_url: start_param = invite_url.split('?start=')[-1].split('&')[0]
                    elif '&start=' in invite_url: start_param = invite_url.split('&start=')[-1].split('&')[0]
                    else: start_param = ""
                    print(f"   🤖 Отправляю /start {start_param} боту @{bot_username}")
                    await client.send_message(bot_username, f"/start {start_param}")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(random.randint(4, 7))
                elif '/joinchat/' in invite_url or '/+' in invite_url:
                    invite_hash = invite_url.split('/')[-1]
                    if invite_hash.startswith('+'): invite_hash = invite_hash[1:]
                    invite_hash = invite_hash.split('?')[0]
                    print(f"   📢 Подписка на приватный канал")
                    try:
                        await client(ImportChatInviteRequest(invite_hash))
                        print(f"   ✅ Подписался")
                    except FloodWaitError as e:
                        print(f"   ⏳ FloodWait: {e.seconds} сек")
                        await asyncio.sleep(e.seconds + 10)
                        continue
                    except Exception as e:
                        if 'successfully requested' in str(e).lower() or 'already in' in str(e).lower():
                            print(f"   ✅ Уже подписан")
                        else:
                            print(f"   ⚠️ Ошибка: {e}")
                            await client.send_message(bot_name, "/start")
                            await asyncio.sleep(2)
                            await click_button(bot_name, "Пропустить")
                            await asyncio.sleep(3)
                            continue
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(random.randint(4, 7))
                else:
                    channel_username = invite_url.split('/')[-1]
                    if '/' in channel_username: channel_username = channel_username.split('/')[0]
                    channel_username = channel_username.split('?')[0]
                    channel_username = channel_username.lstrip('@')
                    if not channel_username:
                        print(f"   ⚠️ Не удалось извлечь имя канала из {invite_url}")
                        await client.send_message(bot_name, "/start")
                        await asyncio.sleep(2)
                        await click_button(bot_name, "Пропустить")
                        await asyncio.sleep(3)
                        continue
                    print(f"   📢 Подписка на @{channel_username}")
                    try:
                        await client(JoinChannelRequest(channel_username))
                        print(f"   ✅ Подписался")
                    except FloodWaitError as e:
                        print(f"   ⏳ FloodWait: {e.seconds} сек")
                        await asyncio.sleep(e.seconds + 10)
                        continue
                    except Exception as e:
                        if 'already in' in str(e).lower() or 'successfully requested' in str(e).lower():
                            print(f"   ✅ Уже подписан")
                        else:
                            print(f"   ⚠️ Ошибка: {e}")
                            await client.send_message(bot_name, "/start")
                            await asyncio.sleep(2)
                            await click_button(bot_name, "Пропустить")
                            await asyncio.sleep(3)
                            continue
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(random.randint(4, 7))
            except FloodWaitError as e:
                print(f"   ⏳ FloodWait: {e.seconds} сек")
                await asyncio.sleep(e.seconds + 10)
                continue
            except Exception as e:
                print(f"   ⚠️ Ошибка обработки ссылки: {e}")
                await client.send_message(bot_name, "/start")
                await asyncio.sleep(2)
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(3)
                continue
            await solve_emoji_captcha(bot_name)
            await asyncio.sleep(1)
            clicked = False
            for btn_text in ["Проверить", "Подтвердить", "Я выполнил", "Выполнил", "Готово", "Проверка"]:
                if await click_button(bot_name, btn_text):
                    clicked = True
                    print(f"   ✅ Нажата кнопка: {btn_text}")
                    break
            if not clicked: print(f"   ⚠️ Кнопка проверки не найдена")
            await asyncio.sleep(3)
            task_done = False
            async for msg in client.iter_messages(bot_name, limit=5):
                if msg.text:
                    text_lower = msg.text.lower()
                    if 'задание выполнено' in text_lower or 'засчитано' in text_lower:
                        task_done = True
                        local_success += 1
                        print(f"   ✅ Задание выполнено! (всего: {local_success})")
                        break
                    elif 'не выполнено' in text_lower or 'не засчитано' in text_lower:
                        print(f"   ❌ Задание не выполнено")
                        break
            if not task_done:
                print(f"   ⏭ Пропускаю...")
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(2)
            await solve_emoji_captcha(bot_name)
            await asyncio.sleep(1)
            await asyncio.sleep(2)
        print(f"📊 {bot_name}: пропущено WebApp: {webapp_skipped}, выполнено: {local_success}")
    except Exception as e:
        print(f"❌ Ошибка для {bot_name}: {e}")
    return current_success + local_success

# === РУЧНОЙ ЗАПУСК ЗАДАНИЙ С ОТЛАДКОЙ ===
async def execute_tasks_manual(bot_name):
    from telethon.errors import FloodWaitError
    await client.send_message('me', f"🚀 РУЧНОЙ ЗАПУСК для {bot_name}...")
    processed_messages = set()
    local_success = 0
    failed_attempts = 0
    total_attempts = 0
    max_attempts = 30
    webapp_skipped = 0
    try:
        await client.send_message('me', "📨 Отправляю /start...")
        await client.send_message(bot_name, "/start")
        await asyncio.sleep(3)
        if await solve_emoji_captcha(bot_name): await client.send_message('me', "🎯 Эмодзи-капча решена")
        await asyncio.sleep(1)
        await client.send_message('me', "🔍 Ищу кнопку 'Задания'...")
        if not await click_button(bot_name, "Задания"):
            await client.send_message('me', "❌ Кнопка 'Задания' не найдена")
            return
        await client.send_message('me', "✅ Кнопка 'Задания' нажата")
        await asyncio.sleep(3)
        if await solve_emoji_captcha(bot_name): await client.send_message('me', "🎯 Эмодзи-капча решена")
        await asyncio.sleep(1)
        while total_attempts < max_attempts:
            total_attempts += 1
            await client.send_message('me', f"🔄 Попытка {total_attempts}/{max_attempts}...")
            invite_url = None
            current_msg_id = None
            async for msg in client.iter_messages(bot_name, limit=5):
                if msg.buttons:
                    for row in msg.buttons:
                        for button in row:
                            if ('перейти' in button.text.lower() or 'выполнить' in button.text.lower() or 'подписаться' in button.text.lower() or 'запустить' in button.text.lower() or 'открыть' in button.text.lower()) and button.url:
                                invite_url = button.url
                                current_msg_id = msg.id
                                break
                    if invite_url: break
            if not invite_url:
                failed_attempts += 1
                await client.send_message('me', f"⚠️ Ссылка не читается ({failed_attempts}/5)")
                await client.send_message(bot_name, "/start")
                await asyncio.sleep(2)
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(3)
                if failed_attempts >= 5:
                    await client.send_message('me', "⛔ 5 неудач подряд")
                    break
                continue
            if current_msg_id in processed_messages:
                await asyncio.sleep(1)
                continue
            else:
                processed_messages.add(current_msg_id)
            failed_attempts = 0
            await client.send_message('me', f"🔗 Ссылка: {invite_url}")
            url_lower = invite_url.lower()
            is_webapp = False
            if any(marker in url_lower for marker in ['/app', '?startapp=', 'webapp', 'miniapp', '/web', 'tg://']):
                if '?start=' in url_lower and '/app' not in url_lower and 'webapp' not in url_lower:
                    is_webapp = False
                else:
                    is_webapp = True
            if is_webapp:
                webapp_skipped += 1
                await client.send_message('me', f"🌐 WebApp, пропускаю (всего: {webapp_skipped})")
                await client.send_message(bot_name, "/start")
                await asyncio.sleep(2)
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(3)
                continue
            clicked_subscribe = False
            for btn_text in ["Подписаться", "Запустить бота", "Запустить", "Перейти", "Выполнить", "Начать", "Открыть"]:
                if await click_button(bot_name, btn_text):
                    clicked_subscribe = True
                    await client.send_message('me', f"✅ Нажата кнопка: {btn_text}")
                    break
            if not clicked_subscribe:
                failed_attempts += 1
                await client.send_message('me', f"⚠️ Кнопка не найдена ({failed_attempts}/5)")
                if failed_attempts >= 5: break
                await asyncio.sleep(1)
                continue
            await asyncio.sleep(3)
            if await solve_emoji_captcha(bot_name):
                await client.send_message('me', "🎯 Эмодзи-капча решена")
                await asyncio.sleep(1)
            try:
                if '?start=' in invite_url or '&start=' in invite_url or '?startgroup=' in invite_url:
                    bot_username = None
                    match = re.search(r't\.me/([a-zA-Z0-9_]+)', invite_url)
                    if match: bot_username = match.group(1)
                    if not bot_username:
                        match = re.search(r'domain=([a-zA-Z0-9_]+)', invite_url)
                        if match: bot_username = match.group(1)
                    if not bot_username:
                        await client.send_message('me', f"⚠️ Не удалось извлечь имя бота")
                        await client.send_message(bot_name, "/start")
                        await asyncio.sleep(2)
                        await click_button(bot_name, "Пропустить")
                        await asyncio.sleep(3)
                        continue
                    if '?startgroup=' in invite_url: start_param = invite_url.split('?startgroup=')[-1].split('&')[0]
                    elif '?start=' in invite_url: start_param = invite_url.split('?start=')[-1].split('&')[0]
                    elif '&start=' in invite_url: start_param = invite_url.split('&start=')[-1].split('&')[0]
                    else: start_param = ""
                    await client.send_message('me', f"🤖 Отправляю /start {start_param} боту @{bot_username}")
                    await client.send_message(bot_username, f"/start {start_param}")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(random.randint(4, 7))
                elif '/joinchat/' in invite_url or '/+' in invite_url:
                    invite_hash = invite_url.split('/')[-1]
                    if invite_hash.startswith('+'): invite_hash = invite_hash[1:]
                    invite_hash = invite_hash.split('?')[0]
                    await client.send_message('me', f"📢 Подписка на приватный канал")
                    try:
                        await client(ImportChatInviteRequest(invite_hash))
                        await client.send_message('me', "✅ Подписался")
                    except FloodWaitError as e:
                        await client.send_message('me', f"⏳ FloodWait: {e.seconds} сек")
                        await asyncio.sleep(e.seconds + 10)
                        continue
                    except Exception as e:
                        if 'successfully requested' in str(e).lower() or 'already in' in str(e).lower():
                            await client.send_message('me', "✅ Уже подписан")
                        else:
                            await client.send_message('me', f"⚠️ Ошибка: {e}")
                            await client.send_message(bot_name, "/start")
                            await asyncio.sleep(2)
                            await click_button(bot_name, "Пропустить")
                            await asyncio.sleep(3)
                            continue
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(random.randint(4, 7))
                else:
                    channel_username = invite_url.split('/')[-1]
                    if '/' in channel_username: channel_username = channel_username.split('/')[0]
                    channel_username = channel_username.split('?')[0]
                    channel_username = channel_username.lstrip('@')
                    if not channel_username:
                        await client.send_message('me', f"⚠️ Не удалось извлечь имя канала")
                        await client.send_message(bot_name, "/start")
                        await asyncio.sleep(2)
                        await click_button(bot_name, "Пропустить")
                        await asyncio.sleep(3)
                        continue
                    await client.send_message('me', f"📢 Подписка на @{channel_username}")
                    try:
                        await client(JoinChannelRequest(channel_username))
                        await client.send_message('me', "✅ Подписался")
                    except FloodWaitError as e:
                        await client.send_message('me', f"⏳ FloodWait: {e.seconds} сек")
                        await asyncio.sleep(e.seconds + 10)
                        continue
                    except Exception as e:
                        if 'already in' in str(e).lower() or 'successfully requested' in str(e).lower():
                            await client.send_message('me', "✅ Уже подписан")
                        else:
                            await client.send_message('me', f"⚠️ Ошибка: {e}")
                            await client.send_message(bot_name, "/start")
                            await asyncio.sleep(2)
                            await click_button(bot_name, "Пропустить")
                            await asyncio.sleep(3)
                            continue
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(3)
                    await client.send_message(bot_name, "/start")
                    await asyncio.sleep(random.randint(4, 7))
            except FloodWaitError as e:
                await client.send_message('me', f"⏳ FloodWait: {e.seconds} сек")
                await asyncio.sleep(e.seconds + 10)
                continue
            except Exception as e:
                await client.send_message('me', f"⚠️ Ошибка обработки ссылки: {e}")
                await client.send_message(bot_name, "/start")
                await asyncio.sleep(2)
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(3)
                continue
            if await solve_emoji_captcha(bot_name):
                await client.send_message('me', "🎯 Эмодзи-капча решена")
                await asyncio.sleep(1)
            clicked = False
            for btn_text in ["Проверить", "Подтвердить", "Я выполнил", "Выполнил", "Готово", "Проверка"]:
                if await click_button(bot_name, btn_text):
                    clicked = True
                    await client.send_message('me', f"✅ Нажата кнопка: {btn_text}")
                    break
            if not clicked: await client.send_message('me', "⚠️ Кнопка проверки не найдена")
            await asyncio.sleep(3)
            task_done = False
            async for msg in client.iter_messages(bot_name, limit=5):
                if msg.text:
                    text_lower = msg.text.lower()
                    if 'задание выполнено' in text_lower or 'засчитано' in text_lower:
                        task_done = True
                        local_success += 1
                        await client.send_message('me', f"✅ Задание выполнено! (всего: {local_success})")
                        break
                    elif 'не выполнено' in text_lower or 'не засчитано' in text_lower:
                        await client.send_message('me', "❌ Задание не выполнено")
                        break
            if not task_done:
                await client.send_message('me', "⏭ Пропускаю...")
                await click_button(bot_name, "Пропустить")
                await asyncio.sleep(2)
            if await solve_emoji_captcha(bot_name):
                await client.send_message('me', "🎯 Эмодзи-капча решена")
                await asyncio.sleep(1)
            await asyncio.sleep(2)
        await client.send_message('me', f"📊 ИТОГ: выполнено {local_success}, пропущено WebApp: {webapp_skipped}")
    except Exception as e:
        await client.send_message('me', f"❌ ОШИБКА: {e}")

# === ПЛАНИРОВЩИК ЗАДАНИЙ ===
async def auto_tasks_scheduler():
    MSK = timezone(timedelta(hours=3))
    BOTS_CONFIG = {"@patrickstarsrobot": ["11:00", "15:00", "17:00"]}
    MAX_DAILY_SUCCESS = 16
    COUNTER_FILE = "daily_success_counter.json"
    def load_counter():
        if os.path.exists(COUNTER_FILE):
            try:
                with open(COUNTER_FILE, 'r') as f:
                    data = json.load(f)
                    if data.get('date') == datetime.now(MSK).date().isoformat():
                        return data.get('count', 0)
            except:
                pass
        return 0
    def save_counter(count):
        with open(COUNTER_FILE, 'w') as f:
            json.dump({'date': datetime.now(MSK).date().isoformat(), 'count': count}, f)
    global_success_count = load_counter()
    while True:
        now = datetime.now(MSK)
        if global_success_count >= MAX_DAILY_SUCCESS:
            print(f"⛔ Лимит {MAX_DAILY_SUCCESS} достигнут. Жду до завтра.")
            tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            await asyncio.sleep((tomorrow - now).total_seconds())
            global_success_count = 0
            save_counter(0)
            continue
        next_runs = []
        for bot_name, times in BOTS_CONFIG.items():
            for time_str in times:
                hours, minutes = map(int, time_str.split(':'))
                run_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                if now > run_time:
                    run_time += timedelta(days=1)
                next_runs.append((run_time, bot_name))
        if not next_runs:
            await asyncio.sleep(60)
            continue
        next_runs.sort(key=lambda x: x[0])
        next_run, next_bot = next_runs[0]
        random_minutes = random.randint(0, 59)
        random_seconds = random.randint(0, 59)
        run_time_with_delay = next_run + timedelta(minutes=random_minutes, seconds=random_seconds)
        delay = (run_time_with_delay - now).total_seconds()
        if delay < 0: delay += timedelta(days=1).total_seconds()
        print("📋 ВСЕ ВРЕМЕНА:")
        for run_time, bot in next_runs:
            print(f"   {bot}: {run_time.strftime('%d.%m %H:%M:%S')}")
        print(f"🕐 СЕЙЧАС: {now.strftime('%d.%m %H:%M:%S')}")
        print(f"⏳ Следующий запуск для {next_bot}: {run_time_with_delay.strftime('%H:%M:%S')} (счётчик: {global_success_count}/{MAX_DAILY_SUCCESS})")
        await asyncio.sleep(delay)
        if global_success_count >= MAX_DAILY_SUCCESS: continue
        new_count = await execute_tasks_once(next_bot, global_success_count, MAX_DAILY_SUCCESS)
        if new_count > global_success_count:
            global_success_count = new_count
            save_counter(global_success_count)

# === ОБРАБОТЧИК КОМАНД (ВМЕСТО ПУЛИНГА) ===
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.'))
async def command_handler(event):
    if event.sender_id != MY_USER_ID:
        return
    
    text = event.raw_text.strip()
    print(f"📩 Обрабатываю команду: {text}")
    chat_id = event.chat_id
    
    if text.startswith('.subscribe'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("⚠️ Формат: .subscribe @bot_name")
        else:
            bot_name = parts[1].strip()
            await event.reply(f"🚀 Запускаю ручное выполнение заданий для {bot_name}...")
            asyncio.create_task(execute_tasks_manual(bot_name))
            
    elif text.startswith('.daily'):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.reply("⚠️ Формат: .daily @bot_name [2026-08-15 20:00]")
        else:
            match = re.match(r'(@\w+|-?\d+)\s+(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', parts[1])
            if match:
                bot_name = match.group(1)
                date_str = match.group(2)
                target_time = match.group(3)
                MSK = timezone(timedelta(hours=3))
                now = datetime.now(MSK)
                hours, minutes = map(int, target_time.split(':'))
                try:
                    scheduled_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    scheduled_time = datetime.combine(scheduled_date, datetime.min.time()).replace(hour=hours, minute=minutes, second=0, microsecond=0, tzinfo=MSK)
                except ValueError:
                    await event.reply("⚠️ Неверный формат даты. Используй ГГГГ-ММ-ДД")
                    return
                if scheduled_time < now:
                    await event.reply(f"⚠️ Указанное время уже прошло: {date_str} {target_time}")
                    return
                delay = (scheduled_time - now).total_seconds()
                await event.reply(f"⏳ Ежедневка для {bot_name} запланирована на {scheduled_time.strftime('%d.%m.%Y в %H:%M')} по Москве")
                asyncio.create_task(schedule_daily(bot_name, chat_id, delay))
            else:
                bot_name = parts[1]
                daily_buttons = ["Забрать", "Получить", "Ежедневка", "Забрать награду", "Claim", "Daily", "Получить награду"]
                clicked = False
                for btn in daily_buttons:
                    if await click_button(bot_name, btn):
                        clicked = True
                        break
                if not clicked:
                    await event.reply("   ❌ Не найдена кнопка для ежедневки")
                else:
                    await asyncio.sleep(3)
                    async for msg in client.iter_messages(bot_name, limit=10):
                        if msg.text and ('+' in msg.text or '-' in msg.text or '×' in msg.text or '÷' in msg.text):
                            match_expr = re.search(r'(\d+)\s*([+\-×÷])\s*(\d+)\s*[=？?]', msg.text)
                            if match_expr:
                                num1 = int(match_expr.group(1))
                                operator = match_expr.group(2)
                                num2 = int(match_expr.group(3))
                                if operator == '+': answer = num1 + num2
                                elif operator == '-': answer = num1 - num2
                                elif operator == '×': answer = num1 * num2
                                elif operator == '÷': answer = num1 / num2; answer = round(answer) if isinstance(answer, float) else answer
                                await click_button(bot_name, str(answer))
                                break

# === ОСНОВНАЯ ФУНКЦИЯ ===
async def main():
    print("🚀 Запуск юзербота...")
    await client.start()
    print("✅ Клиент запущен!")
    await client.send_message('me', '✅ Бот запущен и готов к работе!')
    
    asyncio.create_task(auto_parse_and_activate())
    asyncio.create_task(auto_daily())
    asyncio.create_task(auto_tasks_scheduler())
    
    print("🔄 Перехожу в режим ожидания команд...")
    
    # Просто держим бота включенным. Обработчик @client.on сделает всё сам.
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен вручную")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
