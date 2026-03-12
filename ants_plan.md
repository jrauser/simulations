# Ants Simulation — Implementation Plan

## Overview

Single-file Python simulation (`ants.py`) using pygame. Classes: `Patch`, `Ant`, and `World`. Inspired by Resnick's StarLogo: the world is a hex grid of patch objects, each of which participates actively each turn (pheromone decay). Shares the `Slider` UI pattern from `termites.py` and `bees.py`.

---

## World

- **Hex grid**: flat-top hexagons in axial (q, r) coordinates. Colony at (q=0, r=0).
- **World radius**: 40 patches (all hexes with hex-distance ≤ 40 from origin). Total ~5,000 patches.
- **Hex size**: dynamically calculated so the grid fills the canvas — `hex_size = canvas_w / ((2 * WORLD_RADIUS + 1) * 1.5 + 0.5)`.
- **Scale**: ~0.5m per patch → ~40m foraging radius, which is realistic for small ants.
- **Boundary**: ants at the world edge are simply blocked (no valid neighbor outside radius).

---

## Patches

Each patch is an object with:

```python
class Patch:
    q: int          # axial coordinate
    r: int          # axial coordinate
    pheromone: float  # ≥ 0.0
    food_count: int   # 0 = empty; >0 = food present
```

**Every simulation step**, each patch updates:
- `pheromone *= PHEROMONE_DECAY`  (e.g. `PHEROMONE_DECAY = 0.985` per step)

Pheromone has no cap but realistically plateaus when deposit rate ≈ decay rate.

---

## Food Placement

- `n_clusters` cluster centers are placed at random hexes with hex-distance between `FOOD_MIN_DIST` (e.g. 15) and `WORLD_RADIUS - 5` from origin.
- Each cluster seeds food on all patches within hex-distance 3 of the center → ~37 patches per cluster.
- Each food patch starts with `food_count = FOOD_START` (default 10, slider-controlled via Depletion).

---

## Ant States

```
IN_COLONY ──(P_EXIT)──> EXPLORING ──(on food patch)──> CARRYING
                              │         │                    │
                         (detects       └──(tired)──> RETURNING
                          pheromone)                        ↑    │ (reaches colony)
                              │                             │   ↓
                              └──────────────> FOLLOWING   │  IN_COLONY
                                                   │  └──(tired)
                                              (food patch)
                                                   └──> CARRYING
                                              (pheromone lost)
                                                   └──> EXPLORING
```

### State Descriptions

| State | Behavior |
|-------|----------|
| `IN_COLONY` | Invisible. Each step: exit with probability `P_EXIT` (default 3%) → `EXPLORING`. Set a random initial heading and draw a fresh `fatigue_limit` from exponential distribution (mean = `ANT_FATIGUE`). |
| `EXPLORING` | Random walk: each step pick the neighbor closest to current heading ± small noise (heading drifts by σ=30° per step). Reflects off boundary. Increments `fatigue` counter; if `fatigue ≥ fatigue_limit` → `RETURNING`. If current patch has `food_count > 0` → pick up food, decrement `food_count`, → `CARRYING`. If any neighbor has pheromone above `PHEROMONE_THRESHOLD` → `FOLLOWING`. |
| `CARRYING` | Step toward colony with noise (heading toward colony ± σ=20°). Deposit `PHEROMONE_DEPOSIT` on current patch each step. On reaching colony patch (hex-distance = 0) → `IN_COLONY`. No fatigue check — ant is already heading home. |
| `FOLLOWING` | Move to the neighbor with the **lowest** pheromone among neighbors with pheromone above `PHEROMONE_THRESHOLD` (down-gradient → toward food). Increments `fatigue`; if `fatigue ≥ fatigue_limit` → `RETURNING`. If current patch has `food_count > 0` → `CARRYING`. If no neighbors have pheromone above threshold (trail lost) → `EXPLORING`. |
| `RETURNING` | Tired ant heading home with no food. Step toward colony with noise (same σ as CARRYING). No pheromone deposit. On reaching colony → `IN_COLONY`. |

**Fatigue variation**: `fatigue_limit` is drawn from `int(random.expovariate(1.0 / ANT_FATIGUE))` at the moment the ant exits the colony. The exponential distribution gives wide variation (some ants tire quickly, others linger) which prevents the synchronized returning waves seen in bees when a fixed fatigue limit is used.

**Pheromone gradient direction**: pheromone is deposited only while returning home. The first ant to find food lays pheromone starting at the food source; the trail is freshest/strongest near the colony (where pheromone is youngest) and oldest/weakest near the food (most time to decay). Following *down*-gradient (toward weaker pheromone) leads toward food.

---

## Parameters and Defaults

| Parameter | Value | Notes |
|-----------|-------|-------|
| `WORLD_RADIUS` | 40 patches | Fixed |
| `PHEROMONE_DECAY` | 0.985 per step | Exponential decay |
| `PHEROMONE_DEPOSIT` | 5.0 | Per step while CARRYING |
| `PHEROMONE_THRESHOLD` | 0.1 | Minimum to detect / follow |
| `P_EXIT` | 0.03 | Per-step exit probability |
| `MAX_OUTSIDE_FRACTION` | 0.6 | Cap on ants outside colony |
| `FOOD_START` | 10 | Default visits before depletion |
| `FOOD_MIN_DIST` | 15 | Minimum hex distance from colony |
| `ANT_FATIGUE` | 120 steps | Mean fatigue (exponential distribution) |
| `EXPLORE_TURN_SIGMA` | 30° | Heading drift per step in EXPLORING |
| `CARRY_TURN_SIGMA` | 20° | Noise when heading home |
| Default ants | 100 | Slider-controlled |
| Default food clusters | 5 | Slider-controlled |

