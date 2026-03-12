# Turtles — Implementation Plan

## Overview

Single-file Python simulation (`turtles.py`) using pygame. Implements Schelling's segregation
model on a toroidal hexagonal grid. Two animal types (turtles and frogs) want their neighbors
to be "mostly like them"; unhappy animals hop to a random empty neighboring cell.

Two new shared modules are introduced: `hex_utils.py` and `ui.py`. Both are extracted from
existing code; all four simulation files import from them.

---

## Shared Modules

### `hex_utils.py`

`hex_to_pixel` and `hex_corners` are defined identically in both `termites.py` and `ants.py`
(verified: the two implementations are mathematically the same, just formatted differently).
`HEX_DIRECTIONS` also appears in both, with the same 6 directions in different rotational
orders — a single canonical ordering can be chosen. `hex_cells` and `build_neighbor_table`
are currently termites-only but turtles also needs them.

Exports:

```python
HEX_DIRECTIONS       # 6 flat-top axial neighbor offsets, canonical order
hex_to_pixel(q, r, size, ox, oy) -> (float, float)
hex_corners(cx, cy, size) -> list[tuple]
hex_cells(radius) -> frozenset[tuple]
build_neighbor_table(cells, radius) -> dict[tuple, list[tuple]]
```

Not moved here: `hex_distance`, `HEX_DIR_ANGLES`, `heading_to_hex_dir` — these are
ants-specific and have no use in the other sims.

Existing files to update: remove the local definitions of the above from `termites.py`
and `ants.py` and replace with `from hex_utils import ...`.

---

### `ui.py`

The `Slider` class is copy-pasted verbatim across all three existing simulations. The only
differences are cosmetic: `termites.py` appends a `%` suffix for fractional steps;
`bees.py` uses `.1f`; `ants.py` uses `:g`. The canonical version uses `:g` (simple,
handles both int and float naturally).

Beyond `Slider`, three more things are identical in all three files:

1. **Five UI colors** — `COLOR_PANEL`, `COLOR_PANEL_BORDER`, `COLOR_SLIDER_TRACK`,
   `COLOR_SLIDER_THUMB`, `COLOR_LABEL` — all have the exact same values in every file.
   Move them to `ui.py` as module-level constants.

2. **`draw_panel(screen, font, control_rect, sliders)`** — the 3-line block that fills the
   control rect, draws the top border line, and calls `slider.draw()` for each slider is
   identical in all three `main()` loops. Extract it as a function.

3. **`slider_row_geometry(control_rect, n, pad)`** — each `make_sliders` function computes
   the same layout formula: `sw = (width - (n+1)*pad) // n`, `sy = y + 40`, `sh = 24`,
   `x0 = x + pad`. A helper returning `(x0, sy, sw, sh)` removes this boilerplate.
   (The per-sim `pad` values differ — 12, 15, 20 — so `pad` stays a parameter.)

`ui.py` exports:

```python
COLOR_PANEL, COLOR_PANEL_BORDER        # (35,35,35), (60,60,60)
COLOR_SLIDER_TRACK, COLOR_SLIDER_THUMB # (80,80,80), (180,180,180)
COLOR_LABEL                            # (200,200,200)

class Slider:
    def __init__(self, label, x, y, w, h, lo, hi, default, step=1): ...
    def handle_event(self, event) -> bool: ...
    def draw(self, screen, font): ...

def draw_panel(screen, font, control_rect, sliders): ...
def slider_row_geometry(control_rect, n, pad=15) -> (x0, sy, sw, sh): ...
```

Existing files to update: remove the local `Slider` class and the five color constants from
`termites.py`, `ants.py`, and `bees.py`; replace with `from ui import ...`.

---

## Coordinate System & Grid

Uses the flat-top hex grid with axial (q, r) coordinates, imported from `hex_utils.py`.
Grid is all cells with max(|q|, |r|, |q+r|) ≤ radius. The "Size" slider controls radius.
Toroidal wrapping is handled by `build_neighbor_table` (same approach as termites).

---

## Simulation Class

### `World`

State:
- `radius: int`
- `cells: frozenset[tuple[int,int]]`
- `neighbor_table: dict[tuple, list[tuple]]` — precomputed toroidal neighbors
- `grid: dict[tuple, str | None]` — `'T'` (turtle), `'F'` (frog), or `None` (empty)
- `preference: float` — min fraction of same-type among occupied neighbors to be happy

