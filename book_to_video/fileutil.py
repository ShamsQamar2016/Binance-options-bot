"""Файлларни хавфсиз ёзиш ва ўқиш.

Файл аввал вақтинчалик номга тўлиқ ёзилади, кейин бир ҳаракатда асл номга алмаштирилади. Шунда
жараён ёзиш пайтида узилса ҳам, ёки бошқа поток (thread) уни шу пайт ўқиса ҳам, чала файл қолмайди.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


def temp_name(path: Path) -> Path:
    """Шу жараён ва шу поток учун ноёб вақтинчалик ном (кенгайтма сақланади)."""
    path = Path(path)
    return path.with_name(f".{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp{path.suffix}")


def write_text_atomic(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = temp_name(path)
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json_atomic(path: Path, data) -> None:
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=1))


def read_json_cache(path: Path, default):
    """Кеш файлини ўқийди. Йўқ ёки бузилган бўлса — default (кеш қайта тўлдирилади)."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except (ValueError, OSError) as exc:
        logger.warning("Бузилган кеш файли эътиборсиз қолдирилди: %s (%s)", path, exc)
        return default
