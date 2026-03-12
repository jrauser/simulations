"""Shared hex-grid utilities used by all hex-based simulations."""

import math

# Flat-top axial neighbor directions (q, r)
HEX_DIRECTIONS = [(1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]


def hex_cells(radius):
    """Return frozenset of all (q, r) axial coords with max(|q|, |r|, |s|) <= radius."""
    cells = set()
    for q in range(-radius, radius + 1):
        for r in range(-radius, radius + 1):
            if max(abs(q), abs(r), abs(q + r)) <= radius:
                cells.add((q, r))
    return frozenset(cells)


def _clamp_to_hex(q, r, radius):
    """Project out-of-bounds cube coords to a nearby valid cell in O(1).

    Used as a fallback when modular wrap alone doesn't produce a valid cell.
    """
    q = max(-radius, min(radius, q))
    r = max(-radius, min(radius, r))
    s = -q - r
    if abs(s) > radius:
        s = max(-radius, min(radius, s))
        q = -r - s
    return q, r


def build_neighbor_table(cells, radius):
    """Precompute toroidally-wrapped 6-neighbor list for every cell.

    For out-of-bounds neighbors, tries modular wrap on each axial component
    first. Falls back to clamping the antipodal position to the valid arena.
    """
    d = 2 * radius + 1
    table = {}
    for q, r in cells:
        nbrs = []
        for dq, dr in HEX_DIRECTIONS:
            nq, nr = q + dq, r + dr
            if (nq, nr) in cells:
                nbrs.append((nq, nr))
            else:
                wq = (nq + radius) % d - radius
                wr = (nr + radius) % d - radius
                ws = -wq - wr
                if max(abs(wq), abs(wr), abs(ws)) <= radius:
                    nbrs.append((wq, wr))
                else:
                    nbrs.append(_clamp_to_hex(-nq, -nr, radius))
        table[(q, r)] = nbrs
    return table


def hex_to_pixel(q, r, cell_size, ox, oy):
    """Pixel center of a flat-top hex cell at axial (q, r)."""
    x = ox + cell_size * 1.5 * q
    y = oy + cell_size * math.sqrt(3) * (r + q / 2.0)
    return x, y


def hex_corners(cx, cy, size):
    """Six corner points of a flat-top hexagon centered at (cx, cy)."""
    return [
        (
            cx + size * math.cos(math.radians(60 * i)),
            cy + size * math.sin(math.radians(60 * i)),
        )
        for i in range(6)
    ]


def compute_hex_layout(radius, canvas_rect):
    """Return (cell_size, ox, oy) to center a hex arena of given radius in canvas_rect."""
    margin = 12
    usable_w = canvas_rect.width - 2 * margin
    usable_h = canvas_rect.height - 2 * margin
    cell_from_w = usable_w / (3 * radius + 2)
    cell_from_h = usable_h / ((2 * radius + 1) * math.sqrt(3))
    cell_size = min(cell_from_w, cell_from_h)
    return cell_size, canvas_rect.centerx, canvas_rect.centery
