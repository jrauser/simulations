"""Ants — a toy pheromone trail foraging simulation."""

import math
import random
from enum import IntEnum

import pygame

from hex_utils import hex_to_pixel, hex_corners
from ui import Slider, draw_panel, slider_row_geometry

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 740
CONTROL_HEIGHT = 110

WORLD_RADIUS = 40           # hex distance from colony to edge
PHEROMONE_DECAY = 0.985     # multiplier per step
PHEROMONE_DROP_MAX = 35.0   # deposit at world edge; tapers to 0 at colony
PHEROMONE_DROP_HALFLIFE = 20.0  # hex distance at which deposit reaches 63% of max
PHEROMONE_THRESHOLD = 0.1   # minimum to detect / follow
PHEROMONE_VIS_MAX = 50.0    # pheromone value that saturates the color scale

P_EXIT = 0.03               # per-step probability an IN_COLONY ant exits
MAX_OUTSIDE_FRACTION = 0.6  # stop sending ants out once this fraction is outside
ANT_FATIGUE = 120           # mean steps before tiring (exponential distribution)
FOOD_START = 10             # default food visits per patch before depletion
FOOD_MIN_DIST = 15          # minimum hex distance from colony to food cluster
FOOD_CLUSTER_RADIUS = 3     # food patches within this hex distance of cluster center

EXPLORE_TURN_SIGMA = math.radians(30)  # per-step heading drift while exploring
CARRY_TURN_SIGMA = math.radians(8)     # noise on homeward leg (small → straighter trails)
FOLLOW_LOOK_AHEAD = 3                  # steps ahead to average pheromone per direction
PHEROMONE_DIFFUSION = 0.02             # fraction spread to each neighbor per step
HISTORY_LEN = 8                        # positions tracked for loop detection
LOOP_BLIND_STEPS = 12                  # steps to ignore pheromone after loop detection

ANT_DOT_RADIUS = 2

# Colors
COLOR_BG = (18, 12, 8)
COLOR_PATCH_BASE = (30, 22, 15)
COLOR_FOOD = (60, 180, 60)
COLOR_FOOD_DEPLETED = (25, 55, 25)
COLOR_PHEROMONE = (80, 180, 255)
COLOR_COLONY_OUTER = (200, 150, 50)
COLOR_COLONY_INNER = (255, 220, 100)
# Flat-top hex: 6 axial neighbor directions
HEX_DIRECTIONS = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (-1, +1), (0, +1)]

# Angles (radians) for each of the 6 hex directions (flat-top layout)
# direction index → angle of the hex center in that direction
HEX_DIR_ANGLES = [
    math.atan2(math.sqrt(3) / 2 * d[0] + math.sqrt(3) * d[1],
               3 / 2 * d[0])
    for d in HEX_DIRECTIONS
]

# ---------------------------------------------------------------------------
# Hex grid utilities
# ---------------------------------------------------------------------------


def hex_distance(q1, r1, q2, r2):
    return (abs(q1 - q2) + abs(q1 + r1 - q2 - r2) + abs(r1 - r2)) // 2



def heading_to_hex_dir(heading):
    """Return the index (0-5) of the HEX_DIRECTIONS entry closest to heading."""
    best = 0
    best_cos = -2.0
    for i, a in enumerate(HEX_DIR_ANGLES):
        c = math.cos(heading - a)
        if c > best_cos:
            best_cos = c
            best = i
    return best


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


# ---------------------------------------------------------------------------
# Patch
# ---------------------------------------------------------------------------


