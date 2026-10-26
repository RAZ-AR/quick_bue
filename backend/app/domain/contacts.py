"""Contact details of a company: Armenian phone numbers, e-mail, bank account. Pure functions.

Kept in step with web/src/lib/contacts.ts (the form checks as you type, the server has the last word).
"""

import re

# Armenian numbers have 8 digits after +374: a 2-digit mobile/Yerevan code + 6 digits,
# or a 3-digit regional code + 5 digits. Nothing starts with 0 after the country code.
_NSN = re.compile(r"^[1-9]\d{7}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")

# Mailbox providers people in Armenia use; a domain one or two letters off is likely a typo
COMMON_DOMAINS = (
    "gmail.com",
    "mail.ru",
    "yandex.ru",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "inbox.ru",
    "list.ru",
    "bk.ru",
    "rambler.ru",
    "protonmail.com",
)


def normalize_phone(raw: str | None) -> str | None:
    """'091 23-45-67', '+37491234567', '374 91 234567' → '+374 91 234 567'; None if not an Armenian number."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("00374"):
        digits = digits[5:]
    elif digits.startswith("374") and len(digits) == 11:
        digits = digits[3:]
    elif digits.startswith("0") and len(digits) == 9:
        digits = digits[1:]
    if not _NSN.match(digits):
        return None
    return f"+374 {digits[:2]} {digits[2:5]} {digits[5:]}"


def _distance(a: str, b: str) -> int:
    """Levenshtein distance, small strings only."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def normalize_email(raw: str | None) -> str | None:
    email = (raw or "").strip().lower()
    return email if _EMAIL.match(email) and len(email) <= 320 else None


def email_suggestion(email: str) -> str | None:
    """'ani@gmial.com' → 'ani@gmail.com'; None when the domain looks fine or unknown."""
    local, _, domain = email.partition("@")
    if not domain or domain in COMMON_DOMAINS:
        return None
    best = min(COMMON_DOMAINS, key=lambda d: _distance(domain, d))
    return f"{local}@{best}" if _distance(domain, best) <= 2 else None


def normalize_bank_account(raw: str | None) -> str | None:
    """Armenian bank accounts are 16 digits (the first 3 are the bank's code)."""
    digits = re.sub(r"[\s-]", "", raw or "")
    return digits if re.fullmatch(r"\d{16}", digits) else None


def check(fields: dict) -> tuple[dict, list[dict]]:
    """Normalized phone / email / bank_account from `fields` (only the keys present) and problems."""
    out, problems = {}, []
    rules = (
        ("phone", normalize_phone, "bad_phone"),
        ("email", normalize_email, "bad_email"),
        ("bank_account", normalize_bank_account, "bad_bank_account"),
    )
    for key, normalize, code in rules:
        if key not in fields:
            continue
        value = fields[key]
        if value is None or not str(value).strip():
            out[key] = None
            continue
        normalized = normalize(value)
        if normalized is None:
            problems.append({"field": key, "code": code})
        else:
            out[key] = normalized
    return out, problems
