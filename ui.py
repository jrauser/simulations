"""Shared pygame UI utilities used by all simulations."""

import pygame

# ---------------------------------------------------------------------------
# Shared control panel colors
# ---------------------------------------------------------------------------

COLOR_PANEL        = (35, 35, 35)
COLOR_PANEL_BORDER = (60, 60, 60)
COLOR_SLIDER_TRACK = (80, 80, 80)
COLOR_SLIDER_THUMB = (180, 180, 180)
COLOR_LABEL        = (200, 200, 200)

# ---------------------------------------------------------------------------
# Slider
# ---------------------------------------------------------------------------


class Slider:
    _THUMB_W = 12
    _THUMB_INSET = 4

    def __init__(self, label, x, y, w, h, lo, hi, default, step=1):
        self.label = label
        self.rect = pygame.Rect(x, y, w, h)
        self.lo = lo
        self.hi = hi
        self.value = default
        self.step = step
        self.dragging = False
        self.track = pygame.Rect(x, y + h // 2 - 3, w, 6)

    def _thumb_x(self):
        frac = (self.value - self.lo) / (self.hi - self.lo)
        return int(self.rect.x + frac * self.rect.width)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            tx = self._thumb_x()
            hit = pygame.Rect(tx - self._THUMB_W // 2, self.rect.y,
                              self._THUMB_W, self.rect.height)
            if hit.collidepoint(event.pos) or self.track.collidepoint(event.pos):
                self.dragging = True
                return self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            return self._set_from_x(event.pos[0])
        return False

    def _set_from_x(self, x):
        frac = max(0.0, min(1.0, (x - self.rect.x) / self.rect.width))
        raw = self.lo + frac * (self.hi - self.lo)
        new_val = round(round(raw / self.step) * self.step, 10)
        if new_val != self.value:
            self.value = new_val
            return True
        return False

    def draw(self, screen, font):
        pygame.draw.rect(screen, COLOR_SLIDER_TRACK, self.track, border_radius=3)
        tx = self._thumb_x()
        thumb = pygame.Rect(tx - self._THUMB_W // 2,
                            self.rect.y + self._THUMB_INSET,
                            self._THUMB_W,
                            self.rect.height - 2 * self._THUMB_INSET)
        pygame.draw.rect(screen, COLOR_SLIDER_THUMB, thumb, border_radius=4)
        surf = font.render(f"{self.label}: {self.value:g}", True, COLOR_LABEL)
        screen.blit(surf, (self.rect.x, self.rect.y - 18))

# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def slider_row_geometry(control_rect, n, pad=15):
    """Return (xs, sy, sw, sh) for a row of n evenly-spaced sliders.

    xs is a list of n x positions; sy, sw, sh are the shared y, width, height.
    """
    sw = (control_rect.width - (n + 1) * pad) // n
    sy = control_rect.y + 40
    sh = 24
    xs = [control_rect.x + pad + i * (sw + pad) for i in range(n)]
    return xs, sy, sw, sh


def draw_panel(screen, font, control_rect, sliders):
    """Draw the control panel background, border, and all sliders."""
    pygame.draw.rect(screen, COLOR_PANEL, control_rect)
    pygame.draw.line(screen, COLOR_PANEL_BORDER,
                     control_rect.topleft, control_rect.topright)
    for slider in sliders:
        slider.draw(screen, font)