class Patch:
    __slots__ = ("pheromone", "_inflow", "food_count", "food_start")

    def __init__(self):
        self.pheromone = 0.0
        self._inflow = 0.0
        self.food_count = 0
        self.food_start = 0  # original food count, for color scaling

    def diffuse_out(self, neighbors):
        """Phase 1: push a fraction of pheromone into neighbor inflow buffers."""
        if self.pheromone > 0.0001:
            amount = self.pheromone * PHEROMONE_DIFFUSION
            for nb in neighbors:
                nb._inflow += amount
            self.pheromone *= 1.0 - len(neighbors) * PHEROMONE_DIFFUSION

    def step(self, decay, threshold):
        """Phase 2: absorb inflow, then evaporate."""
        self.pheromone += self._inflow
        self._inflow = 0.0
        if self.pheromone > 0.0:
            self.pheromone *= decay
            if self.pheromone < threshold:
                self.pheromone = 0.0

    def color(self):
        # Base: food color or plain dirt
        if self.food_start > 0:
            if self.food_count <= 0:
                base = COLOR_FOOD_DEPLETED
            else:
                t = self.food_count / self.food_start
                base = lerp_color(COLOR_FOOD_DEPLETED, COLOR_FOOD, t)
        else:
            base = COLOR_PATCH_BASE

        # Overlay pheromone
        if self.pheromone > 0:
            t = min(self.pheromone / PHEROMONE_VIS_MAX, 1.0)
            return lerp_color(base, COLOR_PHEROMONE, t)
        return base


# ---------------------------------------------------------------------------
# Ant states
# ---------------------------------------------------------------------------


class State(IntEnum):
    IN_COLONY = 0
    EXPLORING = 1
    CARRYING = 2
    FOLLOWING = 3
    RETURNING = 4   # tired, heading home without food


STATE_COLORS = {
    State.EXPLORING: (220, 200, 120),   # sandy yellow
    State.CARRYING:  (220, 90,  50),    # orange-red
    State.FOLLOWING: (240, 60,  220),   # magenta — visible against cyan pheromone
    State.RETURNING: (220, 200, 120),   # same as EXPLORING
}

# ---------------------------------------------------------------------------
# Ant
# ---------------------------------------------------------------------------


