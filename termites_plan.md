# Termites Simulation — Implementation Plan

## Overview

Single-file Python simulation (`termites.py`) using pygame. Two classes: `Arena` and `Termite`. All simulation logic lives in these classes; pygame rendering code is kept strictly separate in a render/UI section.

---

## Coordinate System

Hex grid with flat-top orientation, cube coordinates (q, r, s where q+r+s=0). The six neighbor directions for flat-top hex are:

```
(+1, -1, 0), (+1, 0, -1), (0, +1, -1)
(-1, +1, 0), (-1, 0, +1), (0, -1, +1)
```

Toroidal wrapping is applied after each step. Wrapping on a hex grid requires care: map cube coords to offset coords, apply modulo, map back. The arena "size" parameter N defines a hex grid of radius N (i.e., all cells with max(|q|,|r|,|s|) <= N), giving `3N²+3N+1` cells total. Alternatively, a simpler rectangular region in offset coords could be used — this is a decision point worth resolving before coding, as it affects wrapping logic significantly.

**Decision: use hex-radius grid** — all cells with max(|q|,|r|,|s|) <= N form a hexagonal arena of radius N, giving `3N²+3N+1` cells. The "size" slider controls N. Toroidal wrapping maps cube coords that fall outside the radius back to their mirror position on the opposite side, achieved by wrapping each axial component modulo the grid diameter `(2N+1)` and re-deriving s.

---

## Classes

### `Arena`

State:
- `radius: int` — N, defines the hex-radius grid
- `cells: set[tuple[int,int]]` — all valid (q, r) axial coords in the arena
- `chips: set[tuple[int,int]]` — set of (q, r) cells containing a woodchip
- `termites: list[Termite]`

Methods:
- `__init__(radius, termite_density, chip_density)` — populate randomly
- `step()` — run one epoch: shuffle termite list, call `termite.act(arena)` for each
- `wrap(q, r) -> tuple[int,int]` — apply toroidal wrapping to keep coords in the hex-radius arena
- `neighbors(q, r) -> list[tuple[int,int]]` — returns 6 neighbors with toroidal wrapping applied
- `has_chip(q, r) -> bool`
- `add_chip(q, r)`, `remove_chip(q, r)`

### `Termite`

State:
- `q`, `r` — current position in axial cube coords
- `carrying: bool` — whether holding a chip

Methods:
- `act(arena: Arena)` — execute one move per the rules:
  1. If emptyhanded: step to a random neighbor; if new cell has chip, pick it up.
  2. If carrying and current cell has a chip: find a random neighbor with no chip and drop there; if none, stay put.
  3. If carrying and current cell has no chip: step to a random neighbor.

---

## Simulation Rules (clarifications)

- "Empty cell" for dropping means no woodchip (termites don't block).
- A carrying termite checks drop conditions *before* any movement. If it steps (case 3), it does not re-check drop conditions after the step — that happens next epoch.
- Termites can freely share cells at all times.
- Initial placement: chips and termites placed randomly; overlaps allowed.

---

## Rendering

Window layout:
- Top: hex grid canvas (most of the window)
- Bottom: control panel with 4 sliders

Hex cell rendering:
- Compute pixel center of each hex cell from (col, row) using standard flat-top hex math
- Draw a filled hexagon for each cell with a chip (tan color)
- Draw a small filled circle for each termite: red if carrying, blue if empty
- When a carrying termite is on a chip cell, both are drawn (chip hex underneath, termite circle on top)
- Background: dark (near-black)

Colors:
- Background: `(20, 20, 20)`
- Chip: `(210, 180, 140)` (tan)
- Carrying termite: `(200, 80, 60)` (reddish)
- Empty termite: `(80, 130, 210)` (blue)

---

## Controls

Four pygame-gui (or hand-rolled) sliders:

| Slider | Range | Default | Resets sim? |
|--------|-------|---------|-------------|
| Arena size (radius N) | 3–20 | 8 | Yes |
| Termite density | 1–30% | 5% | Yes |
| Chip density | 5–60% | 20% | Yes |
| Speed (epochs/sec) | 1–200 | 20 | No |

Changing any non-speed slider calls `reset()` which reinitializes the Arena and Termite list.

**Library choice:** Use `pygame` only (no pygame-gui dependency) with hand-rolled sliders. Keeps dependencies minimal.

---

## Main Loop

```
init pygame
create arena from defaults
while running:
    handle events (quit, slider interactions)
    if slider changed (non-speed): reset arena
    run N epochs based on speed setting and elapsed time
    render arena + controls
    tick clock
```

Speed slider controls epochs per second. On each frame, accumulate elapsed time and run `floor(elapsed * speed)` epochs, carrying over fractional remainder.

---

## File Structure

```
termites.py
  # --- Constants / Config ---
  # --- Hex coordinate utilities ---
  # --- class Termite ---
  # --- class Arena ---
  # --- Rendering functions ---
  # --- Slider UI ---
  # --- Main ---
```

---

## Open Questions / Decisions Made

| Question | Decision |
|----------|----------|
| Grid topology | Hex-radius (all cells with max(|q|,|r|,|s|) <= N) for aesthetics |
| Overlap on init | Allowed (chips and termites can share cells initially) |
| Drop after step | No — carrying termite only drops at start of move, not after stepping |
| UI library | Pure pygame, hand-rolled sliders |
| Tests | Not written, but coordinate/wrapping logic should be carefully verified manually |
