from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from locales import get_text


INTERESTS = {
    "ru": [
        "Путешествия", "Музыка", "Кино", "Спорт", "Книги", "Фотография", "Танцы", "Йога",
        "Кулинария", "Искусство", "Технологии", "Мода", "Природа", "Животные", "Автомобили",
        "Игры", "Бизнес", "Фитнес", "Бег", "Велосипед", "Плавание", "Кемпинг",
        "Аниме", "Блогинг", "Психология", "Медитация", "Кофе", "DIY", "Стартапы", "Дизайн"
    ],
    "uz": [
        "Sayohat", "Musiqa", "Kino", "Sport", "Kitoblar", "Fotografiya", "Raqs", "Yoga",
        "Oshxona", "San'at", "Texnologiyalar", "Moda", "Tabiat", "Hayvonlar", "Avtomobillar",
        "O'yinlar", "Biznes", "Fitnes", "Yugurish", "Velosiped", "Suzish", "Kemping",
        "Anime", "Bloging", "Psixologiya", "Meditatsiya", "Kofe", "DIY", "Startaplar", "Dizayn"
    ]
}


def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")]
    ])


def main_menu_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_watch", lang), callback_data="goto_watch")],
        [InlineKeyboardButton(text=get_text("btn_profile", lang), callback_data="goto_profile"),
         InlineKeyboardButton(text=get_text("btn_filters", lang), callback_data="goto_filters")],
        [InlineKeyboardButton(text=get_text("btn_matches", lang), callback_data="goto_matches"),
         InlineKeyboardButton(text=get_text("btn_likes", lang), callback_data="goto_likes")],
        [InlineKeyboardButton(text=get_text("btn_delete", lang), callback_data="menu_delete")]
    ])


def gender_select_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("male", lang), callback_data="gender_male"),
         InlineKeyboardButton(text=get_text("female", lang), callback_data="gender_female")]
    ])


def looking_select_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("look_male", lang), callback_data="look_male"),
         InlineKeyboardButton(text=get_text("look_female", lang), callback_data="look_female")],
        [InlineKeyboardButton(text=get_text("look_all", lang), callback_data="look_all")]
    ])

def interests_kb(lang: str, selected: set = None):
    if selected is None:
        selected = set()
    items = INTERESTS.get(lang, INTERESTS["ru"])
    buttons = []
    row = []
    for i, item in enumerate(items):
        text = ("✅ " if item in selected else "") + item
        row.append(InlineKeyboardButton(text=text, callback_data=f"interest_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text=get_text("interests_done", lang), callback_data="interests_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def bio_skip_kb(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("skip_bio", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )




def reactions_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔥", callback_data="react_fire"),
            InlineKeyboardButton(text="❤️", callback_data="react_heart"),
            InlineKeyboardButton(text="🤝", callback_data="react_handshake"),
        ],
        [
            InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip")
        ]
    ])


def write_kb(user_id: int, lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("match_write", lang), url=f"tg://user?id={user_id}")]
    ])




def photo_done_inline_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("interests_done", lang), callback_data="photo_done")]
    ])

def filters_menu_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("filter_city", lang), callback_data="filter_city"),
         InlineKeyboardButton(text=get_text("filter_radius", lang), callback_data="filter_radius")],
        [InlineKeyboardButton(text=get_text("filter_age", lang), callback_data="filter_age")],
        [InlineKeyboardButton(text=get_text("filter_reset", lang), callback_data="filter_reset")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="filter_back")]
    ])


def location_kb(lang: str):
    loc_text = get_text("location_btn", lang)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=loc_text, request_location=True)],
            [KeyboardButton(text=get_text("skip_btn", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def delete_confirm_kb(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("delete_yes", lang)), KeyboardButton(text=get_text("delete_no", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def profile_actions_kb(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("edit_profile", lang), callback_data="profile_edit")],
        [InlineKeyboardButton(text=get_text("btn_delete", lang), callback_data="profile_delete")]
    ])





def watch_again_kb(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("yes", lang)), KeyboardButton(text=get_text("no", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# === ФЕЙКИ ===
def fake_list_kb(fakes: list, lang: str = "ru"):
    """Клавиатура списка фейков для редактирования"""
    buttons = []
    for f in fakes:
        buttons.append([InlineKeyboardButton(
            text=f"{f['name']}, {f['age']} — {f['city']}",
            callback_data=f"fake_edit_{f['user_id']}"
        )])
    buttons.append([InlineKeyboardButton(text=get_text("delete_all", lang), callback_data="fake_delete_all")])
    buttons.append([InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="fake_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def fake_edit_fields_kb(fake_id: int, lang: str = "ru"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("fake_field_name", lang), callback_data=f"fakefield_name_{fake_id}")],
        [InlineKeyboardButton(text=get_text("fake_field_age", lang), callback_data=f"fakefield_age_{fake_id}")],
        [InlineKeyboardButton(text=get_text("fake_field_city", lang), callback_data=f"fakefield_city_{fake_id}")],
        [InlineKeyboardButton(text=get_text("fake_field_bio", lang), callback_data=f"fakefield_bio_{fake_id}")],
        [InlineKeyboardButton(text=get_text("interests", lang), callback_data=f"fakefield_interests_{fake_id}")],
        [InlineKeyboardButton(text=get_text("fake_field_photo", lang), callback_data=f"fakefield_photo_{fake_id}")],
        [InlineKeyboardButton(text=get_text("fake_field_delete", lang), callback_data=f"fakedel_{fake_id}")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="fake_back")]
    ])


def like_back_kb(user_id: int, lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("reaction_heart", lang), callback_data=f"likeback_{user_id}")],
        [InlineKeyboardButton(text="⏭️", callback_data=f"skipback_{user_id}")]
    ])


def inline_main_menu_kb(lang: str):
    """Inline кнопки для быстрого доступа к разделам"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_watch", lang), callback_data="goto_watch")],
        [InlineKeyboardButton(text=get_text("btn_profile", lang), callback_data="goto_profile"),
         InlineKeyboardButton(text=get_text("btn_filters", lang), callback_data="goto_filters")],
        [InlineKeyboardButton(text=get_text("btn_matches", lang), callback_data="goto_matches"),
         InlineKeyboardButton(text=get_text("btn_likes", lang), callback_data="goto_likes")],
    ])


# === ВЕРИФИКАЦИЯ ===
def verify_kb(lang: str = "ru"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("verify_button", lang))]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def verify_contact_kb(lang: str = "ru"):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("verify_share_contact", lang), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def verify_code_kb(lang: str = "ru"):
    """Inline клавиатура для ввода кода верификации"""
    buttons = [
        [
            InlineKeyboardButton(text="1", callback_data="code_1"),
            InlineKeyboardButton(text="2", callback_data="code_2"),
            InlineKeyboardButton(text="3", callback_data="code_3")
        ],
        [
            InlineKeyboardButton(text="4", callback_data="code_4"),
            InlineKeyboardButton(text="5", callback_data="code_5"),
            InlineKeyboardButton(text="6", callback_data="code_6")
        ],
        [
            InlineKeyboardButton(text="7", callback_data="code_7"),
            InlineKeyboardButton(text="8", callback_data="code_8"),
            InlineKeyboardButton(text="9", callback_data="code_9")
        ],
        [
            InlineKeyboardButton(text="0", callback_data="code_0"),
            InlineKeyboardButton(text="⌫", callback_data="code_backspace"),
            InlineKeyboardButton(text="✅", callback_data="code_submit")
        ],
        [
            InlineKeyboardButton(text="🔄 Новый код", callback_data="resend_code")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
