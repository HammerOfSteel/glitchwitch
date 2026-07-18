"""Low-poly mesh kit: flat-shaded faces UV-mapped onto palette cells.

Every face duplicates its vertices (flat normals — the toy-render look) and
maps all of them to the center of one palette cell. Deterministic: pure math,
coordinates rounded before export.
"""
from __future__ import annotations

import math

from . import palette

ROUND = 5


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize(v):
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if length < 1e-12:
        return (0.0, 1.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


def rotate_y(point, angle):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    x, y, z = point
    return (x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a)


class MeshBuilder:
    """Accumulates flat-shaded, palette-mapped faces."""

    def __init__(self) -> None:
        self.positions = []
        self.normals = []
        self.uvs = []
        self.indices = []

    @property
    def tri_count(self) -> int:
        return len(self.indices) // 3

    @property
    def vertex_count(self) -> int:
        return len(self.positions)

    def add_face(self, points, ramp: str, shade: int) -> None:
        """Add a convex face (3+ points, CCW winding seen from outside)."""
        if len(points) < 3:
            raise ValueError("face needs at least 3 points")
        normal = _normalize(_cross(_sub(points[1], points[0]), _sub(points[2], points[0])))
        uv = palette.cell_uv(ramp, shade)
        base = len(self.positions)
        for point in points:
            self.positions.append(tuple(round(c, ROUND) for c in point))
            self.normals.append(tuple(round(c, ROUND) for c in normal))
            self.uvs.append(uv)
        for i in range(1, len(points) - 1):
            self.indices.extend((base, base + i, base + i + 1))

    def merge(self, other: "MeshBuilder", offset=(0.0, 0.0, 0.0), yaw: float = 0.0) -> None:
        base = len(self.positions)
        for position in other.positions:
            point = rotate_y(position, yaw) if yaw else position
            self.positions.append(tuple(round(point[i] + offset[i], ROUND) for i in range(3)))
        for normal in other.normals:
            rotated = rotate_y(normal, yaw) if yaw else normal
            self.normals.append(tuple(round(c, ROUND) for c in rotated))
        self.uvs.extend(other.uvs)
        self.indices.extend(base + i for i in other.indices)


def add_box(builder: MeshBuilder, center, size, ramp: str, shade: int,
            top=None, bottom=None) -> None:
    """Axis-aligned box. Optional (ramp, shade) overrides for top/bottom faces."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    top = top or (ramp, shade)
    bottom = bottom or (ramp, max(shade - 1, 0))
    # corners: 0..7
    c = [
        (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz + hz),
        (cx - hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz - hz),
        (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
    ]
    builder.add_face([c[4], c[5], c[6], c[7]], *top)          # +Y
    builder.add_face([c[3], c[2], c[1], c[0]], *bottom)       # -Y
    builder.add_face([c[7], c[6], c[2], c[3]], ramp, shade)   # +Z
    builder.add_face([c[5], c[4], c[0], c[1]], ramp, shade)   # -Z
    builder.add_face([c[6], c[5], c[1], c[2]], ramp, shade)   # +X
    builder.add_face([c[4], c[7], c[3], c[0]], ramp, shade)   # -X


def add_lathe(builder: MeshBuilder, profile, segments: int, ramp: str, shade: int,
              center=(0.0, 0.0, 0.0), cap_start: bool = False, cap_end: bool = False,
              shade_top=None) -> None:
    """Revolve a profile of (radius, y) pairs around the Y axis.

    Consecutive profile points become quad rings. Caps close the first/last
    ring with a triangle fan when the radius is non-zero.
    """
    if len(profile) < 2:
        raise ValueError("lathe profile needs at least 2 points")
    cx, cy, cz = center

    def ring_point(radius, y, segment):
        angle = (2.0 * math.pi * segment) / segments
        return (cx + radius * math.cos(angle), cy + y, cz + radius * math.sin(angle))

    for i in range(len(profile) - 1):
        r0, y0 = profile[i]
        r1, y1 = profile[i + 1]
        face_shade = shade_top if (shade_top is not None and i == len(profile) - 2) else shade
        for segment in range(segments):
            nxt = (segment + 1) % segments
            p00 = ring_point(r0, y0, segment)
            p01 = ring_point(r0, y0, nxt)
            p10 = ring_point(r1, y1, segment)
            p11 = ring_point(r1, y1, nxt)
            if r0 < 1e-9:
                builder.add_face([p00, p11, p10], ramp, face_shade)
            elif r1 < 1e-9:
                builder.add_face([p00, p01, p10], ramp, face_shade)
            else:
                builder.add_face([p00, p01, p11, p10], ramp, face_shade)
    if cap_start and profile[0][0] > 1e-9:
        radius, y = profile[0]
        points = [ring_point(radius, y, s) for s in range(segments)]
        _fan(builder, (cx, cy + y, cz), points, ramp, shade, up=False)
    if cap_end and profile[-1][0] > 1e-9:
        radius, y = profile[-1]
        points = [ring_point(radius, y, s) for s in range(segments)]
        _fan(builder, (cx, cy + y, cz), points, ramp, shade_top if shade_top is not None else shade, up=True)


def _fan(builder: MeshBuilder, center, ring, ramp: str, shade: int, up: bool) -> None:
    count = len(ring)
    for i in range(count):
        nxt = (i + 1) % count
        if up:
            builder.add_face([center, ring[nxt], ring[i]], ramp, shade)
        else:
            builder.add_face([center, ring[i], ring[nxt]], ramp, shade)


def add_cylinder(builder: MeshBuilder, center, radius: float, height: float,
                 segments: int, ramp: str, shade: int,
                 cap_bottom: bool = True, cap_top: bool = True, shade_top=None) -> None:
    add_lathe(
        builder,
        [(radius, -height / 2.0), (radius, height / 2.0)],
        segments, ramp, shade, center=center,
        cap_start=cap_bottom, cap_end=cap_top, shade_top=shade_top,
    )


def add_cone(builder: MeshBuilder, center, radius: float, height: float,
             segments: int, ramp: str, shade: int, cap: bool = True) -> None:
    add_lathe(
        builder,
        [(radius, 0.0), (0.0, height)],
        segments, ramp, shade, center=center, cap_start=cap,
    )
