import telebot
from telebot import types
import json

API_TOKEN = '7925423997:AAHkMFZ4WnZfayI4oyu4Uwd5IN_Lt5lLyFI'
bot = telebot.TeleBot(API_TOKEN)

CHANNEL_FILE = 'channels.json'
user_states = {}

STATE_IDLE = "idle"
STATE_ADDING = "adding"
STATE_BROADCASTING = "broadcasting"

user_prefs = {}

def get_user_prefs(user_id):
    if user_id not in user_prefs:
        user_prefs[user_id] = {
            "show_id": True,
            "show_forward_from": True
        }
    return user_prefs[user_id]

def load_channels():
    try:
        with open(CHANNEL_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_channels(channels):
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(channels, f)

def add_channel(name):
    name = name.strip()
    if not name.startswith("@"):
        return False

    channels = load_channels()
    if not any(ch['name'] == name for ch in channels):
        channels.append({"name": name, "enabled": True})
        save_channels(channels)
        return True
    return False

def toggle_channel(name):
    channels = load_channels()
    for ch in channels:
        if ch['name'] == name:
            ch['enabled'] = not ch['enabled']
            break
    save_channels(channels)

def get_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("▶️ Старт"), types.KeyboardButton("⛔ Стоп"))
    kb.row(types.KeyboardButton("➕ Додати канали"), types.KeyboardButton("📋 Показати канали"))
    kb.row(types.KeyboardButton("⚙️ Налаштування"))
    return kb

def get_settings_keyboard(user_id):
    prefs = get_user_prefs(user_id)
    show_id = "✅" if prefs["show_id"] else "❌"
    show_forward = "✅" if prefs["show_forward_from"] else "❌"
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton(f"{show_id} Показувати ID повідомлень"))
    kb.row(types.KeyboardButton(f"{show_forward} Показувати джерело пересилки"))
    kb.row(types.KeyboardButton("⬅️ Назад"))
    return kb

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_states[message.chat.id] = STATE_IDLE
    get_user_prefs(message.chat.id)
    bot.send_message(message.chat.id, "Вітаю! Керуй розсилкою кнопками нижче:", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "➕ Додати канали")
def add_channels(message):
    user_states[message.chat.id] = STATE_ADDING
    bot.send_message(message.chat.id, "Надішли список каналів:\n@канал\n@канал\n@канал")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == STATE_ADDING)
def handle_channel_input(message):
    lines = message.text.splitlines()
    added = []
    for line in lines:
        if add_channel(line.strip()):
            added.append(line.strip())

    user_states[message.chat.id] = STATE_IDLE
    if added:
        bot.send_message(message.chat.id, f"✅ Додано канали:\n" + "\n".join(added), reply_markup=get_main_keyboard())
    else:
        bot.send_message(message.chat.id, "⚠️ Нічого не додано. Можливо, канали вже існують або мають неправильний формат.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📋 Показати канали")
