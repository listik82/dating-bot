import random
from datetime import datetime, timedelta
import database as db
from locales import get_text

FEMALE_NAMES = [
    "Dilnoza", "Gulnora", "Nodira", "Zulfiya", "Munira", "Sevara",
    "Lola", "Dilorom", "Rano", "Nigora", "Zarina", "Madina",
    "Nilufar", "Shahnoza", "Dilbar", "Gulchehra", "Ziyoda", "Aziza",
    "Dilfuza", "Nargiza", "Umida", "Feruza", "Zilola", "Dilshoda",
    "Ravshan", "Muborak", "Gulsara", "Zukhra", "Nodira", "Dilora",
    "Saida", "Mushtariy", "Zamira", "Rushana", "Dildora", "Gulbahor",
    "Nazokat", "Zarnigor", "Dilnoza", "Oygul", "Nigina", "Shahzoda",
    "Dilfuza", "Guliston", "Ziyoda", "Muyassar", "Rano", "Dilshoda",
    "Nodira", "Zarina", "Gulnora", "Sevara", "Dilnoza", "Madina"
]

CITIES_COORDS = {
    "Ташкент": (41.2995, 69.2401),
    "Самарканд": (39.6270, 66.9750),
    "Бухара": (39.7680, 64.4556),
    "Андижан": (40.7821, 72.3442),
    "Наманган": (40.9983, 71.6726),
    "Фергана": (40.3842, 71.7843),
    "Карши": (38.8606, 65.7893),
    "Нукус": (42.4602, 59.6179),
    "Ургенч": (41.5505, 60.6316),
    "Джизак": (40.1158, 67.8422),
    "Гулистан": (40.4897, 68.7842),
    "Коканд": (40.5289, 70.9425),
    "Маргилан": (40.4711, 71.7247),
    "Ангрен": (41.0167, 70.1436),
    "Алмалык": (40.8458, 69.5980),
    "Бекабад": (40.2208, 69.2725),
    "Навои": (40.1031, 65.3735),
    "Термез": (37.2242, 67.2783),
    "Шахрисабз": (39.0578, 66.8346),
    "Кунград": (43.0771, 58.9106),
}

CITIES = list(CITIES_COORDS.keys())

BIOS = [
    "Люблю Ташкент ночью и плов по воскресеньям. Ищу надёжного человека.",
    "Студентка, учусь на врача. Мечтаю о семье и уютном доме.",
    "Обожаю узбекскую музыку и танцы. Люблю готовить самсу и лагман.",
    "Работаю в сфере красоты. Люблю моду, уход за собой и чистоту.",
    "Люблю путешествовать по Узбекистану. Самарканд — мой любимый город!",
    "Верю в настоящую любовь. Ищу того, кто ценит семейные традиции.",
    "Люблю кошек, чай с лимоном и длинные разговоры до утра.",
    "Работаю в офисе, но душа просит творчества. Люблю рисовать.",
    "Обожаю зиму в горах Чимгана. Лето провожу у бабушки в кишлаке.",
    "Ищу серьёзные отношения. Не для игр, не для флирта — только по-настоящему.",
    "Люблю узбекские сериалы и турецкие дорамы. Давайте обсудим сюжет!",
    "Вегетарианка, но плов — исключение. Готовлю лучший плов в районе ;)",
    "Мечтаю открыть свой салон красоты. Пока работаю и коплю на мечту.",
    "Люблю ранние утра, когда город ещё спит. Прогулки по Анхору — моё всё.",
    "Спокойная, домашняя, хозяйственная. Ищу заботливого и щедрого мужчину.",
    "Увлекаюсь йогой и здоровым образом жизни. Ищу позитивного человека.",
    "Люблю детей, хочу большую семью. Главное — чтобы был достойный отец.",
    "Работаю в IT-компании в Ташкенте. Люблю современное и традиционное.",
    "Люблю шопинг в Самарканд Дарвозе и ужины в Мирзо-Улугбеке.",
    "По выходным уезжаю к родителям в Фергану. Семья для меня — всё.",
    "Интроверт, но с правильным человеком открываюсь. Ищу душевного.",
    "Люблю фотографировать закаты над Амударьей. Романтик в душе.",
    "Готовлю отличный шурпу и манты. Приходи на обед — не пожалеешь!",
    "Люблю читать узбекскую поэзию. Алишер Навои — мой кумир.",
    "Активная, жизнерадостная, улыбаюсь каждый день. Позитив заряжаю!"
]

