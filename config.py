import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8759646429:AAHGdOl59I7KNJCFR8gW688lke06gs_Wo68")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8930867864"))

MIN_AGE = 18
MAX_AGE = 99
MAX_BIO_LENGTH = 300

# Настройки фейков
FAKE_COUNT = 50

# === ВЕРИФИКАЦИЯ ===
VERIFICATION_REQUIRED = os.getenv("VERIFICATION_REQUIRED", "True").lower() in ("true", "1", "yes")
VERIFICATION_AFTER_LIKES = int(os.getenv("VERIFICATION_AFTER_LIKES", "5"))

# Telethon API
API_ID = int(os.getenv("API_ID", "32863589"))
API_HASH = os.getenv("API_HASH", "aabbec6f1df02695d71b84dea7a77411")