def show_channels(message):
    channels = load_channels()
    if not channels:
        bot.send_message(message.chat.id, "Список каналів порожній.")
        return

    kb = types.InlineKeyboardMarkup()
    for ch in channels:
        status = "🟢" if ch['enabled'] else "🔴"
        kb.add(types.InlineKeyboardButton(f"{status} {ch['name']}", callback_data=f"toggle:{ch['name']}"))

    bot.send_message(message.chat.id, "Натисни на канал, щоб увімкнути/вимкнути:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("delete:", "toggle:")))
def handle_channel_callback(call):
    action, ch_name = call.data.split(":", 1)
    channels = load_channels()

    if action == "delete":
        # Видаляємо канал
        channels = [ch for ch in channels if ch['name'] != ch_name]
    elif action == "toggle":
        # Переключаємо стан каналу
        for ch in channels:
            if ch['name'] == ch_name:
                ch['enabled'] = not ch['enabled']
                break

    save_channels(channels)

    # Створюємо оновлену клавіатуру
    kb = types.InlineKeyboardMarkup(row_width=2)
    for ch in channels:
        status = "🟢" if ch['enabled'] else "🔴"
        kb.add(
            types.InlineKeyboardButton(f"{status} {ch['name']}", callback_data=f"toggle:{ch['name']}"),
            types.InlineKeyboardButton("❌", callback_data=f"delete:{ch['name']}")
        )

    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
    except Exception as e:
        print(f"Помилка при оновленні списку каналів: {e}")

@bot.message_handler(func=lambda m: m.text == "▶️ Старт")
def start_broadcast(message):
    user_states[message.chat.id] = STATE_BROADCASTING
    bot.send_message(message.chat.id, "Режим розсилки увімкнено. Надсилай будь-які повідомлення для розсилки.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "⛔ Стоп")
def stop_broadcast(message):
    if user_states.get(message.chat.id) == STATE_BROADCASTING:
        user_states[message.chat.id] = STATE_IDLE
        bot.send_message(message.chat.id, "Розсилка зупинена.", reply_markup=get_main_keyboard())
    else:
        bot.send_message(message.chat.id, "Розсилка не була активною.")

@bot.message_handler(func=lambda m: m.text == "⚙️ Налаштування")
def settings_menu(message):
    bot.send_message(message.chat.id, "Оберіть налаштування:", reply_markup=get_settings_keyboard(message.chat.id))

@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back_to_main(message):
    bot.send_message(message.chat.id, "Повертаємось в головне меню:", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: "ID повідомлень" in m.text)
def toggle_show_id(message):
    prefs = get_user_prefs(message.chat.id)
    prefs["show_id"] = not prefs["show_id"]
    bot.send_message(message.chat.id, f"Показ ID повідомлень {'увімкнено' if prefs['show_id'] else 'вимкнено'}", reply_markup=get_settings_keyboard(message.chat.id))

@bot.message_handler(func=lambda m: "джерело пересилки" in m.text)
def toggle_show_forward(message):
    prefs = get_user_prefs(message.chat.id)
    prefs["show_forward_from"] = not prefs["show_forward_from"]
    bot.send_message(message.chat.id, f"Показ джерела пересилки {'увімкнено' if prefs['show_forward_from'] else 'вимкнено'}", reply_markup=get_settings_keyboard(message.chat.id))

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice'])
def handle_messages(message):
    state = user_states.get(message.chat.id, STATE_IDLE)

    if state == STATE_BROADCASTING:
        prefs = get_user_prefs(message.chat.id)
        channels = [ch for ch in load_channels() if ch.get("enabled", True)]
        success, failed = 0, 0

        original_sender = None
        if prefs["show_forward_from"]:
            if message.forward_from:
                original_sender = f"Переслано від користувача: {message.forward_from.first_name or ''} {message.forward_from.last_name or ''} (@{message.forward_from.username or 'немає'})"
            elif message.forward_from_chat:
                chat_username = message.forward_from_chat.username
                chat_title = message.forward_from_chat.title or "Канал"
                if chat_username:
                    link_to_channel = f"https://t.me/{chat_username}"
                    original_sender = f'ℹ️ Переслано з каналу: <a href="{link_to_channel}">{chat_title}</a>'
                else:
                    original_sender = f"ℹ️ Переслано з каналу: {chat_title}"

        for ch in channels:
            try:
                sent_msg = None
                text_note = f"\n\n{original_sender}" if original_sender else ""
                parse_mode = 'HTML' if original_sender else None

                if message.text:
                    sent_msg = bot.send_message(chat_id=ch['name'], text=message.text + text_note, parse_mode=parse_mode)
                elif message.photo:
                    caption = (message.caption or "") + text_note
                    sent_msg = bot.send_photo(chat_id=ch['name'], photo=message.photo[-1].file_id, caption=caption, parse_mode=parse_mode)
                elif message.video:
                    caption = (message.caption or "") + text_note
                    sent_msg = bot.send_video(chat_id=ch['name'], video=message.video.file_id, caption=caption, parse_mode=parse_mode)
                elif message.document:
                    caption = (message.caption or "") + text_note
                    sent_msg = bot.send_document(chat_id=ch['name'], document=message.document.file_id, caption=caption, parse_mode=parse_mode)
                elif message.audio:
                    caption = (message.caption or "") + text_note
                    sent_msg = bot.send_audio(chat_id=ch['name'], audio=message.audio.file_id, caption=caption, parse_mode=parse_mode)
                elif message.voice:
                    sent_msg = bot.send_voice(chat_id=ch['name'], voice=message.voice.file_id)
                else:
                    sent_msg = bot.copy_message(chat_id=ch['name'], from_chat_id=message.chat.id, message_id=message.message_id)

                success += 1
                if prefs["show_id"] and sent_msg:
                    bot.send_message(message.chat.id, f"📩 Надіслано в {ch['name']} | ID: {sent_msg.message_id}")

            except Exception as e:
                failed += 1
                print(f"Помилка при надсиланні в {ch['name']}: {e}")

        bot.send_message(message.chat.id, f"✅ Успішно: {success}, ❌ Не вдалося: {failed}")

# Запуск
bot.infinity_polling()
