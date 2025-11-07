from pathlib import Path

# Путь до корневой директории проекта. Он будет правильным даже при изменении текущей рабочей директории (CWD)
ROOT_DIR = Path(__file__).parent.parent.parent

SERVER_DIR = Path(__file__).parent.parent

DATA_DIR = ROOT_DIR / "data"
PRIVATE_DATA_DIR = DATA_DIR / "private"

ENV_FILE = SERVER_DIR / ".env"
