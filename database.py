import sqlite3
import math
from datetime import datetime, timedelta
from typing import Optional, List, Dict

DB_NAME = "dating.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
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

    # Миграции: добавляем колонки если таблица уже существует
    for col in ["interests", "verified"]:
        try:
            c.execute(f"ALTER TABLE profiles ADD COLUMN {col} TEXT" if col == "interests" else f"ALTER TABLE profiles ADD COLUMN {col} INTEGER DEFAULT 0")
        except:
            pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            photo_file_id TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'ru'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS filters (
            user_id INTEGER PRIMARY KEY,
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER NOT NULL,
            to_user INTEGER NOT NULL,
            action TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(from_user, to_user)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1 INTEGER NOT NULL,
            user2 INTEGER NOT NULL,
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if last_active is None:
        c.execute("""
            INSERT OR REPLACE INTO profiles
            (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake))
    else:
        c.execute("""
            INSERT OR REPLACE INTO profiles
            (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, age, city, lat, lon, gender, looking_for, bio, interests, is_fake, last_active))
    conn.commit()
    conn.close()


def add_photo(user_id: int, photo_file_id: str, sort_order: int = 0):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO photos (user_id, photo_file_id, sort_order) VALUES (?, ?, ?)",
              (user_id, photo_file_id, sort_order))
    conn.commit()
    conn.close()


def get_photos(user_id: int) -> List[str]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT photo_file_id FROM photos WHERE user_id = ? ORDER BY sort_order", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def delete_photos(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM photos WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_fake_profile(user_id: int, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    allowed = {"name", "age", "city", "lat", "lon", "bio", "interests", "last_active"}
    fields = []
    values = []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        conn.close()
        return False
    values.append(user_id)
    c.execute(f"UPDATE profiles SET {', '.join(fields)} WHERE user_id = ?", values)
    conn.commit()
    conn.close()
    return True


def get_fake_profiles() -> List[Dict]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE is_fake = 1 ORDER BY user_id")
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        p = {
            "user_id": r[0], "name": r[1], "age": r[2], "city": r[3],
            "lat": r[4], "lon": r[5],
            "gender": r[6], "looking_for": r[7], "bio": r[8], "interests": r[9],
            "is_fake": r[10], "verified": r[11], "last_active": r[12]
        }
        p["photos"] = get_photos(r[0])
        result.append(p)
    return result


