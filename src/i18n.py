from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"
DEFAULT_LANGUAGE = "zh-CN"


def _normalize_language(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANGUAGE
    normalized = lang.strip().replace("_", "-")
    if normalized.lower() in {"zh", "zh-cn", "zh-hans", "zh-hans-cn"}:
        return "zh-CN"
    if normalized.lower() in {"en", "en-us", "en-us-posix"}:
        return "en-US"
    return normalized


def _load_json(path: Path) -> Dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    out: Dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


@dataclass(frozen=True)
class I18n:
    language: str
    messages: Dict[str, str]

    @staticmethod
    def load(language: str | None = None) -> "I18n":
        lang = _normalize_language(language)
        base = _load_json(I18N_DIR / f"{DEFAULT_LANGUAGE}.json")
        overlay = _load_json(I18N_DIR / f"{lang}.json")
        merged = dict(base)
        merged.update(overlay)
        return I18n(language=lang, messages=merged)

    def t(self, key: str, **kwargs: Any) -> str:
        text = self.messages.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text
