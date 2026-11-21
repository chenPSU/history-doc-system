"""Licence classes for downloaded assets (TASKS P3.2).

classify() maps a free-text or URL licence to one class:
  pd        public domain (PD mark, PD-old, PD-Art, "no known restrictions")
  cc0       CC0 dedication
  cc-by     CC BY (any version)
  cc-by-sa  CC BY-SA (any version)
  nc        any NonCommercial licence (never usable on a monetised channel)
  nd        any NoDerivatives licence (we always crop, zoom and grade)
  unknown   everything else, including GFDL-only and "all rights reserved"
Only classes listed in config/assets.yaml -> allowed_licences are downloaded. Unknown is never downloaded.
"""
from __future__ import annotations

import re

CLASSES = ("pd", "cc0", "cc-by", "cc-by-sa", "nc", "nd", "unknown")
NEEDS_CREDIT = {"cc-by", "cc-by-sa"}


def classify(text: str | None) -> str:
    t = (text or "").strip().lower()
    if not t:
        return "unknown"
    t = t.replace("_", "-")
    if re.search(r"\bnc\b|-nc\b|noncommercial|non-commercial", t):
        return "nc"
    if re.search(r"\bnd\b|-nd\b|noderiv|no-deriv", t):
        return "nd"
    if "cc0" in t or "cc-zero" in t or "publicdomain/zero" in t:
        return "cc0"
    if (t in ("pd", "public domain") or t.startswith("pd-") or "publicdomain/mark" in t
            or "public domain" in t or "no known restrictions" in t):
        return "pd"
    if re.search(r"by-sa|attribution-sharealike|cc by sa", t):
        return "cc-by-sa"
    if re.search(r"cc-by\b|cc by\b|licenses/by/|attribution", t):
        return "cc-by"
    return "unknown"


def allowed(cls: str, allowed_classes) -> bool:
    return cls != "unknown" and cls in set(allowed_classes)