def update_last_active(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE profiles SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_profile(user_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    p = {
        "user_id": row[0], "name": row[1], "age": row[2], "city": row[3],
        "lat": row[4], "lon": row[5],
        "gender": row[6], "looking_for": row[7], "bio": row[8], "interests": row[9],
        "is_fake": row[10], "verified": row[11], "last_active": row[12]
    }
    p["photos"] = get_photos(user_id)
    return p


def get_lang(user_id: int) -> str:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT lang FROM user_settings WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""


def set_lang(user_id: int, lang: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_settings (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    conn.close()


def get_filters(user_id: int) -> Dict:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM filters WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {"min_age": 18, "max_age": 99, "city_filter": "", "radius_km": 0, "use_location": 0, "filter_lat": None, "filter_lon": None}
    return {"min_age": row[1], "max_age": row[2], "city_filter": row[3], "radius_km": row[4], "use_location": row[5], "filter_lat": row[6], "filter_lon": row[7]}


def set_filters(user_id: int, min_age: int, max_age: int, city_filter: str, radius_km: int = 0,
                use_location: int = 0, filter_lat=None, filter_lon=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO filters (user_id, min_age, max_age, city_filter, radius_km, use_location, filter_lat, filter_lon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, min_age, max_age, city_filter, radius_km, use_location, filter_lat, filter_lon))
    conn.commit()
    conn.close()


def get_next_profile(user_id: int, looking_for: str, filters: Dict, my_lat=None, my_lon=None) -> Optional[Dict]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT to_user FROM actions WHERE from_user = ?", (user_id,))
    seen = [r[0] for r in c.fetchall()]
    seen.append(user_id)

    placeholders = ','.join('?' * len(seen)) if seen else '0'

    query = f"""
        SELECT * FROM profiles
        WHERE user_id NOT IN ({placeholders})
        AND age BETWEEN ? AND ?
    """
    params = seen + [filters["min_age"], filters["max_age"]]

    if looking_for != "all":
        query += " AND gender = ?"
        params.append(looking_for)

    if filters.get("city_filter") and not filters.get("use_location"):
        query += " AND city = ?"
        params.append(filters["city_filter"])

    query += " ORDER BY RANDOM() LIMIT 50"

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    candidates = []
    for row in rows:
        p = {
            "user_id": row[0], "name": row[1], "age": row[2], "city": row[3],
            "lat": row[4], "lon": row[5],
            "gender": row[6], "looking_for": row[7], "bio": row[8], "interests": row[9],
            "is_fake": row[10], "verified": row[11], "last_active": row[12]
        }
        p["photos"] = get_photos(row[0])
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO actions (from_user, to_user, action)
        VALUES (?, ?, ?)
    """, (from_user, to_user, action))
    conn.commit()
    conn.close()


def check_mutual_like(user1: int, user2: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM actions
        WHERE ((from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?))
        AND action IN ('like', 'crown')
    """, (user1, user2, user2, user1))
    count = c.fetchone()[0]
    conn.close()
    return count >= 2


def save_match(user1: int, user2: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    a, b = sorted([user1, user2])
    c.execute("""
        INSERT OR IGNORE INTO matches (user1, user2)
        VALUES (?, ?)
    """, (a, b))
    conn.commit()
    conn.close()


def get_matches(user_id: int) -> List[Dict]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT p.* FROM profiles p
        JOIN matches m ON (p.user_id = m.user1 OR p.user_id = m.user2)
        WHERE (m.user1 = ? OR m.user2 = ?) AND p.user_id != ?
    """, (user_id, user_id, user_id))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        p = {
            "user_id": r[0], "name": r[1], "age": r[2], "city": r[3],
            "lat": r[4], "lon": r[5],
            "gender": r[6], "bio": r[8], "interests": r[9],
            "is_fake": r[10], "verified": r[11], "last_active": r[12]
        }
        p["photos"] = get_photos(r[0])
        result.append(p)
    return result


def get_likes_received(user_id: int) -> List[Dict]:
    """Возвращает анкеты тех, кто лайкнул меня, но я ещё не видел (нет взаимного действия)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        SELECT p.* FROM profiles p
        JOIN actions a ON p.user_id = a.from_user
        WHERE a.to_user = ? AND a.action IN ('like', 'crown')
        AND a.from_user NOT IN (
            SELECT to_user FROM actions WHERE from_user = ?
        )
        ORDER BY a.created_at DESC
    """, (user_id, user_id))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        p = {
            "user_id": r[0], "name": r[1], "age": r[2], "city": r[3],
            "lat": r[4], "lon": r[5],
            "gender": r[6], "bio": r[8], "interests": r[9],
            "is_fake": r[10], "verified": r[11], "last_active": r[12]
        }
        p["photos"] = get_photos(r[0])
        result.append(p)
    return result


def delete_profile(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM photos WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM filters WHERE user_id = ?", (user_id,))
    c.execute("DELETE FROM actions WHERE from_user = ? OR to_user = ?", (user_id, user_id))
    c.execute("DELETE FROM matches WHERE user1 = ? OR user2 = ?", (user_id, user_id))
    conn.commit()
    conn.close()


def get_stats() -> Dict:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM profiles WHERE is_fake = 0")
    real = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM profiles WHERE is_fake = 1")
    fake = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM matches")
    matches = c.fetchone()[0]
    conn.close()
    return {"real": real, "fake": fake, "matches": matches}


def is_verified(user_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT verified FROM profiles WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return bool(row[0]) if row else False
    except sqlite3.OperationalError:
        # Колонки verified нет в старой БД — считаем всех верифицированными
        return True


def verify_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE profiles SET verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_actions_count(user_id: int) -> int:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM actions WHERE from_user = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count


init_db()
