"""Compatibility imports for callers using the original core module."""

from .errors import ScoutError as ScoutError
from .files import (
    now as now,
    identifier as identifier,
    atomic_json as atomic_json,
    read_json as read_json,
    file_lock as file_lock,
)
from .geometry import (
    number as number,
    point as point,
    distance as distance,
    angles as angles,
    cell as cell,
)
from .library import Library as Library
from .transport import Bridge as Bridge
