from typing import Optional


def format_number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def format_signed_number(value: int) -> str:
    prefix = "+" if value > 0 else ""
    return f"{prefix}{format_number(value)}"


def format_percent(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}%"


def safe_text(value: Optional[str], fallback: str = "н/д") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback
