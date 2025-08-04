import os
import json
import random
import re
from flask import Flask
from keep_alive import keep_alive
from threading import Thread
from datetime import datetime, timezone
from telebot.types import InlineQueryResultArticle, InputTextMessageContent
import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto
)

TOKEN = "7700337651:AAEYR-Uru8MtN3BfofwIduT5go4ZZLh-5Qw"
bot = telebot.TeleBot(TOKEN)

CHANNELS = {
    "kanal1": "@MemoryHubUz",
    "kanal2": "@moodri_channel",
    "kanal3": "@qashqirlarmakoni_fullserial"
}

CHANNEL_LINKS = {
    "@MemoryHubUz": "https://t.me/MemoryHubUz",
    "@moodri_channel": "https://t.me/moodri_channel",
    "@qashqirlarmakoni_fullserial": "https://t.me/qashqirlarmakoni_fullserial"
}

ADMIN_IDS = [5715520170]
# 🔐 Faqat shu kanal orqali kelgan postlar saqlanadi
MOVIE_FEED_CHANNEL_ID = -1002860992075 
DONAT_LINK = "https://t.me/MemoryHubUz/178"
MOVIES_DB = "movies.json"
USERS_DB = "users.json"

def get_current_datetime():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def get_current_user():
    return "Yusufbek-1701"

admin_states = {}
user_states = {}
user_random_history = {}

class Database:
    @staticmethod
    def initialize():
        for db_file in [MOVIES_DB, USERS_DB]:
            if not os.path.exists(db_file):
                with open(db_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)

    @staticmethod
    def load_data(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_data(data, file_path):
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    @classmethod
    def add_movie(cls, movie_id: str, movie_data: dict):
        movies = cls.load_data(MOVIES_DB)
        movies[movie_id] = {
            "data": movie_data,
            "added_date": get_current_datetime(),
            "added_by": get_current_user(),
            "timestamp": datetime.now(timezone.utc).timestamp()
        }
        cls.save_data(movies, MOVIES_DB)

    @classmethod
    def get_movie(cls, movie_id: str):
        movies = cls.load_data(MOVIES_DB)
        return movies.get(movie_id)

    @classmethod
    def delete_movie(cls, movie_id: str):
        movies = cls.load_data(MOVIES_DB)
        if movie_id in movies:
            del movies[movie_id]
            cls.save_data(movies, MOVIES_DB)
            return True
        return False

    @classmethod
    def get_random_movie(cls, user_id=None):
        movies = cls.load_data(MOVIES_DB)
        if not movies:
            return None, None
        all_keys = list(movies.keys())
        if user_id is not None:
            history = user_random_history.get(user_id, [])
            available = [k for k in all_keys if k not in history]
            if not available:
                user_random_history[user_id] = []
                available = all_keys.copy()
            movie_id = random.choice(available)
            user_random_history.setdefault(user_id, []).append(movie_id)
            if len(user_random_history[user_id]) > len(all_keys):
                user_random_history[user_id] = user_random_history[user_id][-len(all_keys):]
            return movie_id, movies[movie_id]
        else:
            movie_id = random.choice(all_keys)
            return movie_id, movies[movie_id]

def parse_caption(caption: str) -> dict:
    data = {}
    lines = caption.strip().splitlines()

    for line in lines:
        if line.startswith('🎬'):
            clean_line = re.sub(r'<.*?>', '', line)  # <b> yoki boshqa HTML taglarni olib tashlash
            data['title'] = clean_line.replace('🎬', '').strip()
        elif 'Davlat:' in line:
            data['country'] = line.split('Davlat:')[1].strip().strip('*')
        elif 'Til:' in line:
            data['language'] = line.split('Til:')[1].strip().strip('*')
        elif 'Janr:' in line:
            data['genre'] = line.split('Janr:')[1].strip().strip('*')
        elif 'Sifat:' in line:
            data['quality'] = line.split('Sifat:')[1].strip().strip('*')
        elif 'Yil:' in line:
            data['year'] = line.split('Yil:')[1].strip().strip('*')
        elif 'Kod:' in line:
            data['code'] = line.split('Kod:')[1].strip().strip('*')
        elif 'Ko\'rishlar:' in line:
            data['views'] = line.split('Ko\'rishlar:')[1].strip().strip('*')

    return data

def create_subscription_keyboard():
    keyboard = InlineKeyboardMarkup()
    for channel_id, channel_username in CHANNELS.items():
        keyboard.add(InlineKeyboardButton(
            text=f"➕ Obuna bo`ling",
            url=f"https://t.me/{channel_username.replace('@', '')}"
        ))
    keyboard.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription"))
    return keyboard

def generate_caption(meta: dict) -> str:
    return (
        f"🎬 <b>{meta.get('title', '')}</b>\n"
        f"➖➖➖➖➖➖➖\n"
        f"<b>🌐 Davlat:</b> {meta.get('country', '')}\n"
        f"<b>🚩 Til:</b> {meta.get('language', '')}\n"
        f"<b>🎭 Janr:</b> {meta.get('genre', '')}\n"
        f"<b>💿 Sifat:</b> {meta.get('quality', '')}\n"
        f"<b>📆 Yil:</b> {meta.get('year', '')}\n\n"
        f"<b>🔢 Kod:</b> {meta.get('code', '')}\n"
        f"<b>👁 Ko'rishlar:</b> {meta.get('views', '0')}\n\n"
        f"<b>🎬</b> @MemoryHubUz <b>| Filmlar olami 🍿</b>"
    )

def check_subscription(user_id: int) -> tuple:
    not_subscribed = []
    for channel in CHANNELS.values():
        try:
            member = bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel)
        except Exception as e:
            print(f"Subscription check error: {e}")
            not_subscribed.append(channel)
    return len(not_subscribed) == 0, not_subscribed

