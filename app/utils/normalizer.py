import re
from datetime import time
from typing import Optional


def normalize_time(time_str: Optional[str]) -> Optional[time]:
    if not time_str:
        return None

    s = str(time_str).strip()
    if not s or s.lower() in ["null", "none", ""]:
        return None

    # Normalize common variants
    s = s.replace("O", "0").replace("o", "0").replace(" ", "")
    s = s.replace(".", ":")

    # Try patterns
    patterns = [
        r"^(\d{1,2}):(\d{2})$",
    ]

    for pattern in patterns:
        m = re.match(pattern, s)
        if m:
            h = int(m.group(1))
            mm = int(m.group(2))
            if h < 0 or h > 23 or mm < 0 or mm > 59:
                return None
            return time(hour=h, minute=mm)

    # Try just hour
    m2 = re.match(r"^(\d{1,2})$", s)
    if m2:
        h = int(m2.group(1))
        if h < 0 or h > 23:
            return None
        return time(hour=h, minute=0)

    return None


def normalize_name(name_str: Optional[str]) -> Optional[str]:
    if not name_str:
        return None
    s = str(name_str).strip()
    if not s or s.lower() in ["null", "none", ""]:
        return None
    # Keep as is but normalize whitespace
    s = re.sub(r"\s+", " ", s)
    return s.upper()