# Большой пул фото URL (разные девушки)
INTERESTS_LIST = [
    "Путешествия", "Музыка", "Кино", "Спорт", "Книги", "Фотография",
    "Танцы", "Йога", "Кулинария", "Искусство", "Технологии", "Мода",
    "Природа", "Велосипед", "Бег", "Плавание", "Шопинг", "Кофе",
    "Чай", "Сериалы", "Игры", "Автомобили", "Животные", "Волонтёрство",
    "Бизнес", "Образование", "Языки", "Рисование", "Пение", "Гитара"
]

PHOTO_URLS = [
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1523264939339-c89f9dadde2e?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1519345182560-3f2917c472ef?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1464863979621-258859e62245?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1499557354967-2b2d8910bcca?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1507591064344-4c6ce005b128?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1521119989659-a83eee488058?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1489424731084-a5d8b219a5bb?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1515377905703-c4788e51af15?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1520813792240-56fc4a3765a7?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1485893086445-ed75865251e0?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1502323777036-f29e3972d82f?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1492106087820-71f1a00d2b11?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1509967419530-da38b4704bc6?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1516726817505-f5ed825624d8?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1503104834685-7205e8607eb9?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1496345875659-11f7dd282d1d?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1484515991647-c5760fcecfc7?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1500917293891-ef795e70e1f6?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1515934751635-c81c6bc9a2d8?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1542596594-649edbc13630?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1519058082700-08a0b56da9b4?w=400&h=400&fit=crop",
    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=400&h=400&fit=crop",
]


def random_last_active() -> str:
    now = datetime.now()
    r = random.random()
    if r < 0.30:
        delta = timedelta(minutes=random.randint(0, 5))
    elif r < 0.70:
        delta = timedelta(minutes=random.randint(5, 720))
    elif r < 0.90:
        delta = timedelta(hours=random.randint(12, 36))
    else:
        delta = timedelta(days=random.randint(2, 5), hours=random.randint(0, 12))
    return (now - delta).isoformat()


async def generate_fake_profiles(bot, count: int = 50):
    generated = 0
    for i in range(count):
        try:
            name = random.choice(FEMALE_NAMES)
            age = random.randint(19, 32)
            city = random.choice(CITIES)
            base_lat, base_lon = CITIES_COORDS[city]
            lat = base_lat + random.uniform(-0.03, 0.03)
            lon = base_lon + random.uniform(-0.03, 0.03)
            bio = random.choice(BIOS)

            # Выбираем 3-5 случайных уникальных фото
            num_photos = random.randint(5, 10)
            photos = random.sample(PHOTO_URLS, num_photos)

            fake_id = 1000000 + i
            last_active = random_last_active()

            interests = ", ".join(random.sample(INTERESTS_LIST, random.randint(3, 6)))

            db.save_profile(
                user_id=fake_id,
                name=name,
                age=age,
                city=city,
                lat=lat,
                lon=lon,
                gender="female",
                looking_for="male",
                bio=bio,
                interests=interests,
                is_fake=1,
                last_active=last_active
            )

            # Сохраняем все фото
            for idx, photo_url in enumerate(photos):
                db.add_photo(fake_id, photo_url, idx)

            generated += 1
        except Exception as e:
            print(f"Ошибка генерации фейка {i}: {e}")
            continue

    return generated


def get_online_status(last_active_str: str, lang: str = "ru") -> str:
    try:
        last = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
        now = datetime.now()
        diff = now - last
        minutes = int(diff.total_seconds() // 60)

        if minutes < 5:
            return get_text("online", lang)
        elif minutes < 60:
            return f"{get_text('recently', lang)} ({minutes} min)"
        elif minutes < 180:
            return f"{minutes // 60}h {get_text('recently', lang)}"
        elif diff.days == 0:
            return get_text("today", lang)
        elif diff.days == 1:
            return get_text("yesterday", lang)
        else:
            return get_text("days_ago", lang, d=diff.days)
    except:
        return get_text("recently", lang)
