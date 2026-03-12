"""Termites — a toy hex-grid swarm simulation inspired by Resnick's book."""

import math
import random

import pygame

from hex_utils import (
    hex_cells, build_neighbor_table, hex_to_pixel, hex_corners, compute_hex_layout,
)
from ui import Slider, draw_panel, slider_row_geometry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
CONTROL_HEIGHT = 110

COLOR_BG = (20, 20, 20)
COLOR_CHIP = (210, 180, 140)
COLOR_CARRYING = (200, 80, 60)
COLOR_EMPTY = (80, 130, 210)
COLOR_CELL = (65, 65, 65)

# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


DROP_COOLDOWN = 10


class Termite:
    def __init__(self, q, r):
        self.q = q
        self.r = r
        self.carrying = False
        self.cooldown = 0

    def act(self, arena):
        pos = (self.q, self.r)
        nbrs = arena.neighbors_of(pos)

        if self.cooldown > 0:
            self.cooldown -= 1

        if not self.carrying:
            new_pos = random.choice(nbrs)
            self.q, self.r = new_pos
            if self.cooldown == 0 and arena.has_chip(new_pos):
                arena.remove_chip(new_pos)
                self.carrying = True
        else:
            if arena.has_chip(pos):
                free = [n for n in nbrs if not arena.has_chip(n)]
                if free:
                    drop = random.choice(free)
                    arena.add_chip(drop)
                    self.carrying = False
                    self.cooldown = DROP_COOLDOWN
                # else: no free neighbor — retain chip, don't move
            else:
                new_pos = random.choice(nbrs)
                self.q, self.r = new_pos


class Arena:
    def __init__(self, radius, termite_density, chip_density):
        self.radius = radius
        self.cells = hex_cells(radius)
        self._neighbor_table = build_neighbor_table(self.cells, radius)
        self.chips = set()
        self.termites = []
        self._populate(termite_density, chip_density)

    def _populate(self, termite_density, chip_density):
        cell_list = list(self.cells)
        n_cells = len(cell_list)
        n_chips = max(1, round(n_cells * chip_density))
        n_termites = max(1, round(n_cells * termite_density))
        self.chips = set(random.sample(cell_list, min(n_chips, n_cells)))
        termite_cells = random.sample(cell_list, min(n_termites, n_cells))
        self.termites = [Termite(q, r) for q, r in termite_cells]

    def step(self):
        random.shuffle(self.termites)
        for t in self.termites:
            t.act(self)

    def neighbors_of(self, pos):
        return self._neighbor_table[pos]

    def has_chip(self, pos):
        return pos in self.chips

    def add_chip(self, pos):
        self.chips.add(pos)

    def remove_chip(self, pos):
        self.chips.discard(pos)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------



def render_arena(screen, arena, canvas_rect, cell_size, ox, oy):
    screen.fill(COLOR_BG, canvas_rect)

    if cell_size >= 1.5:
        cell_inner = cell_size * 0.92
        chip_size = cell_size * 1.04  # slightly oversized so chips fully cover cell
        for q, r in arena.cells:
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            pts = [(round(x), round(y)) for x, y in hex_corners(cx, cy, cell_inner)]
            pygame.draw.polygon(screen, COLOR_CELL, pts)

        for q, r in arena.chips:
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            pts = [(round(x), round(y)) for x, y in hex_corners(cx, cy, chip_size)]
            pygame.draw.polygon(screen, COLOR_CHIP, pts)
    else:
        for q, r in arena.cells:
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            screen.set_at((int(cx), int(cy)), COLOR_CELL)
        for q, r in arena.chips:
            cx, cy = hex_to_pixel(q, r, cell_size, ox, oy)
            screen.set_at((int(cx), int(cy)), COLOR_CHIP)

    termite_r = max(2, int(cell_size * 0.45))
    for t in arena.termites:
        cx, cy = hex_to_pixel(t.q, t.r, cell_size, ox, oy)
        color = COLOR_CARRYING if t.carrying else COLOR_EMPTY
        pygame.draw.circle(screen, color, (int(cx), int(cy)), termite_r)



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def make_sliders(control_rect):
    xs, sy, sw, sh = slider_row_geometry(control_rect, 4, pad=20)
    return [
        Slider("Size (N)",  xs[0], sy, sw, sh,  3, 200,   8),
        Slider("Termites",  xs[1], sy, sw, sh, 0.1, 10,  1.0, step=0.1),
        Slider("Chips",     xs[2], sy, sw, sh, 0.1, 40,  8.0, step=0.1),
        Slider("Speed",     xs[3], sy, sw, sh,   1, 200,  20),
    ]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Termites")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    canvas_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT - CONTROL_HEIGHT)
    control_rect = pygame.Rect(
        0, WINDOW_HEIGHT - CONTROL_HEIGHT, WINDOW_WIDTH, CONTROL_HEIGHT
    )

    sliders = make_sliders(control_rect)
    size_s, termite_s, chip_s, speed_s = sliders

    def new_arena():
        return Arena(
            radius=size_s.value,
            termite_density=termite_s.value / 100.0,
            chip_density=chip_s.value / 100.0,
        )

    arena = new_arena()
    cell_size, ox, oy = compute_hex_layout(arena.radius, canvas_rect)
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
            arena = new_arena()
            cell_size, ox, oy = compute_hex_layout(arena.radius, canvas_rect)
            epoch_accum = 0.0

        epoch_accum += speed_s.value * dt
        n_epochs = int(epoch_accum)
        epoch_accum -= n_epochs
        for _ in range(n_epochs):
            arena.step()

        render_arena(screen, arena, canvas_rect, cell_size, ox, oy)
        draw_panel(screen, font, control_rect, sliders)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
