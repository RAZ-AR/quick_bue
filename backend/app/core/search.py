"""Builds products.search_text: all names lowercased + Armenian and Cyrillic in Latin letters.

A buyer may type «պանիր», «сыр», «panir» or «syr»; trigram search over this one string finds all of them.
"""

_HY = {
    "ա": "a", "բ": "b", "գ": "g", "դ": "d", "ե": "e", "զ": "z", "է": "e", "ը": "y", "թ": "t", "ժ": "zh",
    "ի": "i", "լ": "l", "խ": "kh", "ծ": "ts", "կ": "k", "հ": "h", "ձ": "dz", "ղ": "gh", "ճ": "ch", "մ": "m",
    "յ": "y", "ն": "n", "շ": "sh", "ո": "o", "չ": "ch", "պ": "p", "ջ": "j", "ռ": "r", "ս": "s", "վ": "v",
    "տ": "t", "ր": "r", "ց": "ts", "ւ": "v", "փ": "p", "ք": "k", "օ": "o", "ֆ": "f", "և": "ev",
}  # fmt: skip
_RU = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}  # fmt: skip
_TABLE = str.maketrans({**_HY, **_RU})


def transliterate(text: str) -> str:
    # "ու" is one sound (u), handle it before single letters
    return text.lower().replace("ու", "u").translate(_TABLE)


def build_search_text(*parts: str | dict | None) -> str:
    words: list[str] = []
    for part in parts:
        if not part:
            continue
        values = part.values() if isinstance(part, dict) else [part]
        for value in values:
            if value:
                words.append(value.lower())
                latin = transliterate(value)
                if latin != value.lower():
                    words.append(latin)
    return " ".join(dict.fromkeys(words))  # dedupe, keep order