---

## Hex Navigation Utilities

```python
# Flat-top axial hex neighbors (6 directions)
HEX_DIRECTIONS = [(+1,0),(+1,-1),(0,-1),(-1,0),(-1,+1),(0,+1)]

def hex_distance(q1, r1, q2, r2):
    return (abs(q1-q2) + abs(q1+r1-q2-r2) + abs(r1-r2)) // 2

def hex_to_pixel(q, r, hex_size, origin_x, origin_y):
    # Flat-top layout
    x = hex_size * (3/2 * q)
    y = hex_size * (sqrt(3)/2 * q + sqrt(3) * r)
    return origin_x + x, origin_y + y

def pixel_to_hex(px, py, hex_size, origin_x, origin_y):
    # Inverse of above, then cube-round
    ...
```

A dict `patches: dict[(q,r), Patch]` stores all valid patches.

**Navigating toward colony**: among the 6 neighbors, pick the one with smallest `hex_distance(nq, nr, 0, 0)`, then add turn noise by sometimes picking the second-best neighbor with probability derived from `CARRY_TURN_SIGMA`.

**Navigating in EXPLORING**: maintain a float `heading` (radians). Each step: `heading += N(0, EXPLORE_TURN_SIGMA)`. Convert heading to the nearest of the 6 hex directions and move there if valid.

---

## Rendering

**Patch colors** are computed each frame:

1. Base color by food state:
   - No food, no pheromone: `PATCH_BASE = (30, 22, 15)` (dark dirt)
   - Food active: `FOOD_COLOR = (60, 180, 60)` (green), blended toward base as food depletes
   - Food depleted: `FOOD_DEPLETED = (25, 55, 25)` (dark green)
2. Pheromone overlay: blend in `PHEROMONE_COLOR = (80, 180, 255)` (cyan) proportional to `min(pheromone / PHEROMONE_VIS_MAX, 1.0)` where `PHEROMONE_VIS_MAX ≈ 20.0`.

```python
def patch_color(patch):
    base = food_color(patch)
    t = min(patch.pheromone / PHEROMONE_VIS_MAX, 1.0)
    return lerp_color(base, PHEROMONE_COLOR, t)
```

**Hexes** are drawn as filled polygons (flat-top) each frame. No persistent trail surface needed — pheromone on patches serves as the trail.

**Colony**: amber filled circle at center, radius ~hex_size * 1.5.

**Ants**: colored dots (radius 3px) drawn on their patch center:
- `IN_COLONY`: invisible
- `EXPLORING`: `(220, 200, 120)` (sandy yellow)
- `CARRYING`: `(220, 90, 50)` (orange-red)
- `FOLLOWING`: `(100, 220, 255)` (bright cyan)
- `RETURNING`: same color as `EXPLORING` (tired ant looks like any other outbound ant)

---

## Rendering Performance

With ~5,000 patches drawn as polygons each frame at moderate speed, performance may be acceptable but needs monitoring. Optimization options if needed:
- Pre-cache hex polygon vertex lists (only translate by patch center).
- Skip drawing patches with default color (no food, no pheromone) using a dirty-patch set.
- Use `pygame.draw.polygon` for hex_size ≥ 4, `screen.set_at` for smaller.

---

## Controls

Three sliders:

| Slider | Range | Default | Resets? |
|--------|-------|---------|---------|
| Ants | 10–400 | 100 | Yes |
| Food Clusters | 1–15 | 5 | Yes |
| Speed | 1–300 steps/sec | 20 | No |

Touching Ants or Food Clusters resets the simulation. Speed-only changes take effect immediately.

---

## File Structure

```
ants.py
  # --- Constants ---
  # --- Hex grid utilities (coords, neighbors, pixel conversion) ---
  # --- class Patch ---
  # --- class Ant ---
  # --- class World ---
  # --- Rendering functions ---
  # --- Slider UI (adapted from bees.py) ---
  # --- Main ---
```

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Gradient direction | Down-gradient (toward weaker pheromone) leads to food |
| Pheromone diffusion | None — decay only |
| Navigation model | Hex neighbors + float heading for EXPLORING; best-neighbor for CARRY/FOLLOW |
| Food depletion | Visit counter, starts at 10, slider-controlled |
| Ant exit mechanic | P_EXIT like bees, capped at MAX_OUTSIDE_FRACTION |
| World boundary | Ants blocked at edge (no valid neighbor) |
| Hex orientation | Flat-top, axial coordinates |
| Pheromone visualization | Cyan blend on patch color, scaled to visible range |
| IN_COLONY rendering | Invisible (like bees) |
| Fatigue distribution | Exponential (mean=120 steps) to prevent synchronized return waves |
| Tired ant color | Same as EXPLORING — tired returning looks like outbound foraging |
| No dance mechanic | Ants communicate via pheromone trail only |
