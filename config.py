import os

# Cấu hình Token & Server
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
PORT = int(os.environ.get("PORT", 10000))

# Cấu hình danh mục giải Vietlott
GAME_CONFIG = {
    "655": {"name": "Power 6/55", "max_num": 55, "pick": 6, "type": "standard"},
    "645": {"name": "Mega 6/45", "max_num": 45, "pick": 6, "type": "standard"},
    "3d": {"name": "Max 3D", "length": 3, "type": "digit"},
    "keno": {"name": "Keno", "max_num": 80, "pick": 20, "type": "standard"},
}

# Đường dẫn Database
DB_FILE = "vietlott.db"
