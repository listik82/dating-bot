import random
import datetime
import database as db

# === 6 ЖЕНСКИХ ИМЁН ===
FEMALE_NAMES = [
    "Dilnoza", "Sevara", "Madina", "Zarina", "Nigora", "Lola"
]

# === 6 МУЖСКИХ ИМЁН ===
MALE_NAMES = [
    "Bobur", "Shavkat", "Javlon", "Sardor", "Ulugbek", "Sherzod"
]

# === 12 ФОТО (6 женских + 6 мужских) ===
PHOTO_URLS = [
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1504257432389-52343af06ae3?w=400&h=500&fit=crop",
    "https://images.unsplash.com/photo-1522529599102-193c0d76b5b6?w=400&h=500&fit=crop",
]

# === 12 ОПИСАНИЙ (6 женских + 6 мужских) ===
FEMALE_BIOS = [
    "Люблю Ташкент ночью и плов по воскресеньям. Ищу надёжного мужчину.",
    "Студентка, учусь на дизайнера. Мечтаю о семье и уютном доме.",
    "Обожаю узбекскую музыку. Люблю готовить и встречать гостей.",
    "Работаю в сфере IT. Люблю спорт, путешествия и чистоту.",
    "Люблю путешествовать по Узбекистану. Самарканд — мой любимый город!",
    "Верю в настоящую любовь. Ищу того, кто ценит семейные традиции.",
]

MALE_BIOS = [
    "Люблю Ташкент ночью и плов по воскресеньям. Ищу добрую девушку.",
    "Студент, учусь на инженера. Мечтаю о семье и уютном доме.",
    "Обожаю узбекскую музыку. Люблю готовить шашлык и лагман.",
    "Работаю в сфере IT. Люблю спорт, машины и чистоту.",
    "Люблю путешествовать по Узбекистану. Бухара — мой любимый город!",
    "Верю в настоящую любовь. Ищу ту, кто ценит семейные традиции.",
]

# === ГОРОДА ===
CITIES = [
    "Toshkent", "Namangan", "Samarqand"
]

CITIES_COORDS = {
    "Toshkent": (41.2995, 69.2401),
    "Namangan": (40.9983, 71.6726),
    "Samarqand": (39.6270, 66.9750),
}

INTERESTS_LIST = [
    "Sayohat", "Musiqa", "Kino", "Sport", "Kitoblar", "Fotografiya",
    "Raqs", "Yoga", "Oshxona", "San'at", "Texnologiyalar", "Moda",
    "Tabiat", "Hayvonlar", "Avtomobillar", "O'yinlar", "Biznes", "Fitnes"
]

def random_last_active():
    """Генерирует случайную дату последней активности"""
    now = datetime.datetime.now()
    delta = random.randint(0, 72)
    return now - datetime.timedelta(hours=delta)


async def generate_fake_profiles(bot, count: int = 50):
    """Создаёт ровно 12 фейков: 6 женских + 6 мужских"""
    generated = 0

    for i in range(12):
        try:
            # Первые 6 (i=0..5) — женские, следующие 6 (i=6..11) — мужские
            is_female = i < 6

            if is_female:
                name = FEMALE_NAMES[i]
                gender = "female"
                looking_for = "male"
                bio = FEMALE_BIOS[i]
            else:
                name = MALE_NAMES[i - 6]
                gender = "male"
                looking_for = "female"
                bio = MALE_BIOS[i - 6]

            age = random.randint(20, 30)
            city = random.choice(CITIES)
            base_lat, base_lon = CITIES_COORDS[city]
            lat = base_lat + random.uniform(-0.03, 0.03)
            lon = base_lon + random.uniform(-0.03, 0.03)

            # Каждому фейку — 2-4 фото
            num_photos = random.randint(2, 4)
            start_idx = i * 1  # Уникальные фото для каждого
            photos = PHOTO_URLS[start_idx : start_idx + num_photos]
            if len(photos) < num_photos:
                photos = random.sample(PHOTO_URLS, num_photos)

            fake_id = 1000000 + i
            last_active = random_last_active()
            interests = ", ".join(random.sample(INTERESTS_LIST, random.randint(2, 4)))

            db.save_profile(
                user_id=fake_id,
                name=name,
                age=age,
                city=city,
                lat=lat,
                lon=lon,
                gender=gender,
                looking_for=looking_for,
                bio=bio,
                interests=interests,
                is_fake=1,
                last_active=last_active
            )

            for idx, photo_url in enumerate(photos):
                db.add_photo(fake_id, photo_url, idx)

            generated += 1
        except Exception as e:
            print(f"Ошибка генерации фейка {i}: {e}")
            continue

    return generated
