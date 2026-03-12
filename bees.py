"""Bees — a toy waggle-dance foraging simulation."""

import math
import random
from enum import IntEnum

import pygame

from ui import Slider, draw_panel, slider_row_geometry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
CONTROL_HEIGHT = 110

WORLD_SIZE = 1000.0         # meters, square world
DT = 1.0                    # seconds per simulation step
BEE_SPEED = 7.0             # m/s
BEE_STEP = BEE_SPEED * DT  # meters per step = 7 m
HIVE_POS = (WORLD_SIZE / 2, WORLD_SIZE / 2)
HIVE_RADIUS = 20.0          # meters — "at hive" threshold
DETECTION_RANGE = 30.0      # meters — flower detection radius for foragers
CLUSTER_SIGMA = 18.0        # meters — Gaussian spread per flower cluster
FLOWERS_PER_CLUSTER = 50
DANCE_ANGLE_SIGMA = math.radians(5)   # direction noise in waggle dance
DANCE_DIST_SIGMA = 0.15               # fractional distance noise
MAX_RECRUITS = 5
P_EXIT = 0.02               # probability per step that an IN_HIVE bee exits
MAX_OUTSIDE_FRACTION = 0.5  # bees stop leaving once this fraction is outside
FORAGE_FATIGUE = 150        # steps of fruitless foraging before returning home
FORAGE_TURN_SIGMA = math.radians(15)  # per-step heading drift while foraging
MIN_FLOWER_HIVE_DIST = 150.0          # cluster centers must be this far from hive

TRAIL_FADE_ALPHA = 50       # per-epoch trail decay (out of 255)
BEE_DOT_RADIUS = 3

COLOR_BG = (15, 20, 15)
COLOR_FLOWER = (180, 80, 220)
COLOR_FLOWER_DEPLETED = (60, 20, 70)
COLOR_HIVE_OUTER = (200, 150, 50)
COLOR_HIVE_INNER = (255, 220, 100)
# ---------------------------------------------------------------------------
# Bee states
# ---------------------------------------------------------------------------


class State(IntEnum):
    IN_HIVE = 0
    FORAGING = 1
    GOING_TO_FLOWER = 2
    RETURNING = 3
    DANCING = 4
    COLLECTING = 5


STATE_COLORS = {
    State.FORAGING: (100, 180, 100),
    State.GOING_TO_FLOWER: (210, 210, 70),
    State.COLLECTING: (210, 210, 70),
    State.RETURNING: (220, 100, 60),
    State.DANCING: (220, 100, 60),
}

# ---------------------------------------------------------------------------
# Spatial flower index
# ---------------------------------------------------------------------------