class Ant:
    def __init__(self):
        self.q = 0
        self.r = 0
        self.state = State.IN_COLONY
        self.heading = 0.0
        self.fatigue = 0
        self.fatigue_limit = ANT_FATIGUE
        self.pos_history: list[tuple[int, int]] = []  # recent positions for loop detection
        self.pheromone_blind = 0  # steps remaining where pheromone is ignored

    def step(self, world):
        match self.state:
            case State.IN_COLONY:  self._act_in_colony(world)
            case State.EXPLORING:  self._act_exploring(world)
            case State.CARRYING:   self._act_carrying(world)
            case State.FOLLOWING:  self._act_following(world)
            case State.RETURNING:  self._act_returning(world)

    # --- per-state methods ---

    def _act_in_colony(self, world):
        if world.n_outside < len(world.ants) * MAX_OUTSIDE_FRACTION:
            if random.random() < P_EXIT:
                self.heading = random.uniform(0, 2 * math.pi)
                self.fatigue = 0
                self.fatigue_limit = max(20, int(random.expovariate(1.0 / ANT_FATIGUE)))
                has_trail = any(
                    world.patches[self.q + dq, self.r + dr].pheromone >= PHEROMONE_THRESHOLD
                    for dq, dr in HEX_DIRECTIONS
                )
                self.state = State.FOLLOWING if has_trail else State.EXPLORING
                self.pos_history.clear()

    def _act_exploring(self, world):
        if self._fatigue_check(): return
        if self._try_pickup_food(world):
            return
        food_di = self._food_direction(world)
        if food_di is not None:
            self._move_to(world, food_di)
            self._try_pickup_food(world)
            return
        if self.pheromone_blind > 0:
            self.pheromone_blind -= 1
        elif world.patches[self.q, self.r].pheromone >= PHEROMONE_THRESHOLD:
            self.state = State.FOLLOWING
            self.pos_history.clear()
            return
        self.heading += random.gauss(0.0, EXPLORE_TURN_SIGMA)
        self._move_by_heading(world)

    def _act_carrying(self, world):
        # Deposit pheromone proportional to distance from colony.
        # Exponential rise: 0 at colony, ~63% of max at PHEROMONE_DROP_HALFLIFE hexes,
        # approaching world.drop_max at the world edge.
        patch = world.patches[self.q, self.r]
        dist = hex_distance(self.q, self.r, 0, 0)
        deposit = world.drop_max * (1.0 - math.exp(-dist / PHEROMONE_DROP_HALFLIFE))
        patch.pheromone += deposit
        if self.q == 0 and self.r == 0:
            self.state = State.IN_COLONY
            return
        self._move_toward_colony(world, CARRY_TURN_SIGMA)

    def _act_following(self, world):
        if self._fatigue_check(): return
        if self._try_pickup_food(world): return
        if self._detect_loop():
            self.heading = random.uniform(0, 2 * math.pi)
            self.pheromone_blind = LOOP_BLIND_STEPS
            self.state = State.EXPLORING
            self.pos_history.clear()
            return
        food_di = self._food_direction(world)
        chosen_di = food_di if food_di is not None else self._gradient_dir(world)
        self._move_to(world, chosen_di)

    def _act_returning(self, world):
        if self.q == 0 and self.r == 0:
            self.state = State.IN_COLONY
            return
        self._move_toward_colony(world, CARRY_TURN_SIGMA)

    # --- helpers ---

    def _fatigue_check(self):
        """Increment fatigue; return True (and set RETURNING) if limit reached."""
        self.fatigue += 1
        if self.fatigue >= self.fatigue_limit:
            self.state = State.RETURNING
            return True
        return False

    def _try_pickup_food(self, world):
        """Pick up food from current patch if available. Returns True if food taken."""
        patch = world.patches[self.q, self.r]
        if patch.food_count > 0:
            patch.food_count -= 1
            self.state = State.CARRYING
            return True
        return False

    def _detect_loop(self):
        """Append current position to history; return True if this cell was visited recently."""
        self.pos_history.append((self.q, self.r))
        if len(self.pos_history) > HISTORY_LEN:
            self.pos_history.pop(0)
        return self.pos_history.count((self.q, self.r)) >= 2

    def _food_direction(self, world):
        """Return direction index toward nearest food within FOLLOW_LOOK_AHEAD steps,
        scanning all 6 directions. Returns None if no food detected."""
        best_dist = FOLLOW_LOOK_AHEAD + 1
        best_di = None
        for di, (dq, dr) in enumerate(HEX_DIRECTIONS):
            for k in range(1, FOLLOW_LOOK_AHEAD + 1):
                p = world.patches.get((self.q + dq * k, self.r + dr * k))
                if p is None:
                    break
                if p.food_count > 0 and k < best_dist:
                    best_dist = k
                    best_di = di
                    break
        return best_di

    def _gradient_dir(self, world):
        """Return best outward direction by pheromone sum (with Resnick jitter), or None."""
        center_di = heading_to_hex_dir(self.heading)
        perp_di = (center_di + random.choice([2, 4])) % 6  # ±120° ≈ perpendicular
        jq = self.q + HEX_DIRECTIONS[perp_di][0]
        jr = self.r + HEX_DIRECTIONS[perp_di][1]
        sense_q, sense_r = (jq, jr) if (jq, jr) in world.patches else (self.q, self.r)

        cur_dist = hex_distance(self.q, self.r, 0, 0)
        best_score = 0.0
        chosen_di = None
        for di, (dq, dr) in enumerate(HEX_DIRECTIONS):
            if hex_distance(self.q + dq, self.r + dr, 0, 0) <= cur_dist:
                continue  # nestward or lateral — skip
            ph_sum = 0.0
            for k in range(1, FOLLOW_LOOK_AHEAD + 1):
                p = world.patches.get((sense_q + dq * k, sense_r + dr * k))
                if p is None:
                    break
                if p.pheromone >= PHEROMONE_THRESHOLD:
                    ph_sum += p.pheromone
            if ph_sum > best_score:
                best_score = ph_sum
                chosen_di = di
        return chosen_di

    def _move_to(self, world, di):
        """Move one step in direction di. Falls back to EXPLORING (with blind) if blocked."""
        if di is not None:
            dq, dr = HEX_DIRECTIONS[di]
            nq, nr = self.q + dq, self.r + dr
            if (nq, nr) in world.patches:
                self.q, self.r = nq, nr
                self.heading = HEX_DIR_ANGLES[di]
                return
        self.heading = random.uniform(0, 2 * math.pi)
        self.pheromone_blind = LOOP_BLIND_STEPS
        self.state = State.EXPLORING

    def _move_by_heading(self, world):
        """Move one step in the direction closest to self.heading; reflect at edge."""
        di = heading_to_hex_dir(self.heading)
        dq, dr = HEX_DIRECTIONS[di]
        nq, nr = self.q + dq, self.r + dr
        if (nq, nr) in world.patches:
            self.q, self.r = nq, nr
        else:
            # Reflect: reverse heading and try again
            self.heading += math.pi
            di = heading_to_hex_dir(self.heading)
            dq, dr = HEX_DIRECTIONS[di]
            nq2, nr2 = self.q + dq, self.r + dr
            if (nq2, nr2) in world.patches:
                self.q, self.r = nq2, nr2

    def _move_toward_colony(self, world, sigma):
        """Move to the neighbor closest to (0,0), with angular noise."""
        neighbors = []
        for dq, dr in HEX_DIRECTIONS:
            nq, nr = self.q + dq, self.r + dr
            if (nq, nr) in world.patches:
                d = hex_distance(nq, nr, 0, 0)
                neighbors.append((d, nq, nr))
        if not neighbors:
            return
        neighbors.sort()
        # Noisy: with probability based on sigma, pick 2nd best instead of 1st
        p_noise = min(0.5, sigma / math.pi)
        if len(neighbors) > 1 and random.random() < p_noise:
            _, nq, nr = random.choice(neighbors[:3])
        else:
            _, nq, nr = neighbors[0]
        self.q, self.r = nq, nr


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------