def create_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔍 Kod orqali", callback_data="enter_code"),
        InlineKeyboardButton("🔎 Nom orqali", switch_inline_query_current_chat="")
    )
    keyboard.add(
        InlineKeyboardButton("🎲 Random", callback_data="random_movie"),
        InlineKeyboardButton("📊 Top filmlar", switch_inline_query_current_chat="top_films")
    )
    return keyboard

def create_movie_keyboard(movie_id: str, admin=False):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(
            "Ulashish 🚀",
            switch_inline_query=f"code_{movie_id}"
        ),
        InlineKeyboardButton("💰 Donat", url=DONAT_LINK)
    )
   
    keyboard.add(InlineKeyboardButton("🗑 O'chirish", callback_data=f"delete_{movie_id}"))
    return keyboard

def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("➕ Raqamli ma'lumot qo'shish", callback_data="add_movie"))
    keyboard.add(InlineKeyboardButton("📊 Ma'lumotlar", callback_data="show_data"))
    keyboard.add(InlineKeyboardButton("🗑 Kinoni o'chirish", callback_data="delete_select_movie"))
    return keyboard

from telebot.types import InlineQueryResultCachedVideo, InputTextMessageContent

@bot.inline_handler(lambda query: True)
def inline_search(query: InlineQuery):
    text = query.query.lower().strip()
    results = []

    movies = Database.load_data(MOVIES_DB)

    if text.startswith("code_"):
        # 🔁 Kod orqali ulashish rejimi
        movie_code = text.replace("code_", "")
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start=code_{movie_code}"
        result = InlineQueryResultArticle(
            id=movie_code,
            title="📽 Kinoni ulashish | Ustiga bosing👈",
            description="Do‘stlaringizga ushbu kinoni yuboring!",
            input_message_content=InputTextMessageContent(message_text=link)
        )
        results.append(result)

    elif text == "top_films":
        # 🔝 Eng ko‘p ko‘rilgan 10 ta kino
        sorted_movies = sorted(
            movies.items(),
            key=lambda x: int(x[1]["data"].get("meta", {}).get("views", 0)),
            reverse=True
        )[:10]

        for code, movie in sorted_movies:
            meta = movie["data"].get("meta", {})
            title = meta.get("title", "Nomsiz")
            views = meta.get("views", "0")
            caption = f"🔢 {code} | 👁 {views} ta ko‘rish"
            result = InlineQueryResultArticle(
                id=code,
                title=title,
                description=caption,
                input_message_content=InputTextMessageContent(message_text=f"/start code_{code}")
            )
            results.append(result)

    elif not text:
        # ✨ Faqat @botnomi deb yozilgan holatda random 10 ta kino chiqarish
        random_movies = random.sample(list(movies.items()), min(10, len(movies)))
        for code, movie in random_movies:
            meta = movie["data"].get("meta", {})
            title = meta.get("title", "Nomsiz")
            views = meta.get("views", "0")
            quality = meta.get("quality", "Noma'lum")
            caption = f"🔢 {code} | {quality} | 👁 {views}"
            result = InlineQueryResultArticle(
                id=code,
                title=title,
                description=caption,
                input_message_content=InputTextMessageContent(message_text=f"/start code_{code}")
            )
            results.append(result)

    else:
        # 🔎 Nomi orqali qidiruv
        for code, movie in movies.items():
            meta = movie["data"].get("meta", {})
            title = meta.get("title", "").lower()
            if text in title:
                views = meta.get("views", "0")
                quality = meta.get("quality", "Noma'lum")
                caption = f"🔢 {code} | {quality} | 👁 {views}"
                result = InlineQueryResultArticle(
                    id=code,
                    title=meta.get("title", "Nomsiz"),
                    description=caption,
                    input_message_content=InputTextMessageContent(message_text=f"/start code_{code}")
                )
                results.append(result)

        # ❌ Agar nom bo‘yicha hech nima topilmasa — “kino topilmadi” degan natija chiqaramiz
        if not results:
            result = InlineQueryResultArticle(
                id="not_found",
                title="❌ Kino topilmadi",
                description="‼️Eslatma: Kino kodini @MemoryHubUz kanalidan olasiz! ",
                input_message_content=InputTextMessageContent(message_text="❌ Kino topilmadi.")
            )
            results.append(result)

    bot.answer_inline_query(query.id, results[:10], cache_time=1)