class FlowerGrid:
    """Spatial hash for O(1) nearest-flower detection per bee."""

    def __init__(self, flowers, cell_size, depletion_limit):
        self.cell_size = cell_size
        self.depletion_limit = depletion_limit
        self.visits = {f: 0 for f in flowers}
        self.buckets = {}
        for fx, fy in flowers:
            key = (int(fx / cell_size), int(fy / cell_size))
            self.buckets.setdefault(key, []).append((fx, fy))

    def is_depleted(self, flower):
        return self.visits[flower] >= self.depletion_limit

    def visit(self, flower):
        if flower in self.visits:
            self.visits[flower] += 1

    def nearest_in_range(self, x, y, range_):
        cx, cy = int(x / self.cell_size), int(y / self.cell_size)
        best = None
        best_d2 = range_ * range_
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for fx, fy in self.buckets.get((cx + dx, cy + dy), []):
                    if self.is_depleted((fx, fy)):
                        continue
                    d2 = (fx - x) ** 2 + (fy - y) ** 2
                    if d2 <= best_d2:
                        best_d2 = d2
                        best = (fx, fy)
        return best


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class Bee:
    def __init__(self):
        self.x, self.y = HIVE_POS
        self.vx = 0.0
        self.vy = 0.0
        self.state = State.IN_HIVE
        self.target_x = 0.0
        self.target_y = 0.0
        self.flower_pos = None
        self.steps_foraging = 0
        self.fatigue_limit = FORAGE_FATIGUE
        self.heading = 0.0
        self.step_size = BEE_STEP
        self.depart_delay = 0

    def act(self, world):
        if self.state == State.IN_HIVE:
            if self.depart_delay > 0:
                self.depart_delay -= 1
                if self.depart_delay == 0:
                    self.x, self.y = HIVE_POS
                    self._head_toward(self.target_x, self.target_y)
                    self.state = State.GOING_TO_FLOWER
            elif world.n_outside < len(world.bees) * MAX_OUTSIDE_FRACTION:
                if random.random() < P_EXIT:
                    self.step_size = max(3.0, random.gauss(BEE_STEP, BEE_STEP * 0.2))
                    self._set_random_heading()
                    self.x, self.y = HIVE_POS
                    self.steps_foraging = 0
                    self.fatigue_limit = max(20, int(random.expovariate(1.0 / FORAGE_FATIGUE)))
                    self.state = State.FORAGING

        elif self.state == State.FORAGING:
            new_x = self.x + self.vx
            new_y = self.y + self.vy
            if new_x <= 0.0 or new_x >= WORLD_SIZE:
                self.vx = -self.vx
                self.heading = math.pi - self.heading
                new_x = max(0.0, min(WORLD_SIZE, new_x))
            if new_y <= 0.0 or new_y >= WORLD_SIZE:
                self.vy = -self.vy
                self.heading = -self.heading
                new_y = max(0.0, min(WORLD_SIZE, new_y))
            self.x, self.y = new_x, new_y
            flower = world.flower_grid.nearest_in_range(self.x, self.y, DETECTION_RANGE)
            if flower:
                self.flower_pos = flower
                self.target_x, self.target_y = flower
                self.state = State.COLLECTING
            else:
                self.steps_foraging += 1
                if self.steps_foraging >= self.fatigue_limit:
                    self.flower_pos = None
                    self._head_toward(*HIVE_POS)
                    self.state = State.RETURNING
                else:
                    self.heading += random.gauss(0.0, FORAGE_TURN_SIGMA)
                    self.vx = self.step_size * math.cos(self.heading)
                    self.vy = self.step_size * math.sin(self.heading)

        elif self.state == State.GOING_TO_FLOWER:
            if random.random() < world.p_forget:
                self._set_random_heading()
                self.state = State.FORAGING
                return
            dist = self._dist_to(self.target_x, self.target_y)
            self._move_toward(self.target_x, self.target_y)
            flower = world.flower_grid.nearest_in_range(self.x, self.y, DETECTION_RANGE)
            if flower:
                self.flower_pos = flower
                self.target_x, self.target_y = flower
                self.state = State.COLLECTING
            elif dist <= BEE_STEP:
                self._set_random_heading()
                self.state = State.FORAGING

        elif self.state == State.COLLECTING:
            self._move_toward(self.target_x, self.target_y)
            if self._dist_to(self.target_x, self.target_y) < HIVE_RADIUS:
                world.flower_grid.visit(self.flower_pos)
                self._head_toward(*HIVE_POS)
                self.state = State.RETURNING

        elif self.state == State.RETURNING:
            if self.flower_pos is None:
                self._move_toward_noisy(*HIVE_POS, math.radians(25))
            else:
                self._move_toward(*HIVE_POS)
            if self._dist_to(*HIVE_POS) < HIVE_RADIUS:
                self.x, self.y = HIVE_POS
                self.state = State.DANCING if self.flower_pos is not None else State.IN_HIVE

        elif self.state == State.DANCING:
            world.recruit_from(self)
            self.state = State.IN_HIVE

    def _set_random_heading(self):
        self.heading = random.uniform(0.0, 2.0 * math.pi)
        self.vx = self.step_size * math.cos(self.heading)
        self.vy = self.step_size * math.sin(self.heading)

    def _head_toward(self, tx, ty):
        dx, dy = tx - self.x, ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            self.vx = dx / dist * self.step_size
            self.vy = dy / dist * self.step_size

    def _move_toward_noisy(self, tx, ty, sigma):
        dx, dy = tx - self.x, ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist <= self.step_size:
            self.x, self.y = tx, ty
        else:
            angle = math.atan2(dy, dx) + random.gauss(0.0, sigma)
            self.x += self.step_size * math.cos(angle)
            self.y += self.step_size * math.sin(angle)

    def _move_toward(self, tx, ty):
        dx, dy = tx - self.x, ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist <= self.step_size:
            self.x, self.y = tx, ty
        else:
            self.x += dx / dist * self.step_size
            self.y += dy / dist * self.step_size

    def _dist_to(self, tx, ty):
        return math.sqrt((tx - self.x) ** 2 + (ty - self.y) ** 2)


class World:
    def __init__(self, n_bees, n_clusters, p_forget_pct, depletion):
        self.p_forget = p_forget_pct / 100.0
        self.flowers = self._generate_flowers(n_clusters)
        self.flower_grid = FlowerGrid(self.flowers, DETECTION_RANGE, depletion)
        self.bees = [Bee() for _ in range(n_bees)]

    def _generate_flowers(self, n_clusters):
        flowers = []
        margin = CLUSTER_SIGMA * 2
        hx, hy = HIVE_POS
        for _ in range(n_clusters):
            for _ in range(200):
                cx = random.uniform(margin, WORLD_SIZE - margin)
                cy = random.uniform(margin, WORLD_SIZE - margin)
                if math.sqrt((cx - hx) ** 2 + (cy - hy) ** 2) >= MIN_FLOWER_HIVE_DIST:
                    break
            for _ in range(FLOWERS_PER_CLUSTER):
                fx = cx + random.gauss(0, CLUSTER_SIGMA)
                fy = cy + random.gauss(0, CLUSTER_SIGMA)
                if 0.0 <= fx <= WORLD_SIZE and 0.0 <= fy <= WORLD_SIZE:
                    flowers.append((fx, fy))
        return flowers

    @property
    def n_outside(self):
        return sum(1 for b in self.bees if b.state != State.IN_HIVE)

    def step(self):
        random.shuffle(self.bees)
        for bee in self.bees:
            bee.act(self)

    def recruit_from(self, dancer):
        if dancer.flower_pos is None:
            return
        hx, hy = HIVE_POS
        fx, fy = dancer.flower_pos
        angle = math.atan2(fy - hy, fx - hx)
        dist = math.sqrt((fx - hx) ** 2 + (fy - hy) ** 2)
        candidates = [b for b in self.bees if b.state == State.IN_HIVE]
        random.shuffle(candidates)
        for bee in candidates[:MAX_RECRUITS]:
            noisy_angle = angle + random.gauss(0, DANCE_ANGLE_SIGMA)
            noisy_dist = max(1.0, dist * (1.0 + random.gauss(0, DANCE_DIST_SIGMA)))
            bee.target_x = max(0.0, min(WORLD_SIZE, hx + noisy_dist * math.cos(noisy_angle)))
            bee.target_y = max(0.0, min(WORLD_SIZE, hy + noisy_dist * math.sin(noisy_angle)))
            bee.step_size = max(3.0, random.gauss(BEE_STEP, BEE_STEP * 0.2))
            bee.depart_delay = random.randint(0, 20)
            if bee.depart_delay == 0:
                bee.x, bee.y = HIVE_POS
                bee._head_toward(bee.target_x, bee.target_y)
                bee.state = State.GOING_TO_FLOWER


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def compute_scale(canvas_rect):
    """Return (scale, world_ox, world_oy) mapping world meters to screen pixels."""
    scale = min(canvas_rect.width, canvas_rect.height) / WORLD_SIZE
    world_px = WORLD_SIZE * scale
    world_py = WORLD_SIZE * scale
    ox = canvas_rect.x + (canvas_rect.width - world_px) / 2
    oy = canvas_rect.y + (canvas_rect.height - world_py) / 2
    return scale, ox, oy


def world_to_screen(wx, wy, scale, ox, oy):
    return int(ox + wx * scale), int(oy + wy * scale)


def render(screen, world, canvas_rect, trail_surf, fade_surf, n_epochs, scale, ox, oy):
    if n_epochs > 0:
        # Decay trail once per simulated epoch
        for _ in range(n_epochs):
            trail_surf.blit(fade_surf, (0, 0))
        # Stamp current bee positions onto trail
        lox = ox - canvas_rect.x
        loy = oy - canvas_rect.y
        for bee in world.bees:
            if bee.state == State.IN_HIVE:
                continue
            px, py = world_to_screen(bee.x, bee.y, scale, lox, loy)
            if bee.state == State.RETURNING and bee.flower_pos is None:
                color = STATE_COLORS[State.FORAGING]
            else:
                color = STATE_COLORS[bee.state]
            r = 1 if bee.state in (State.FORAGING, State.COLLECTING) else 2
            pygame.draw.circle(trail_surf, color, (px, py), r)

    screen.fill(COLOR_BG, canvas_rect)
    screen.blit(trail_surf, canvas_rect.topleft)

    # Draw flowers with depletion state
    for flower in world.flowers:
        px, py = world_to_screen(flower[0], flower[1], scale, ox, oy)
        if 0 <= px < canvas_rect.right and 0 <= py < canvas_rect.bottom:
            color = COLOR_FLOWER_DEPLETED if world.flower_grid.is_depleted(flower) else COLOR_FLOWER
            pygame.draw.circle(screen, color, (px, py), 2)

    # Hive marker
    hpx, hpy = world_to_screen(*HIVE_POS, scale, ox, oy)
    outer_r = max(5, int(HIVE_RADIUS * scale))
    inner_r = max(2, outer_r // 2)
    pygame.draw.circle(screen, COLOR_HIVE_OUTER, (hpx, hpy), outer_r)
    pygame.draw.circle(screen, COLOR_HIVE_INNER, (hpx, hpy), inner_r)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def make_sliders(control_rect):
    xs, sy, sw, sh = slider_row_geometry(control_rect, 5)
    return [
        Slider("Bees",      xs[0], sy, sw, sh,  10, 500, 200),
        Slider("Clusters",  xs[1], sy, sw, sh,   1,  50,  20),
        Slider("Forget %",  xs[2], sy, sw, sh,   0,  20,   2, step=0.5),
        Slider("Depletion", xs[3], sy, sw, sh,   1, 100,  10),
        Slider("Speed",     xs[4], sy, sw, sh,   1, 200,  10),
    ]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Bees")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    canvas_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT - CONTROL_HEIGHT)
    control_rect = pygame.Rect(
        0, WINDOW_HEIGHT - CONTROL_HEIGHT, WINDOW_WIDTH, CONTROL_HEIGHT
    )

    sliders = make_sliders(control_rect)
    bees_s, clusters_s, forget_s, depletion_s, speed_s = sliders

    def new_world():
        return World(
            n_bees=int(bees_s.value),
            n_clusters=int(clusters_s.value),
            p_forget_pct=forget_s.value,
            depletion=int(depletion_s.value),
        )

    scale, ox, oy = compute_scale(canvas_rect)
    world = new_world()

    trail_surf = pygame.Surface((canvas_rect.width, canvas_rect.height))
    trail_surf.fill(COLOR_BG)
    fade_surf = pygame.Surface((canvas_rect.width, canvas_rect.height))
    fade_surf.fill(COLOR_BG)
    fade_surf.set_alpha(TRAIL_FADE_ALPHA)

    epoch_accum = 0.0
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        reset_needed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            for idx, slider in enumerate(sliders):
                if slider.handle_event(event) and idx != 4:
                    reset_needed = True

        if reset_needed:
            world = new_world()
            trail_surf.fill(COLOR_BG)
            epoch_accum = 0.0

        epoch_accum += speed_s.value * dt
        n_epochs = int(epoch_accum)
        epoch_accum -= n_epochs
        for _ in range(n_epochs):
            world.step()

        render(screen, world, canvas_rect, trail_surf, fade_surf, n_epochs, scale, ox, oy)
        draw_panel(screen, font, control_rect, sliders)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
