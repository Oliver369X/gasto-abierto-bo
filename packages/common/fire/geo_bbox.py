"""Approximate bounding boxes for first-wave department assignment."""
from __future__ import annotations

from decimal import Decimal

# (min_longitude, min_latitude, max_longitude, max_latitude)
DEPT_BBOX: dict[str, tuple[float, float, float, float]] = {
    "Santa Cruz": (-64.50, -20.60, -57.30, -13.30),
    "Beni": (-67.70, -16.60, -62.60, -10.20),
    "Pando": (-69.70, -12.60, -65.10, -9.60),
}


def assign_department(
    latitude: float | Decimal | str,
    longitude: float | Decimal | str,
) -> str | None:
    lat, lon = float(latitude), float(longitude)
    for department, (min_lon, min_lat, max_lon, max_lat) in DEPT_BBOX.items():
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            return department
    return None