class World:
    def __init__(self, n_ants, n_clusters, food_start):
        self.food_start = food_start
        self.pheromone_decay = PHEROMONE_DECAY
        self.drop_max = PHEROMONE_DROP_MAX
        self.patches = self._build_patches()
        self._place_food(n_clusters, food_start)
        self.ants = [Ant() for _ in range(n_ants)]

    def _build_patches(self):
        patches = {}
        for q in range(-WORLD_RADIUS, WORLD_RADIUS + 1):
            for r in range(-WORLD_RADIUS, WORLD_RADIUS + 1):
                if hex_distance(q, r, 0, 0) <= WORLD_RADIUS:
                    patches[(q, r)] = Patch()
        return patches

    def _place_food(self, n_clusters, food_start):
        all_coords = list(self.patches.keys())
        placed = 0
        attempts = 0
        while placed < n_clusters and attempts < 1000:
            attempts += 1
            cq, cr = random.choice(all_coords)
            d = hex_distance(cq, cr, 0, 0)
            if d < FOOD_MIN_DIST or d > WORLD_RADIUS - FOOD_CLUSTER_RADIUS - 1:
                continue
            # seed food within cluster radius
            for q, r in all_coords:
                if hex_distance(q, r, cq, cr) <= FOOD_CLUSTER_RADIUS:
                    p = self.patches[(q, r)]
                    p.food_count = food_start
                    p.food_start = food_start
            placed += 1

    @property
    def n_outside(self):
        return sum(1 for a in self.ants if a.state != State.IN_COLONY)

    def step(self):
        random.shuffle(self.ants)
        for ant in self.ants:
            ant.step(self)
        if PHEROMONE_DIFFUSION > 0:
            for (q, r), patch in self.patches.items():
                neighbors = [self.patches[q + dq, r + dr]
                             for dq, dr in HEX_DIRECTIONS
                             if (q + dq, r + dr) in self.patches]
                patch.diffuse_out(neighbors)
        for patch in self.patches.values():
            patch.step(self.pheromone_decay, PHEROMONE_THRESHOLD)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def compute_hex_layout(canvas_rect):
    """Return (hex_size, ox, oy) so the hex grid fills the canvas."""
    # Flat-top: horizontal extent = (2*R+1) * 1.5 * hex_size + 0.5 * hex_size
    hex_size_w = canvas_rect.width / ((2 * WORLD_RADIUS + 1) * 1.5 + 0.5)
    # Vertical extent = (2*R+1) * sqrt(3) * hex_size (approximately)
    hex_size_h = canvas_rect.height / ((2 * WORLD_RADIUS + 1) * math.sqrt(3) + math.sqrt(3) / 2)
    hex_size = min(hex_size_w, hex_size_h) * 0.98
    ox = canvas_rect.x + canvas_rect.width / 2
    oy = canvas_rect.y + canvas_rect.height / 2
    return hex_size, ox, oy


