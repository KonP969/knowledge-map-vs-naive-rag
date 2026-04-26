import json
from pathlib import Path
from typing import Any, Dict

DATA_DIR = Path(__file__).parent / "data"
DOCUMENTS_FILE = DATA_DIR / "documents.json"
CHUNKS_FILE = DATA_DIR / "chunks.json"
FOLDERS_FILE = DATA_DIR / "folders.json"


def _ensure_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