@bot.message_handler(
    func=lambda message: not message.text.startswith('/') and message.from_user.id not in admin_states,
    content_types=['text']
)
def handle_user_code(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if text.isdigit():
        # ✅ Agar faqat raqam — kod orqali qidiriladi
        check_and_send_movie(message, text)
    else:
        # ❌ Harf yoki noto‘g‘ri format bo‘lsa — foydalanuvchini yo‘naltiramiz
        msg = (
            "🔢 <b>Kod orqali qidiring</b>\n\n"
            "<blockquote>Agar siz nom orqali qidirmoqchi bo‘lsangiz, quyidagi «🔍 Nom orqali qidirish» tugmasini bosing va filmni yuklang</blockquote>"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("🔍 Nom orqali qidirish", switch_inline_query_current_chat=text)
        )
        keyboard.add(
            InlineKeyboardButton("🔙Orqaga", callback_data="back_to_main")
        )

        bot.send_message(
            message.chat.id,
            msg,
            parse_mode='HTML',
            reply_markup=keyboard
        )

    # 🔚 Kod kiritish jarayoni tugadi — holatni tozalaymiz
    if user_states.get(user_id) == "waiting_for_code":
        del user_states[user_id]

@bot.message_handler(func=lambda message: not message.text.startswith('/') and message.from_user.id not in admin_states, content_types=['text'])
def handle_user_code(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    check_and_send_movie(message, text)
    if user_states.get(user_id) == "waiting_for_code":
        del user_states[user_id]

@bot.message_handler(commands=['start'])
def start_handler(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if message.text.startswith('/start code_'):
        movie_code = message.text.split('code_')[1]
        check_and_send_movie(message, movie_code)
        return

    is_subscribed, _ = check_subscription(user_id)
    if not is_subscribed:
        bot.send_message(
            user_id,
            "🤩Botdan foydalanish uchun quydagi kanallarga obuna bo‘ling‼️",
            reply_markup=create_subscription_keyboard()
        )
        return

    msg = (
        "<b>👋Assalomu alaykum</b>, <a href='tg://user?id={user_id}'>{user_name}</a>!\n\n"
        "<i>🎥Bot yordamida sizga yoqadigan filmlar va seriallarni istalgan vaqtda, yuqori sifatda tomosha qiling.</i>\n\n"
        "<b>Qidiruv turini tanlang:</b>"
    ).format(user_id=user_id, user_name=user_name)
    bot.send_message(
        user_id,
        msg,
        parse_mode='HTML',
        reply_markup=create_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: CallbackQuery):
    user_id = call.from_user.id
    data = call.data
    user_name = call.from_user.first_name

    is_subscribed, not_subscribed = check_subscription(user_id)

    # 🔐 Faqat adminlar uchun sahifalangan statistika
    if data.startswith("show_data"):
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Bu funksiya faqat adminlar uchun!")
            return

        # Sahifa raqamini ajratamiz
        try:
            page = int(data.split("_")[-1])
        except (IndexError, ValueError):
            page = 0

        per_page = 70
        start_index = page * per_page
        end_index = start_index + per_page

        movies = Database.load_data(MOVIES_DB)
        users = Database.load_data(USERS_DB)

        # Sahifadagi kinolarni ajratib olamiz
        movie_items = list(movies.items())[start_index:end_index]

        movies_list = "\n".join([
            f"•Kod: {code} - {movie_data['data'].get('caption', '').splitlines()[0][:30]}..."
            for code, movie_data in movie_items
        ])

        total_pages = (len(movies) + per_page - 1) // per_page

        stats_text = (
            "<b>📊 Statistika:</b>\n\n"
            f"🎬 Kinolar soni: {len(movies)}\n"
            f"👥 Foydalanuvchilar soni: {len(users)}\n"
            f"📅 Joriy vaqt: {get_current_datetime()}\n"
            f"👤 Admin: {get_current_user()}\n\n"
            f"<b>📁 Mavjud kinolar (sahifa {page+1}/{total_pages}):</b>\n"
            f"{movies_list if movie_items else '❌ Kinolar topilmadi'}"
        )

        # Navigatsion tugmalar
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ Oldingi", callback_data=f"show_data_{page-1}"))
        if end_index < len(movies):
            nav_buttons.append(InlineKeyboardButton("▶️ Keyingi", callback_data=f"show_data_{page+1}"))

        keyboard = InlineKeyboardMarkup()
        if nav_buttons:
            keyboard.row(*nav_buttons)
        keyboard.add(InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin"))

        bot.edit_message_text(
            stats_text,
            user_id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        return

    elif data == "add_movie":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Bu funksiya faqat adminlar uchun!")
            return
        admin_states[user_id] = "waiting_for_movie"
        bot.edit_message_text(
            "📤 Qo'shmoqchi bo'lgan kino ma'lumotini yuboring.\n"
            "Video yoki rasm yuborishingiz mumkin",
            user_id,
            call.message.message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("⬅️ Bekor qilish", callback_data="cancel_admin")
            )
        )
    elif data == "delete_select_movie":
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ Bu funksiya faqat adminlar uchun!")
            return
        admin_states[user_id] = "waiting_for_delete_code"
        bot.edit_message_text(
            "Qaysi kodli kinoni o'chirmoqchisiz? Kodni yuboring.",
            user_id,
            call.message.message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("⬅️ Orqaga", callback_data="back_to_admin")
            )
        )
    elif data == "back_to_admin":
        admin_states.pop(user_id, None)
        bot.edit_message_text(
            "Admin paneliga qaytdingiz:",
            user_id,
            call.message.message_id,
            reply_markup=create_admin_keyboard()
        )
    elif data == "check_subscription":
        if is_subscribed:
            msg = (
                f"<b>👋Assalomu alaykum</b>, <a href='tg://user?id={user_id}'>{user_name}</a>!\n\n"
                "<i>🎥Bot yordamida sizga yoqadigan filmlar va seriallarni istalgan vaqtda, yuqori sifatda tomosha qiling.</i>\n\n"
                "<b>Qidiruv turini tanlang:</b>"
            )
            bot.edit_message_text(
                "<b>MemoryHubUz bot</b>\n" + msg,
                user_id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=create_main_keyboard()
            )
        else:
            channels_text = "\n".join([f"• {channel}" for channel in not_subscribed])
            bot.answer_callback_query(
                call.id,
                f" 😕Siz quyidagi kanallarga obuna bo'lmagansiz:\n{channels_text}",
                show_alert=True
            )
        return
    if not is_subscribed:
        bot.answer_callback_query(
            call.id,
            "❌ Botdan foydalanish uchun kanallarga obuna bo'ling!",
            show_alert=True
        )
        bot.edit_message_text(
            "🤨Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            user_id,
            call.message.message_id,
            reply_markup=create_subscription_keyboard()
        )
        return
    if data == "enter_code":
        user_states[user_id] = "waiting_for_code"
        msg = (
            "<b>📹 Kino kodini kiriting!</b>\n\n"
            "<i>Kino kodlarini shu kanaldan olishingiz mumkin:</i>\n"
            f"<b><a href='{CHANNEL_LINKS['@MemoryHubUz']}'>Kodlar bo'limi</a></b>"
        )
        bot.edit_message_text(
            msg,
            user_id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")
            )
        )
    elif data == "random_movie":
        movie_id, movie_data = Database.get_random_movie(user_id)
        if movie_id and movie_data:
            send_movie(call.message, movie_id, movie_data)
        else:
            bot.answer_callback_query(
                call.id,
                "❌ Hozircha kinolar mavjud emas",
                show_alert=True
            )
    # Foydalanuvchi uchun: faqat chatdan xabarni o'chiradi
    elif data.startswith("delete_"):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception as e:
            print(f"Message delete error: {e}")
    elif data == "back_to_main":
        if user_id in user_states:
            del user_states[user_id]
        msg = (
            "<b>MemoryHubUz bot⚜</b>\n\n"
            "🎬<i>Bot yordamida sizga yoqadigan filmlar va seriallarni istalgan vaqtda, yuqori sifatda tomosha qiling.</i>\n\n"
            "<b>Qidiruv turini tanlang:</b>"
        )
        bot.edit_message_text(
            msg,
            user_id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=create_main_keyboard()
        )

def send_movie(message: Message, movie_id: str, movie_data: dict, forward=False):
    data = movie_data['data']
    meta = data.get('meta', {})
    caption = generate_caption(meta) if meta else data.get('caption', '')
    keyboard = create_movie_keyboard(movie_id)

    if 'photo' in data:
        bot.send_photo(message.chat.id, data['photo'], caption=caption, parse_mode='HTML', reply_markup=keyboard)
    elif 'video' in data:
        bot.send_video(message.chat.id, data['video'], caption=caption, parse_mode='HTML', reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, caption, parse_mode='HTML', reply_markup=keyboard)

def check_and_send_movie(message: Message, movie_code: str):
    movie_data = Database.get_movie(movie_code)
    if movie_data:
        # 🔁 Ko‘rishlar sonini oshiramiz
        views = int(movie_data['data']['meta'].get('views', 0))
        views += 1
        movie_data['data']['meta']['views'] = str(views)

        # 🔄 Yangilangan ma’lumot bilan bazani yangilaymiz
        Database.add_movie(movie_code, movie_data['data'])

        # 🎬 Foydalanuvchiga yuboramiz
        send_movie(message, movie_code, movie_data)
    else:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main"))
            bot.send_message(
                    message.chat.id,
                    (
                               "☹️ <b>Kod topilmadi</b>\n"
                               "<blockquote>🔻 Bizning bazamizda ushbu kod mavjud emas.Kodni to'g'ri yuborganingizni hamda uni faqat rasmiy sahifalarimizdan olganingizni tekshiring.</blockquote>"
                     ),
                     parse_mode='HTML',
                     reply_markup=keyboard
             )
@bot.channel_post_handler(content_types=['photo', 'video'])
def handle_channel_post(message: Message):
    if message.chat.id != MOVIE_FEED_CHANNEL_ID:
        return

    caption = message.caption or ''
    parsed = parse_caption(caption)
    movie_code = parsed.get('code')

    if not movie_code:
        print("❌ Kod topilmadi, saqlanmadi.")
        return

    movie_data = {
        "meta": parsed,
        "caption": caption
    }

    if message.content_type == 'photo':
        movie_data["photo"] = message.photo[-1].file_id
    elif message.content_type == 'video':
        movie_data["video"] = message.video.file_id

    # 🔐 Bazaga qo‘shamiz
    Database.add_movie(movie_code, movie_data)

    # ✅ Adminlarga habar yuboramiz
    movie_title = parsed.get('title', 'Noma’lum')
    admin_text = f"📥 Yangi kino qo‘shildi:\n🎬 {movie_title}\n🔢 Kod: {movie_code}"
    for admin_id in ADMIN_IDS:
        bot.send_message(admin_id, admin_text)

    print(f"✅ Kino qo‘shildi: {movie_title} | Kod: {movie_code}")

app = Flask('')

@app.route('/')
def home():
    return "Bot tirik 🙂"

def run():
    app.run(host='0.0.0.0', port=8081)

def keep_alive():
    t = Thread(target=run)
    t.start()
@bot.message_handler(commands=['admin'])
def admin_panel(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Admin paneliga kirish taqiqlanadi. Ruxsat yo‘q")
        return
    bot.send_message(
        user_id,
        "🪬Admin paneliga xush kelibsiz!\n\nKerakli bo‘limni tanlang:",
        reply_markup=create_admin_keyboard()
    )

@bot.message_handler(func=lambda message: message.from_user.id in admin_states, content_types=['text', 'photo', 'video'])
def handle_admin_input(message: Message):
    user_id = message.from_user.id
    state = admin_states[user_id]
    if state == "waiting_for_movie":
        movie_data = {}
        if message.content_type == 'photo':
            movie_data['photo'] = message.photo[-1].file_id
            movie_data['caption'] = message.caption or ''
        elif message.content_type == 'video':
            movie_data['video'] = message.video.file_id
            movie_data['caption'] = message.caption or ''
        else:
            movie_data['text'] = message.text
        admin_states[user_id] = {
            "state": "waiting_for_code",
            "movie_data": movie_data
        }
        bot.reply_to(
            message,
            "Endi ushbu kino uchun kod kiriting:",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_adding")
            )
        )
    elif isinstance(state, dict) and state["state"] == "waiting_for_code":
        try:
            movie_code = message.text.strip()
            if not movie_code.isdigit():
                raise ValueError("Kod raqamlardan iborat bo'lishi kerak")
            Database.add_movie(movie_code, state["movie_data"])
            bot.reply_to(
                message,
                f"✅ Kino muvaffaqiyatli qo'shildi!\nKodi: {movie_code}",
                reply_markup=create_admin_keyboard()
            )
            del admin_states[user_id]
        except Exception as e:
            bot.reply_to(
                message,
                f"❌ Xatolik yuz berdi: {str(e)}",
                reply_markup=create_admin_keyboard()
            )
            del admin_states[user_id]
    elif state == "waiting_for_delete_code":
        movie_code = message.text.strip()
        if Database.delete_movie(movie_code):
            bot.reply_to(
                message,
                f"✅ O‘chirsh tasdiqlandi! {movie_code} ga bog‘langan ma‘lumot o‘chirildi.",
                reply_markup=create_admin_keyboard()
            )
        else:
            bot.reply_to(
                message,
                f"❌ Kod {movie_code} bilan kino topilmadi.",
                reply_markup=create_admin_keyboard()
            )
        del admin_states[user_id]

Database.initialize()

if __name__ == "__main__":
    keep_alive()
    print("Bot ishga tushdi...")
    bot.infinity_polling()