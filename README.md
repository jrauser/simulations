# Simulations

A collection of toy agent-based simulations, inspired by Mitchell Resnick's book
*Turtles, Termites, and Traffic Jams: Explorations in Massively Parallel Microworlds* (1994).

Each simulation runs in a pygame window with a control panel of sliders at the bottom.

## Simulations

### Termites (`termites.py`)
Termites wander randomly, picking up woodchips when they find them and dropping them when
they stumble onto a pile. No coordination, no central control — yet chips spontaneously
consolidate into a small number of large piles.

### Ants (`ants.py`)
Ants forage from a central colony, laying pheromone trails when returning with food.
Other ants follow the trails, reinforcing them. Demonstrates how stigmergic communication
produces efficient collective foraging.

### Bees (`bees.py`)
A waggle-dance model of honeybee foraging. Scouts find flower clusters and recruit hive
mates by dancing; recruited bees fly to approximate locations and search locally.
Shows how noisy indirect communication can still efficiently allocate foragers.

### Turtles (`turtles.py`)
A hex-grid variant of Schelling's segregation model. Two populations (turtles and frogs)
each prefer that some fraction of their neighbors be the same type. Unhappy animals hop
to a random empty neighboring cell. Simple local preferences produce global segregation.

### Slimes (`slimes.py`)
Slime mold aggregation. Each slime emits pheromone every turn. Below a concentration
threshold it wanders randomly; above the threshold it climbs toward the richest neighboring
cell. Pheromone diffuses and evaporates each epoch. Demonstrates how purely local chemical
signaling produces aggregation without any individual knowing about the collective.

## Running

```
uv run termites.py
uv run ants.py
uv run bees.py
uv run turtles.py
uv run slimes.py
```

## Shared Modules

- **`hex_utils.py`** — hex grid geometry, toroidal neighbor tables, pixel conversion
- **`ui.py`** — `Slider` widget, control panel rendering, layout helpers
