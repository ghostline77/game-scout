"""Camera geometry and bounded numeric inputs."""

from __future__ import annotations

import math

from .errors import ScoutError


def number(value, minimum, maximum, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ScoutError(f"{name} must be finite and between {minimum} and {maximum}")
    return float(value)


def point(value):
    return {a: number(value[a], -100000, 100000, a) for a in "xyz"}


def distance(a, b):
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in "xyz"))


def angles(origin, target):
    delta = {k: target[k] - origin[k] for k in "xyz"}
    if distance(origin, target) < 0.01:
        raise ScoutError("Look-at target is at the camera origin")
    return dict(
        yaw=math.degrees(math.atan2(-delta["x"], delta["y"])) % 360,
        pitch=math.degrees(math.atan2(delta["z"], math.hypot(delta["x"], delta["y"]))),
    )


def cell(pose, size=8):
    # Full 3D cells keep balconies and spaces under bridges distinct.
    return ":".join(str(math.floor(pose[a] / size)) for a in "xyz")
