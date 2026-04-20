"""Extrae fecha del nombre de archivo y la compara con el mtime.

Si la fecha del nombre es anterior al mtime, se asume que el mtime fue
modificado (ej. copia reciente de foto antigua) y se usa la del nombre.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path

_DATE_RE = re.compile(
    r"(?<!\d)(19\d{2}|20\d{2}|21\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)"
)
_TIME_RE = re.compile(r"(?<!\d)([01]\d|2[0-3])[-_.:]?([0-5]\d)[-_.:]?([0-5]\d)(?!\d)")


def date_from_filename(name: str) -> float | None:
    """Devuelve timestamp epoch si encuentra YYYY-MM-DD (o variantes) en el nombre."""
    m = _DATE_RE.search(name)
    if not m:
        return None
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        dt = datetime(year, month, day, 12, 0, 0)
    except ValueError:
        return None
    if dt.timestamp() > time.time() + 86400:
        return None

    # Buscar hora después de la fecha para mayor precisión
    tail = name[m.end():]
    tm = _TIME_RE.search(tail)
    if tm:
        try:
            dt = dt.replace(
                hour=int(tm.group(1)),
                minute=int(tm.group(2)),
                second=int(tm.group(3)),
            )
        except ValueError:
            pass
    return dt.timestamp()


def effective_mtime(path: str | os.PathLike) -> float:
    """mtime del archivo, o la fecha del nombre si esta última es anterior."""
    p = Path(path)
    mtime = p.stat().st_mtime
    fn_date = date_from_filename(p.name)
    if fn_date is not None and fn_date < mtime:
        return fn_date
    return mtime
