"""Turtles — Schelling segregation on a toroidal hex grid."""

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

COLOR_BG     = (20, 20, 20)
COLOR_TURTLE = (80, 190, 100)
COLOR_FROG   = (220, 130, 50)
COLOR_EMPTY  = (45, 45, 45)

ANIMAL_COLORS = {'T': COLOR_TURTLE, 'F': COLOR_FROG}

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class World:
    def __init__(self, radius, density, preference):
        self.preference = preference
        self.cells = hex_cells(radius)
        self.neighbor_table = build_neighbor_table(self.cells, radius)
        self.grid = {cell: None for cell in self.cells}

        cell_list = list(self.cells)
        n_occupied = min(round(len(cell_list) * density), len(cell_list))
        occupied = random.sample(cell_list, n_occupied)
        n_turtles = n_occupied // 2
        for i, cell in enumerate(occupied):
            self.grid[cell] = 'T' if i < n_turtles else 'F'

        self._occupied = list(occupied)

    def step(self):
        if not self._occupied:
            return
        idx = random.randrange(len(self._occupied))
        cell = self._occupied[idx]
        if self._is_happy(cell):
            return
        empties = [n for n in self.neighbor_table[cell] if self.grid[n] is None]
        if not empties:
            return
        target = random.choice(empties)
        self.grid[target] = self.grid[cell]
        self.grid[cell] = None
        self._occupied[idx] = target

    def _is_happy(self, cell):
        animal = self.grid[cell]
        occupied_nbrs = [n for n in self.neighbor_table[cell] if self.grid[n] is not None]
        if not occupied_nbrs:
            return True
        same = sum(1 for n in occupied_nbrs if self.grid[n] == animal)
        return same / len(occupied_nbrs) >= self.preference


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render(screen, world, canvas_rect, cell_size, ox, oy):
    screen.fill(COLOR_BG, canvas_rect)
    if cell_size >= 1.5:
        cell_inner = cell_size * 0.95
        for (q, r), occupant in world.grid.items():
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            color = ANIMAL_COLORS.get(occupant, COLOR_EMPTY)
            pts = hex_corners(cx, cy, cell_inner)
            pygame.draw.polygon(screen, color, pts)
    else:
        for (q, r), occupant in world.grid.items():
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            color = ANIMAL_COLORS.get(occupant, COLOR_EMPTY)
            screen.set_at((int(cx), int(cy)), color)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def make_sliders(control_rect):
    xs, sy, sw, sh = slider_row_geometry(control_rect, 4)
    return [
        Slider("Size",    xs[0], sy, sw, sh,   3,   40,  15),
        Slider("Density", xs[1], sy, sw, sh,  10,   90,  70),
        Slider("Pref %",  xs[2], sy, sw, sh,   0,  100,  33),
        Slider("Speed",   xs[3], sy, sw, sh,   1, 2000, 100),
    ]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Turtles")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    canvas_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT - CONTROL_HEIGHT)
    control_rect = pygame.Rect(0, WINDOW_HEIGHT - CONTROL_HEIGHT, WINDOW_WIDTH, CONTROL_HEIGHT)

    sliders = make_sliders(control_rect)
    size_s, density_s, pref_s, speed_s = sliders

    def new_world():
        return World(
            radius=int(size_s.value),
            density=density_s.value / 100.0,
            preference=pref_s.value / 100.0,
        )

    world = new_world()
    cell_size, ox, oy = compute_hex_layout(int(size_s.value), canvas_rect)
    epoch_accum = 0.0
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        reset_needed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for idx, slider in enumerate(sliders):
                if slider.handle_event(event) and idx != 3:
                    reset_needed = True

        if reset_needed:
            world = new_world()
            cell_size, ox, oy = compute_hex_layout(int(size_s.value), canvas_rect)
            epoch_accum = 0.0

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