Constructor: `World(radius, density, preference)`
- Fill `grid` with `None` for all cells
- Choose `round(len(cells) * density)` cells at random; assign half `'T'`, half `'F'`
- Store `preference`

Methods:
- `step()` — pick one random occupied cell; check happiness; if unhappy, hop
- `is_happy(q, r) -> bool`
- `empty_neighbors(q, r) -> list[tuple]`

### Happiness Rule

Count the animal's occupied neighbors; compute the fraction that are the same type.
Happy if fraction ≥ `preference`.

**Decision: denominator is occupied neighbors only**, not all 6.
Rationale: "0 same-type out of 0 occupied" would unconditionally flag every isolated
animal as unhappy, causing chaotic movement at low densities regardless of preference.
Edge case: zero occupied neighbors → happy.

### Step Logic

```
pick a random occupied cell (q, r)
if is_happy(q, r): return
empties = empty_neighbors(q, r)
if not empties: return          # surrounded, can't move
target = random.choice(empties)
grid[target] = grid[(q, r)]
grid[(q, r)] = None
```

---

## Rendering

```
WINDOW_WIDTH   = 900
WINDOW_HEIGHT  = 740
CONTROL_HEIGHT = 110
```

Colors (sim-specific, defined in `turtles.py`):
- Background: `(20, 20, 20)`
- Turtle: `(80, 190, 100)` (green)
- Frog: `(220, 130, 50)` (orange)
- Empty cell: `(45, 45, 45)` (dim gray)
- Panel/slider colors: imported from `ui.py`

Cell rendering: filled hexagons via `hex_corners`; fall back to `set_at` when
`cell_size < 1.5`.

Optional (first pass: skip): tint unhappy animals slightly darker.

---

## Controls

| Slider     | Range     | Default | Step | Resets? |
|------------|-----------|---------|------|---------|
| Size (N)   | 3 – 40    | 15      | 1    | Yes     |
| Density    | 10 – 90   | 70      | 1    | Yes     |
| Preference | 0 – 100   | 33      | 1    | Yes     |
| Speed      | 1 – 2000  | 100     | 1    | No      |

Density and Preference display as percentages; Size and Speed as plain integers.
All non-speed sliders reset the world when touched.

---

## Main Loop

```
init pygame
world = new_world()
epoch_accum = 0.0

while running:
    dt = clock.tick(60) / 1000.0
    handle events; if non-speed slider changed: world = new_world(), epoch_accum = 0.0
    epoch_accum += speed_s.value * dt
    n_steps = int(epoch_accum); epoch_accum -= n_steps
    for _ in range(n_steps): world.step()
    render(screen, world, ...)
    draw_panel(screen, font, control_rect, sliders)   # from ui.py
    pygame.display.flip()
```

Speed is in steps/second. At default 100 steps/sec × 60 fps ≈ 1.7 steps/frame.

---

## File Structure

```
hex_utils.py
  HEX_DIRECTIONS, hex_to_pixel, hex_corners      # used by termites, ants, turtles
  hex_cells, build_neighbor_table                # used by termites, turtles

ui.py
  COLOR_PANEL, COLOR_PANEL_BORDER, ...           # 5 shared colors
  class Slider
  draw_panel(screen, font, control_rect, sliders)
  slider_row_geometry(control_rect, n, pad)

turtles.py
  # --- Constants (sim-specific colors) ---
  # --- class World ---
  # --- Rendering ---
  # --- Main ---
```

Changes to existing files: `termites.py`, `ants.py`, `bees.py` each lose their `Slider`
class and 5 color constants; `termites.py` and `ants.py` also lose their local hex utility
definitions. All replaced with imports.

---

## Open Questions / Decisions

| Question | Decision |
|----------|----------|
| Happiness denominator | Occupied neighbors only (0 occupied → happy) |
| Movement rule | Hop to random empty neighbor; if none available, stay put |
| 50/50 split enforcement | Exact: `floor(n/2)` turtles, `ceil(n/2)` frogs |
| Unhappy visual indicator | Skip for first pass |
| Speed slider units | Steps per second (each step = one animal selected at random) |
| `HEX_DIRECTIONS` ordering | Use termites.py ordering (already matches torus wrap logic) |