def render(screen, world, canvas_rect, hex_size, ox, oy):
    screen.fill(COLOR_BG, canvas_rect)

    # Draw patches
    for (q, r), patch in world.patches.items():
        cx, cy = hex_to_pixel(q, r, hex_size, ox, oy)
        color = patch.color()
        if hex_size >= 2:
            pts = hex_corners(cx, cy, hex_size - 0.5)
            pygame.draw.polygon(screen, color, pts)
        else:
            screen.set_at((int(cx), int(cy)), color)

    # Colony marker
    col_x, col_y = hex_to_pixel(0, 0, hex_size, ox, oy)
    outer_r = max(5, int(hex_size * 2.0))
    inner_r = max(2, outer_r // 2)
    pygame.draw.circle(screen, COLOR_COLONY_OUTER, (int(col_x), int(col_y)), outer_r)
    pygame.draw.circle(screen, COLOR_COLONY_INNER, (int(col_x), int(col_y)), inner_r)

    # Draw ants
    for ant in world.ants:
        if ant.state == State.IN_COLONY:
            continue
        ax, ay = hex_to_pixel(ant.q, ant.r, hex_size, ox, oy)
        color = STATE_COLORS[ant.state]
        pygame.draw.circle(screen, color, (int(ax), int(ay)), ANT_DOT_RADIUS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def make_sliders(control_rect):
    xs, sy, sw, sh = slider_row_geometry(control_rect, 5, pad=12)
    return [
        Slider("Ants",          xs[0], sy, sw, sh,  10, 400, 100),
        Slider("Food Clusters", xs[1], sy, sw, sh,   1,  15,   5),
        Slider("Decay %",       xs[2], sy, sw, sh, 0.01, 15, 1.5, step=0.01),
        Slider("Drop",          xs[3], sy, sw, sh,   1, 100,  35),
        Slider("Speed",         xs[4], sy, sw, sh,   1, 300,  20),
    ]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Ants")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 18)

    canvas_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT - CONTROL_HEIGHT)
    control_rect = pygame.Rect(0, WINDOW_HEIGHT - CONTROL_HEIGHT,
                               WINDOW_WIDTH, CONTROL_HEIGHT)

    sliders = make_sliders(control_rect)
    ants_s, clusters_s, decay_s, drop_s, speed_s = sliders

    def new_world():
        return World(
            n_ants=int(ants_s.value),
            n_clusters=int(clusters_s.value),
            food_start=FOOD_START,
        )

    hex_size, ox, oy = compute_hex_layout(canvas_rect)
    world = new_world()

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
                if slider.handle_event(event) and idx not in (2, 3, 4):  # 2=Decay, 3=Drop, 4=Speed
                    reset_needed = True

        if reset_needed:
            world = new_world()
            epoch_accum = 0.0

        if paused:
            render(screen, world, canvas_rect, hex_size, ox, oy)
            draw_panel(screen, font, control_rect, sliders)
            pygame.display.flip()
            continue

        world.pheromone_decay = 1.0 - decay_s.value / 100.0
        world.drop_max = drop_s.value
        epoch_accum += speed_s.value * dt
        n_epochs = int(epoch_accum)
        epoch_accum -= n_epochs
        for _ in range(n_epochs):
            world.step()

        render(screen, world, canvas_rect, hex_size, ox, oy)
        draw_panel(screen, font, control_rect, sliders)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
