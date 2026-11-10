"""Китоб файлини ўқиш: .txt, .md, .pdf, .docx"""

from pathlib import Path


def read_book(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        # Ўзбек/рус матнлари кўпинча UTF-8 ёки Windows-1251 да бўлади
        for encoding in ("utf-8", "utf-8-sig", "cp1251"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Файл кодировкасини аниқлаб бўлмади: {path}")

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        import docx

        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)

    raise ValueError(f"Қўллаб-қувватланмайдиган формат: {suffix} (.txt, .pdf, .docx бўлиши керак)")


def split_into_chunks(text: str, max_chars: int) -> list[str]:
    """Матнни абзацлар бўйича бўлакларга ажратади (абзац ўртасидан кесмайди)."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in text.split("\n"):
        if current_len + len(paragraph) > max_chars and current:
            chunks.append("\n".join(current))
            current, current_len = [], 0
        # Жуда узун абзацни мажбуран бўлиш
        while len(paragraph) > max_chars:
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        current.append(paragraph)
        current_len += len(paragraph) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks
