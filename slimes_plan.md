# Slimes — Implementation Plan

## Overview

Single-file simulation (`slimes.py`) using pygame. Slime mold aggregation on a toroidal hex
grid. Slimes perform a random walk until local pheromone exceeds a threshold, then climb the
pheromone gradient. Pheromone is emitted by slimes each turn, and diffuses and evaporates
each epoch.

---

## Epoch Structure

Each call to `world.step()` does three things in order:

1. **All slimes act** — shuffled into random order; each slime emits pheromone then
   (possibly) moves
2. **Diffusion** — one pass across all patches, spreading pheromone to neighbors
3. **Evaporation** — one pass across all patches, decaying pheromone by the evaporation
   rate

Pheromone and diffusion/evaporation are parameterized by sliders and can be changed live
without resetting (see Controls).

---

## Classes

### `World`

State:
- `cells: frozenset[tuple]`
- `neighbor_table: dict[tuple, list[tuple]]` — precomputed toroidal neighbors
- `pheromone: dict[tuple, float]` — initialized to 0.0 for all cells
- `occupied: set[tuple]` — O(1) cell occupancy lookup
- `slimes: list[Slime]`
- `drop: float`, `threshold: float`, `evaporation: float`, `diffusion: float`
  — all live-updatable from the main loop (no reset needed when changed)

Constructor: `World(radius, density, drop, threshold, evaporation, diffusion)`
- Build cells and neighbor table from hex_utils
- Populate `pheromone` with 0.0 for all cells
- Randomly place `round(len(cells) * density)` slimes

`step()`:
```
shuffle slimes; for each slime: slime.act(self)

# Two-phase diffusion (avoids order-dependence)
inflow = {cell: 0.0 for cell in cells}
for cell in cells:
    ph = pheromone[cell]
    if ph > 0:
        out = ph * diffusion
        for nbr in neighbor_table[cell]:
            inflow[nbr] += out
        pheromone[cell] -= out * len(neighbor_table[cell])
for cell in cells:
    pheromone[cell] = (pheromone[cell] + inflow[cell]) * (1 - evaporation)
    if pheromone[cell] < 0.001:
        pheromone[cell] = 0.0   # prevent float drift
```

### `Slime`

State:
- `pos: tuple[int, int]`

`act(world)`:
```
world.pheromone[pos] += world.drop         # emit first

empties = [n for n in neighbor_table[pos] if n not in world.occupied]

if world.pheromone[pos] >= world.threshold:
    # Seeking: move to empty neighbor with highest pheromone
    if empties:
        target = max(empties, key=lambda n: world.pheromone[n])
        # break ties randomly among all maximal neighbors
        move(target)
else:
    # Wandering: move to a random empty neighbor
    if empties:
        move(random.choice(empties))
```

`move(target)`:
```
world.occupied.remove(pos)
world.occupied.add(target)
pos = target
```

**Decision: the pheromone just emitted counts toward the threshold check.** This means a
slime that returns to a cell it recently visited may cross the threshold on its own emission,
triggering seeking. This is intentional — it creates the positive feedback needed for
aggregation to bootstrap.

**No empty neighbors:** in either mode, the slime stays put if all 6 neighbors are occupied.

**Tie-breaking in seeking mode:** among all empty neighbors that share the maximum pheromone
value, choose randomly. Using `max()` directly gives a deterministic tie-break (first in
iteration order), but randomizing is more biologically plausible and prevents artifacts.

---

## Rendering

Colors:
- Background: `(10, 10, 10)`
- Pheromone: lerp from background to `(180, 220, 60)` (yellow-green) based on pheromone
  level, saturating at `PHEROMONE_VIS_MAX = 20.0`
- Slime: `(230, 255, 100)` (bright yellow-green, drawn on top of pheromone)

Each cell is a filled hexagon. Cells with zero pheromone and no slime show only as a faint
grid; `COLOR_CELL = (25, 25, 25)` is drawn as the base before the pheromone overlay.

At small cell sizes (`cell_size < 1.5`), fall back to `set_at` for pheromone, skip the
circle for slimes and use `set_at` instead.

Slimes are drawn as small circles (`r = max(1, int(cell_size * 0.35))`).

Rendering order per cell: background → pheromone overlay → (slime if present).
Since slimes need to be drawn on top, do two passes: all cells first, then all slimes.

---

## Controls

Seven sliders — all except Evap %, Diffusion %, and Speed reset the simulation when touched:

| Slider      | Range        | Default | Step | Resets? |
|-------------|-------------|---------|------|---------|
| Size (N)    | 3 – 40      | 40      | 1    | Yes     |
| Population  | 1 – 50 (%)  | 5       | 1    | Yes     |
| Drop        | 0.1 – 5.0   | 1.0     | 0.1  | Yes     |
| Threshold   | 0.5 – 10.0  | 2.0     | 0.5  | Yes     |
| Evap %      | 1 – 50      | 10      | 1    | No      |
| Diffusion % | 0 – 20      | 5       | 1    | No      |
| Speed       | 1 – 500     | 50      | 1    | No      |

Evaporation and Diffusion are made live-update (no reset) because adjusting the physics
mid-run while watching the pheromone field respond is interesting and doesn't require a
fresh start. Population, Drop, Threshold, and Size affect the world structure meaningfully
enough to warrant a reset.

Seven sliders is one more than any other sim. With 7 sliders at `pad=10`:
`sw = (900 - 8×10) // 7 = 117px` per slider — tight but readable at font size 18.

---

## Diffusion Default

2% per neighbor (as in ants.py) is conservative. Recommend 5% as default: with 6 neighbors,
each cell loses up to 30% of its pheromone via diffusion before evaporation. Combined with
10% evaporation that's a reasonably fast decay, but enough gradient survives to guide slimes.
The slider allows tuning.

---

## File Structure

```
slimes.py
  # --- Constants ---
  # --- lerp_color (copy from ants.py or add to hex_utils) ---
  # --- class Slime ---
  # --- class World ---
  # --- Rendering ---
  # --- Main ---
```

`lerp_color` is currently defined in `ants.py` only. Rather than adding it to `hex_utils.py`
(it's not hex-specific), just copy the 5-line function into `slimes.py` directly. If a third
sim needs it, promote it to `ui.py` then.

---

## Open Questions / Decisions

| Question | Decision |
|----------|----------|
| Epoch structure | Slimes act (all, random order), then diffuse, then evaporate |
| Self-emission counts toward threshold | Yes — enables bootstrap feedback |
| No empty neighbor | Stay put in both seeking and wandering modes |
| Tie-breaking in seeking | Random among all tied-max empty neighbors |
| Population control | Density % (consistent with termites) |
| Evap/diffusion: reset on change? | No — interesting to adjust live |
| `lerp_color` home | Copy into slimes.py; promote to ui.py if a third sim needs it |
| Initial pheromone | All zeros |
| Grid size slider? | Yes — Size (N), radius 3–40, default 15, resets sim |
