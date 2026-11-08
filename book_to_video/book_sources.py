"""Китобни олиш: локал файл, URL ҳавола ёки Telegram ботга юборилган файл.

Китоб манбаини сиз танлайсиз: скрипт интернетдан ўзи қидирмайди, чунки
тасодифий сайтлардан рухсатсиз (пират) нусха олиб қўйиш хавфи бор.
"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

import requests

import telegram_sender as tg
from book_reader import read_book

SUPPORTED = (".txt", ".md", ".pdf", ".docx", ".fb2", ".epub")


def download_from_url(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        name = Path(unquote(urlparse(url).path)).name or "book"
        disposition = r.headers.get("content-disposition", "")
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', disposition)
        if m:
            name = unquote(m.group(1))
        if not name.lower().endswith(SUPPORTED):
            ctype = r.headers.get("content-type", "")
            name += ".pdf" if "pdf" in ctype else ".txt"
        path = dest_dir / name
        with open(path, "wb") as f:
            for part in r.iter_content(1 << 20):
                f.write(part)
    return path


def download_from_telegram(dest_dir: Path) -> Path:
    """Ботга (TELEGRAM_CHAT_ID чатидан) охирги юборилган китоб файлини юклаб олади."""
    doc = tg.latest_document_from_admin()
    if not doc:
        raise RuntimeError("Ботга китоб файли юборилмаган. Ботга .pdf/.docx/.fb2/.epub/.txt файл юборинг.")
    return tg.download_file(doc["file_id"], dest_dir / doc.get("file_name", "book.txt"))


def _strip_html(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    markup = re.sub(r"(?i)</(p|div|h\d|br|li)>|<br\s*/?>", "\n", markup)
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def _read_fb2(path: Path) -> str:
    root = ElementTree.parse(path).getroot()
    paragraphs = [
        "".join(el.itertext()) for el in root.iter() if el.tag.split("}")[-1] in ("p", "title", "subtitle")
    ]
    return "\n".join(paragraphs)


def _read_epub(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
        return "\n".join(_strip_html(z.read(n).decode("utf-8", errors="ignore")) for n in names)


def load_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".fb2":
        text = _read_fb2(path)
    elif suffix == ".epub":
        text = _read_epub(path)
    else:
        text = read_book(path)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 2000:
        raise RuntimeError(f"Китоб матни жуда қисқа ({len(text)} белги) — файл тўғрими? (сканер қилинган PDF матнсиз бўлади)")
    return text
