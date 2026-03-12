# Bees Simulation — Implementation Plan

## Overview

Single-file Python simulation (`bees.py`) using pygame. Classes: `Bee` and `World`. Simulation state and rendering are strictly separated. Shares the `Slider` UI pattern from `termites.py`.

---

## World

- **Continuous 2D space**: 1000m × 1000m, floating-point coordinates.
- **Time step**: 5 seconds of simulated time per epoch.
- **Hive**: fixed at world center (500, 500). Represented as a small circle. Radius ~15m for "at hive" detection.
- **Boundary**: bees that reach the world edge reverse direction (reflect) and pick a new random heading.

---

## Flowers

Flowers are placed in **Gaussian clusters**:
- `n_clusters` cluster centers are placed uniformly at random in the world.
- Each cluster contains a fixed number of individual flowers (~50) scattered with σ ≈ 40m around the center.
- Flowers are permanent (no depletion).
- Detection: a foraging bee detects any flower within 30m of its current position.

Stored as a flat list of `(x, y)` float pairs. For detection, a spatial approach is used: flowers are stored in a grid-bucketed dict (bucket size = detection range) so lookup is O(1) per bee per step rather than O(flowers).

---

## Bee States

```
IN_HIVE → FORAGING → (detects flower) → RETURNING
                                              ↓
                                          IN_HIVE → DANCING → IN_HIVE
                                                         ↓
                                              (recruits N bees)
                                                         ↓
                                              GOING_TO_FLOWER → (finds flower) → RETURNING
                                                         ↓ (forget or miss)
                                                      FORAGING
```

### State descriptions

| State | Behavior |
|-------|----------|
| `IN_HIVE` | Invisible. Each step: exit with probability `p_exit` (default 10%) → `FORAGING`. |
| `FORAGING` | Each step: pick a uniformly random direction, fly `bee_speed × dt` meters. If any flower is within detection range: pick it up → `RETURNING`. |
| `RETURNING` | Fly straight toward hive center. On arrival → `DANCING`. |
| `DANCING` | Stay at hive for 1 step. Recruit up to `max_recruits` (default 5) bees currently `IN_HIVE`, giving each a noisy copy of the flower's direction and distance from hive. Then → `IN_HIVE`. |
| `GOING_TO_FLOWER` | Fly toward the noisy target point. Each step: roll `p_forget` (default 2%); if forgotten → `FORAGING`. On reaching target: scan for flower within detection range. If found → `RETURNING`. If not → `FORAGING`. |

---

## Parameters and Defaults

| Parameter | Value | Notes |
|-----------|-------|-------|
| World size | 1000 × 1000 m | Fixed |
| Time step `dt` | 5 s | Fixed |
| Bee speed | 7 m/s → **35 m/step** | Realistic |
| Detection range | 30 m | Generous for playability |
| Hive radius | 15 m | "At hive" threshold |
| Cluster σ | 40 m | Gaussian spread per cluster |
| Flowers per cluster | 50 | Fixed |
| Dance direction noise | σ = 15° | Applied to angle from hive |
| Dance distance noise | σ = 15% | Multiplicative on distance |
| Max recruits per dance | 5 | Fixed cap |
| `p_exit` per step | 10% | Bees leave hive |
| `p_forget` per step | 2% | Default; slider-controlled |

---

## Waggle Dance Details

When a bee arrives at the hive carrying pollen, it knows the flower's world position `(fx, fy)`. It computes:
- `angle = atan2(fy - hive_y, fx - hive_x)`
- `distance = sqrt((fx-hive_x)² + (fy-hive_y)²)`

Each recruited bee receives a noisy copy:
- `noisy_angle = angle + N(0, 15°)`
- `noisy_distance = distance × (1 + N(0, 0.15))`

The recruited bee's target: `(hive_x + noisy_distance × cos(noisy_angle), hive_y + noisy_distance × sin(noisy_angle))`.

---

## Trail Rendering

A persistent `trail_surf` (pygame Surface, same size as canvas) accumulates bee positions:
- Each epoch: blit a semi-transparent background-colored surface onto `trail_surf` to decay old trails.
- Then draw each visible bee's current position onto `trail_surf`.
- Blit `trail_surf` onto the main screen before drawing the static world elements.

**Decay alpha** scales with sim speed: `decay_alpha = max(1, int(5 * speed / 10))`. At low speeds, trails persist longer. At high speeds, they fade faster to avoid saturation.

---

## Rendering

**Colors:**
- Background: `(15, 20, 15)` (very dark green)
- Flowers: `(240, 230, 60)` (yellow)
- Hive: `(200, 150, 50)` (amber)
- Foraging bee: `(100, 180, 100)` (green)
- Going-to-flower bee: `(200, 200, 80)` (yellow-green)
- Returning bee: `(220, 100, 60)` (orange-red)
- Bee dot size: 3px radius

**Layout:**
- Top: canvas (world view), scales to fit window
- Bottom: control panel with sliders

**Scale**: `px_per_m = min(canvas_w, canvas_h) / 1000`. World is rendered as a square, centered.

---

## Controls

Four sliders (same UI pattern as termites):

| Slider | Range | Default | Resets? |
|--------|-------|---------|---------|
| Bees | 10–500 | 200 | Yes |
| Clusters | 1–50 | 20 | Yes |
| Forget % | 0–20% | 2% | Yes |
| Speed | 1–200 steps/sec | 10 | No |

---

## File Structure

```
bees.py
  # --- Constants ---
  # --- World utilities (coord transforms, spatial bucket) ---
  # --- class Bee ---
  # --- class World ---
  # --- Trail surface management ---
  # --- Rendering functions ---
  # --- Slider UI (adapted from termites.py) ---
  # --- Main ---
```

---

## Decisions Made

| Question | Decision |
|----------|----------|
| Flower depletion | None — flowers are permanent |
| Dance noise | 15° direction σ, 15% distance σ |
| Trail decay | Per-pixel fade each frame, rate tied to speed |
| Recruited bee misses target | Falls back to FORAGING |
| Forget trigger | Per-step probability (2% default) |
| Bees in hive | Invisible |
| Dance audience | Fixed cap of 5, sampled from IN_HIVE bees |
| Boundary behavior | Reflect (reverse component) and pick new random heading |
| Flower lookup | Spatial grid bucket for O(1) detection per bee |
