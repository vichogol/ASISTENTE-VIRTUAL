
"""Read-only FAQ snapshots and normalization shared by both retrieval paths."""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from openpyxl import load_workbook

EXCEL = Path(__file__).resolve().parents[3] / "data/raw/preguntas_frecuentes_penalolen.xlsx"
URL = re.compile(r"(?:https?://|www\.)[^\s<>]+", re.I)
PRIVATE = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|"
    r"\b(?:\d{1,2}\.?\d{3}\.?\d{3}-[\dkK])\b|"
    r"(?<!\w)\+?\d(?:[ .-]*\d){7,}(?!\w)", re.I,
)


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in folded if not unicodedata.combining(c))))


def redact(text: str) -> str:
    return PRIVATE.sub("[dato omitido]", URL.sub("[enlace omitido]", text))


def web_url(value: str) -> str | None:
    value = value.strip().rstrip(".,;:)]}")
    if value.lower().startswith("www."):
        value = "https://" + value
    try:
        address = urlsplit(value)
        if address.scheme in {"https", "http"} and address.hostname and not address.username:
            return value
    except ValueError:
        pass
    return None


class FAQHTML(HTMLParser):
    blocks = {"br", "p", "div", "ul", "ol", "li", "tr"}
    skipped = {"script", "style"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.links: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.skipped:
            self.hidden += 1
        if self.hidden:
            return
        if tag in self.blocks:
            self.parts.append("\n• " if tag == "li" else "\n")
        if tag == "a":
            href = web_url(dict(attrs).get("href") or "")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.skipped:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in self.blocks:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def clean_answer(raw: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    parser = FAQHTML()
    parser.feed(raw)
    parser.close()
    text = "".join(parser.parts)
    text = re.sub(r"([^\s])\s*•", r"\1\n• ", text)
    text = re.sub(r"(?<!\n)[ \t]+(?=\([1-9]\)\s)", "\n", text)
    for match in URL.finditer(text):
        link = web_url(match.group())
        if link:
            parser.links.append(link)
    lines = tuple(line for raw_line in text.splitlines() if (line := " ".join(raw_line.split())))
    return lines, tuple(dict.fromkeys(parser.links))


def is_active(value: object) -> bool:
    try:
        return float(str(value)) == 1.0 if str(value).lower() != "nan" else True
    except ValueError:
        return True


@dataclass(frozen=True)
class FAQ:
    key: str
    row_id: int
    sheet: str
    reviewed: bool
    question: str
    unit: str
    category: str
    tags: str
    lines: tuple[str, ...]
    links: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def revision(self) -> str:
        content = "\n".join((self.question, self.unit, self.category, self.text, *self.links))
        return hashlib.sha256(content.encode()).hexdigest()

    def source(self) -> dict[str, str | int]:
        return {
            "id": self.row_id, "pregunta": self.question, "direccion": self.unit,
            "categoria": self.category, "hoja": self.sheet, "revision": self.revision,
        }


@lru_cache(maxsize=4)
def read_faqs(path: Path, modified_ns: int, size: int) -> tuple[FAQ, ...]:
    """The file stat is part of the cache key so replacing the workbook refreshes it."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    records: list[FAQ] = []
    try:
        for sheet in workbook:
            rows = iter(sheet.values)
            headers = next(rows, ())
            if not {"preguntaFrecuenteID", "nombrePreguntaFrecuente", "descripcionPreguntaFrecuente"} <= set(headers):
                continue
            for row in rows:
                record = dict(zip(headers, row))
                if not is_active(record.get("isActivo")):
                    continue
                try:
                    row_id = int(record["preguntaFrecuenteID"])
                except (ValueError, TypeError):
                    continue
                question = str(record.get("nombrePreguntaFrecuente") or "").strip()
                lines, links = clean_answer(str(record.get("descripcionPreguntaFrecuente") or ""))
                if question and lines:
                    records.append(FAQ(
                        f"{sheet.title}:{row_id}", row_id, sheet.title, sheet.sheet_state == "visible",
                        question, str(record.get("Direccion") or "").strip(),
                        " ".join(str(record.get("categoriaPreguntaFrecuente") or "").split()),
                        str(record.get("tagPreguntaFrecuente") or ""), lines, links,
                    ))
    finally:
        workbook.close()
    return tuple(records)
