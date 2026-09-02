import os
import math
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Railway предоставляет DATABASE_URL автоматически при подключении PostgreSQL
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError(
        "DATABASE_URL не задан! "
        "Добавь переменную DATABASE_URL в Railway (Variables сервиса бота)."
    )

# Если URL начинается с postgres://, меняем на postgresql:// (для psycopg2)
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

import psycopg2
from psycopg2.extras import RealDictCursor


def get_conn():
    """Возвращает подключение к PostgreSQL"""
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id BIGINT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            city TEXT NOT NULL,
            lat REAL,
            lon REAL,
            gender TEXT NOT NULL,
            looking_for TEXT NOT NULL,
            bio TEXT,
            interests TEXT,
            is_fake INTEGER DEFAULT 0,
            verified INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            photo_file_id TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY,
            lang TEXT DEFAULT 'ru'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            user_id BIGINT PRIMARY KEY,
            min_age INTEGER DEFAULT 18,
            max_age INTEGER DEFAULT 99,
            city_filter TEXT DEFAULT '',
            radius_km INTEGER DEFAULT 0,
            use_location INTEGER DEFAULT 0,
            filter_lat REAL,
            filter_lon REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id SERIAL PRIMARY KEY,
            from_user BIGINT NOT NULL,
            to_user BIGINT NOT NULL,
            action TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_user, to_user)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id SERIAL PRIMARY KEY,
            user1 BIGINT NOT NULL,
            user2 BIGINT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user1, user2)
        )
    """)

    conn.commit()
    conn.close()


def haversine(lat1, lon1, lat2, lon2):
    if lat1 is None or lat2 is None:
        return float('inf')
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def save_profile(user_id: int, name: str, age: int, city: str, lat, lon,
                 gender: str, looking_for: str, bio: str, interests: str = "",
                 is_fake: int = 0, last_active=None):
    conn = get_conn()
    c = conn.cursor()
    if last_active is None:
        c.execute("""
            INSERT INTO profiles
            (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake, last_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
            name = EXCLUDED.name, age = EXCLUDED.age, city = EXCLUDED.city,
            lat = EXCLUDED.lat, lon = EXCLUDED.lon, gender = EXCLUDED.gender,
            looking_for = EXCLUDED.looking_for, bio = EXCLUDED.bio,
            interests = EXCLUDED.interests, is_fake = EXCLUDED.is_fake,
            last_active = CURRENT_TIMESTAMP
        """, (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake))
    else:
        c.execute("""
            INSERT INTO profiles
            (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake, last_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
            name = EXCLUDED.name, age = EXCLUDED.age, city = EXCLUDED.city,
            lat = EXCLUDED.lat, lon = EXCLUDED.lon, gender = EXCLUDED.gender,
            looking_for = EXCLUDED.looking_for, bio = EXCLUDED.bio,
            interests = EXCLUDED.interests, is_fake = EXCLUDED.is_fake,
            last_active = EXCLUDED.last_active
        """, (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake, last_active))
    conn.commit()
    conn.close()


def add_photo(user_id: int, photo_file_id: str, sort_order: int = 0):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO photos (user_id, photo_file_id, sort_order) VALUES (%s, %s, %s)",
              (user_id, photo_file_id, sort_order))
    conn.commit()
    conn.close()


def get_photos(user_id: int) -> List[str]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT photo_file_id FROM photos WHERE user_id = %s ORDER BY sort_order", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [r["photo_file_id"] for r in rows]


def delete_photos(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM photos WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()


def update_fake_profile(user_id: int, **kwargs):
    conn = get_conn()
    c = conn.cursor()
    allowed = {"name", "age", "city", "lat", "lon", "bio", "interests", "last_active"}
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = %s")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(user_id)
    c.execute(f"UPDATE profiles SET {', '.join(fields)} WHERE user_id = %s", values)
    conn.commit()
    conn.close()
    return True


def get_fake_profiles() -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE is_fake = 1 ORDER BY user_id")
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        p = dict(r)
        p["photos"] = get_photos(r["user_id"])
        result.append(p)
    return result


def update_last_active(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE profiles SET last_active = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()


def get_profile(user_id: int) -> Optional[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    p = dict(row)
    p["photos"] = get_photos(user_id)
    return p


def get_lang(user_id: int) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT lang FROM user_settings WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    return row["lang"] if row else ""


def set_lang(user_id: int, lang: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_settings (user_id, lang) VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET lang = EXCLUDED.lang
    """, (user_id, lang))
    conn.commit()
    conn.close()


def get_filters(user_id: int) -> Dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM filters WHERE user_id = %s", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {"min_age": 18, "max_age": 99, "city_filter": "", "radius_km": 0, "use_location": 0, "filter_lat": None, "filter_lon": None}
    return dict(row)


def set_filters(user_id: int, min_age: int, max_age: int, city_filter: str, radius_km: int = 0,
                use_location: int = 0, filter_lat=None, filter_lon=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO filters (user_id, min_age, max_age, city_filter, radius_km, use_location, filter_lat, filter_lon)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
        min_age = EXCLUDED.min_age, max_age = EXCLUDED.max_age,
        city_filter = EXCLUDED.city_filter, radius_km = EXCLUDED.radius_km,
        use_location = EXCLUDED.use_location, filter_lat = EXCLUDED.filter_lat,
        filter_lon = EXCLUDED.filter_lon
    """, (user_id, min_age, max_age, city_filter, radius_km, use_location, filter_lat, filter_lon))
    conn.commit()
    conn.close()


def get_next_profile(user_id: int, looking_for: str, filters: Dict, my_lat=None, my_lon=None) -> Optional[Dict]:
    conn = get_conn()
    c = conn.cursor()

    c.execute("SELECT to_user FROM actions WHERE from_user = %s", (user_id,))
    seen = [r["to_user"] for r in c.fetchall()]
    seen.append(user_id)

    placeholders = ','.join(['%s'] * len(seen)) if seen else '0'

    query = f"""
        SELECT * FROM profiles
        WHERE user_id NOT IN ({placeholders})
        AND age BETWEEN %s AND %s
    """
    params = seen + [filters["min_age"], filters["max_age"]]

    if looking_for != "all":
        query += " AND gender = %s"
        params.append(looking_for)

    if filters.get("city_filter") and not filters.get("use_location"):
        query += " AND city = %s"
        params.append(filters["city_filter"])

    query += " ORDER BY RANDOM() LIMIT 50"

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    candidates = []
    for row in rows:
        p = dict(row)
        p["photos"] = get_photos(row["user_id"])
        if filters.get("use_location") and filters.get("radius_km", 0) > 0:
            if my_lat is not None and p["lat"] is not None:
                dist = haversine(my_lat, my_lon, p["lat"], p["lon"])
                if dist <= filters["radius_km"]:
                    p["distance_km"] = round(dist, 1)
                    candidates.append(p)
        else:
            candidates.append(p)

    if not candidates:
        return None
    import random
    return random.choice(candidates)


def add_action(from_user: int, to_user: int, action: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO actions (from_user, to_user, action)
        VALUES (%s, %s, %s)
        ON CONFLICT (from_user, to_user) DO UPDATE SET action = EXCLUDED.action, created_at = CURRENT_TIMESTAMP
    """, (from_user, to_user, action))
    conn.commit()
    conn.close()


def check_mutual_like(user1: int, user2: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM actions
        WHERE ((from_user = %s AND to_user = %s) OR (from_user = %s AND to_user = %s))
        AND action IN ('heart', 'crown')
    """, (user1, user2, user2, user1))
    count = c.fetchone()["count"]
    conn.close()
    return count >= 2


def save_match(user1: int, user2: int):
    conn = get_conn()
    c = conn.cursor()
    a, b = sorted([user1, user2])
    c.execute("""
        INSERT INTO matches (user1, user2) VALUES (%s, %s)
        ON CONFLICT (user1, user2) DO NOTHING
    """, (a, b))
    conn.commit()
    conn.close()


def get_matches(user_id: int) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT p.* FROM profiles p
        JOIN matches m ON (p.user_id = m.user1 OR p.user_id = m.user2)
        WHERE (m.user1 = %s OR m.user2 = %s) AND p.user_id != %s
    """, (user_id, user_id, user_id))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        p = dict(r)
        p["photos"] = get_photos(r["user_id"])
        result.append(p)
    return result


def get_likes_received(user_id: int) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT p.* FROM profiles p
        JOIN actions a ON p.user_id = a.from_user
        WHERE a.to_user = %s AND a.action IN ('heart', 'crown')
        AND a.from_user NOT IN (
            SELECT to_user FROM actions WHERE from_user = %s
        )
        ORDER BY a.created_at DESC
    """, (user_id, user_id))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        p = dict(r)
        p["photos"] = get_photos(r["user_id"])
        result.append(p)
    return result


def delete_profile(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM profiles WHERE user_id = %s", (user_id,))
    c.execute("DELETE FROM photos WHERE user_id = %s", (user_id,))
    c.execute("DELETE FROM filters WHERE user_id = %s", (user_id,))
    c.execute("DELETE FROM actions WHERE from_user = %s OR to_user = %s", (user_id, user_id))
    c.execute("DELETE FROM matches WHERE user1 = %s OR user2 = %s", (user_id, user_id))
    conn.commit()
    conn.close()


def get_stats() -> Dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM profiles WHERE is_fake = 0")
    real = c.fetchone()["count"]
    c.execute("SELECT COUNT(*) FROM profiles WHERE is_fake = 1")
    fake = c.fetchone()["count"]
    c.execute("SELECT COUNT(*) FROM matches")
    matches = c.fetchone()["count"]
    conn.close()
    return {"real": real, "fake": fake, "matches": matches}


def is_verified(user_id: int) -> bool:
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT verified FROM profiles WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        conn.close()
        return bool(row["verified"]) if row else False
    except Exception:
        return True


def verify_user(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE profiles SET verified = 1 WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()


def get_actions_count(user_id: int) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM actions WHERE from_user = %s", (user_id,))
    count = c.fetchone()["count"]
    conn.close()
    return count


init_db()
