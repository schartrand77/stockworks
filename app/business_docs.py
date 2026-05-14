"""Helpers for storing and scanning generic business document PDFs."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pypdf import PdfReader


@dataclass(frozen=True)
class BusinessDocumentScan:
    vendor: Optional[str]
    receipt_date: Optional[str]
    total: Optional[str]
    display_name: str


DATE_PATTERN = re.compile(
    r"\b(?P<date>(?:20\d{2}|19\d{2})[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])"
    r"|(?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])[-/.](?:20\d{2}|19\d{2})"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+"
    r"(?:0?[1-9]|[12]\d|3[01]),?\s+(?:20\d{2}|19\d{2}))\b",
    re.IGNORECASE,
)
TOTAL_PATTERN = re.compile(
    r"\b(?:grand\s+total|amount\s+paid|balance\s+due|total)\b[^\d$-]*"
    r"(?P<total>\$?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
    re.IGNORECASE,
)
BAMBU_VENDOR_PATTERN = re.compile(r"\bBambu\s+Labs?(?:\s+CA)?\b", re.IGNORECASE)


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def scan_business_document_pdf(pdf_path: Path, source_filename: str) -> BusinessDocumentScan:
    return scan_business_document_text(extract_pdf_text(pdf_path), source_filename=source_filename)


def scan_business_document_text(text: str, source_filename: str) -> BusinessDocumentScan:
    cleaned_lines = [_clean_spaces(line) for line in text.splitlines()]
    lines = [line for line in cleaned_lines if line]
    vendor = _extract_known_vendor(text) or _extract_vendor(lines)
    receipt_date = _extract_date(text)
    total = _extract_total(text)
    if vendor and receipt_date and total:
        display_name = f"{vendor} - {receipt_date} - {total}"
    else:
        display_name = _fallback_name(source_filename)
    return BusinessDocumentScan(
        vendor=vendor,
        receipt_date=receipt_date,
        total=total,
        display_name=display_name,
    )


def _extract_known_vendor(text: str) -> Optional[str]:
    match = BAMBU_VENDOR_PATTERN.search(text)
    if not match:
        return None
    vendor = _clean_spaces(match.group(0))
    return "Bambu Lab CA" if vendor.lower().endswith(" ca") else "Bambu Lab"


def _extract_vendor(lines: list[str]) -> Optional[str]:
    ignored_prefixes = (
        "receipt",
        "invoice",
        "tax invoice",
        "date",
        "order",
        "total",
        "subtotal",
        "amount",
        "thank you",
    )
    for line in lines[:12]:
        normalized = line.strip(" :-").strip()
        if not normalized:
            continue
        lower = normalized.lower()
        if any(lower.startswith(prefix) for prefix in ignored_prefixes):
            continue
        if DATE_PATTERN.search(normalized) or TOTAL_PATTERN.search(normalized):
            continue
        return normalized[:120]
    return None


def _extract_date(text: str) -> Optional[str]:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    return match.group("date").replace("/", "-").replace(".", "-")


def _extract_total(text: str) -> Optional[str]:
    matches = list(TOTAL_PATTERN.finditer(text))
    if not matches:
        return None
    raw_total = matches[-1].group("total")
    compact = re.sub(r"\s+", "", raw_total)
    if compact.startswith("$"):
        return compact
    return f"${compact}"


def _fallback_name(source_filename: str) -> str:
    name = Path(source_filename or "business-document.pdf").stem
    name = _clean_spaces(name.replace("_", " ").replace("-", " "))
    return name or "business document"


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
