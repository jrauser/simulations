"""Slimes — slime mold aggregation on a toroidal hex grid."""

import random

import pygame

from hex_utils import (
    hex_cells, build_neighbor_table, hex_to_pixel, hex_corners, compute_hex_layout,
)
from ui import Slider, draw_panel, slider_row_geometry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW_WIDTH   = 900
WINDOW_HEIGHT  = 740
CONTROL_HEIGHT = 110

COLOR_BG        = (10, 10, 10)
COLOR_CELL      = (25, 25, 25)
COLOR_PHEROMONE = (180, 220, 60)
COLOR_SLIME     = (230, 255, 100)

PHEROMONE_VIS_MAX = 20.0


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class Slime:
    __slots__ = ("pos",)

    def __init__(self, pos):
        self.pos = pos

    def act(self, world):
        # Emit pheromone first — counts toward own threshold check
        world.pheromone[self.pos] += world.drop

        nbrs = world.neighbor_table[self.pos]
        empties = [n for n in nbrs if n not in world.occupied]

        if world.pheromone[self.pos] >= world.threshold:
            # Seeking: move to empty neighbor with highest pheromone
            if not empties:
                return
            max_ph = max(world.pheromone[n] for n in empties)
            target = random.choice([n for n in empties if world.pheromone[n] == max_ph])
        else:
            # Wandering: move to a random empty neighbor
            if not empties:
                return
            target = random.choice(empties)

        world.occupied.discard(self.pos)
        world.occupied.add(target)
        self.pos = target


class World:
    def __init__(self, radius, density, drop, threshold, evaporation, diffusion):
        self.drop        = drop
        self.threshold   = threshold
        self.evaporation = evaporation
        self.diffusion   = diffusion

        self.cells          = hex_cells(radius)
        self.neighbor_table = build_neighbor_table(self.cells, radius)
        self.pheromone      = {cell: 0.0 for cell in self.cells}
        self.occupied       = set()
        self.slimes         = []

        cell_list = list(self.cells)
        n = min(round(len(cell_list) * density), len(cell_list))
        for pos in random.sample(cell_list, n):
            self.slimes.append(Slime(pos))
            self.occupied.add(pos)

    def step(self):
        # Phase 1: all slimes act in random order
        random.shuffle(self.slimes)
        for slime in self.slimes:
            slime.act(self)

        # Phase 2: diffusion — two-phase to avoid order-dependence
        # Each cell spreads diffusion_rate fraction of its pheromone to each neighbor.
        # Total outflow is clamped to the cell's current amount to keep values non-negative.
        inflow = {cell: 0.0 for cell in self.cells}
        for cell in self.cells:
            ph = self.pheromone[cell]
            if ph <= 0.0:
                continue
            nbrs = self.neighbor_table[cell]
            out_per_nbr = ph * self.diffusion
            total_out = out_per_nbr * len(nbrs)
            if total_out > ph:                  # clamp: can't give away more than you have
                out_per_nbr = ph / len(nbrs)
                total_out = ph
            for nbr in nbrs:
                inflow[nbr] += out_per_nbr
            self.pheromone[cell] = ph - total_out

        # Phase 3: apply inflow and evaporate
        evap_factor = 1.0 - self.evaporation
        for cell in self.cells:
            val = (self.pheromone[cell] + inflow[cell]) * evap_factor
            self.pheromone[cell] = val if val > 0.001 else 0.0


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render(screen, world, canvas_rect, cell_size, ox, oy):
    screen.fill(COLOR_BG, canvas_rect)

    if cell_size >= 1.5:
        cell_inner = cell_size * 0.95
        slime_r = max(1, int(cell_size * 0.35))

        # Pass 1: all cells with pheromone overlay
        for (q, r), ph in world.pheromone.items():
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            if ph > 0.0:
                color = lerp_color(COLOR_CELL, COLOR_PHEROMONE, ph / PHEROMONE_VIS_MAX)
            else:
                color = COLOR_CELL
            pygame.draw.polygon(screen, color, hex_corners(cx, cy, cell_inner))

        # Pass 2: slimes on top
        for slime in world.slimes:
            q, r = slime.pos
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            pygame.draw.circle(screen, COLOR_SLIME, (int(cx), int(cy)), slime_r)

    else:
        for (q, r), ph in world.pheromone.items():
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            color = lerp_color(COLOR_CELL, COLOR_PHEROMONE, ph / PHEROMONE_VIS_MAX) if ph > 0.0 else COLOR_CELL
            screen.set_at((int(cx), int(cy)), color)
        for slime in world.slimes:
            q, r = slime.pos
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            screen.set_at((int(cx), int(cy)), COLOR_SLIME)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def make_sliders(control_rect):
    xs, sy, sw, sh = slider_row_geometry(control_rect, 7, pad=10)
    return [
        Slider("Size",        xs[0], sy, sw, sh,  3,   40, 40),
        Slider("Population",  xs[1], sy, sw, sh,  1,   50,  5),
        Slider("Drop",        xs[2], sy, sw, sh,  0.1,  5, 1.0, step=0.1),
        Slider("Threshold",   xs[3], sy, sw, sh,  0.5, 10, 2.0, step=0.5),
        Slider("Evap %",      xs[4], sy, sw, sh,  1,   50, 10),
        Slider("Diffusion %", xs[5], sy, sw, sh,  0,   20,  5),
        Slider("Speed",       xs[6], sy, sw, sh,  1,  500, 50),
    ]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Slimes")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    canvas_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT - CONTROL_HEIGHT)
    control_rect = pygame.Rect(0, WINDOW_HEIGHT - CONTROL_HEIGHT, WINDOW_WIDTH, CONTROL_HEIGHT)

    sliders = make_sliders(control_rect)
    size_s, pop_s, drop_s, thresh_s, evap_s, diff_s, speed_s = sliders

    def new_world():
        return World(
            radius=int(size_s.value),
            density=pop_s.value / 100.0,
            drop=drop_s.value,
            threshold=thresh_s.value,
            evaporation=evap_s.value / 100.0,
            diffusion=diff_s.value / 100.0,
        )

    world = new_world()
    cell_size, ox, oy = compute_hex_layout(int(size_s.value), canvas_rect)
    epoch_accum = 0.0
    running = True
    paused = False

    while running:
        dt = clock.tick(60) / 1000.0

        reset_needed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_p:
                paused = not paused
            for idx, slider in enumerate(sliders):
                if slider.handle_event(event) and idx < 4:  # Size/Pop/Drop/Threshold reset
                    reset_needed = True

        if reset_needed:
            world = new_world()
            cell_size, ox, oy = compute_hex_layout(int(size_s.value), canvas_rect)
            epoch_accum = 0.0

        if paused:
            render(screen, world, canvas_rect, cell_size, ox, oy)
            draw_panel(screen, font, control_rect, sliders)
            pygame.display.flip()
            continue

        # Physics params update live without reset
        world.evaporation = evap_s.value / 100.0
        world.diffusion   = diff_s.value / 100.0

        epoch_accum += speed_s.value * dt
        n_steps = int(epoch_accum)
        epoch_accum -= n_steps
        for _ in range(n_steps):
            world.step()

        render(screen, world, canvas_rect, cell_size, ox, oy)
        draw_panel(screen, font, control_rect, sliders)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
