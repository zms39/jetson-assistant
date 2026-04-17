import pygame
import sys
import math
import time
import random
import datetime

WIDTH, HEIGHT = 1024, 600
MAX_VISIBLE_LINES = 4
SCROLL_INTERVAL = 2.5  # seconds per line


class DisplayManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Assistant")

        self.font_large = pygame.font.SysFont("monospace", 64)
        self.font_small = pygame.font.SysFont("monospace", 24)

        self.state = "idle"
        self.response_text = ""
        self._wrapped_lines = []
        self._scroll_index = 0
        self._last_scroll_time = 0

        self.clock = pygame.time.Clock()

        self._t = 0
        self._blink = 0
        self._next_blink = random.uniform(2, 5)

    def set_state(self, state, text=""):
        self.state = state
        if text != self.response_text:
            self.response_text = text
            self._wrapped_lines = self._wrap_text(text)
            self._scroll_index = 0
            self._last_scroll_time = time.time()

    def _wrap_text(self, text):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + " " + word if current else word
            if self.font_small.size(test)[0] < WIDTH - 100:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        self._t += 0.05
        self.screen.fill((10, 10, 20))

        self._draw_clock()
        self._draw_face()

        if self.state in ["speaking", "idle"] and self._wrapped_lines:
            self._draw_scrolling_text((120, 140, 180))

        pygame.display.flip()
        self.clock.tick(30)

    def _draw_scrolling_text(self, color):
        lines = self._wrapped_lines
        total = len(lines)

        # Advance scroll index on a timer if there's more text to show
        now = time.time()
        if (total > MAX_VISIBLE_LINES and
                self._scroll_index + MAX_VISIBLE_LINES < total and
                now - self._last_scroll_time >= SCROLL_INTERVAL):
            self._scroll_index += 1
            self._last_scroll_time = now

        visible = lines[self._scroll_index: self._scroll_index + MAX_VISIBLE_LINES]

        # Scroll indicator dot row
        if total > MAX_VISIBLE_LINES:
            num_pages = total - MAX_VISIBLE_LINES + 1
            dot_y = HEIGHT - 148
            dot_spacing = 12
            dot_x_start = WIDTH // 2 - (num_pages * dot_spacing) // 2
            for i in range(num_pages):
                col = (180, 200, 230) if i == self._scroll_index else (60, 70, 100)
                pygame.draw.circle(self.screen, col,
                                   (dot_x_start + i * dot_spacing, dot_y), 3)

        y = HEIGHT - 130
        for line in visible:
            surf = self.font_small.render(line, True, color)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
            y += 30

    def _draw_clock(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%A, %b %d")

        time_surf = self.font_large.render(time_str, True, (180, 200, 230))
        date_surf = self.font_small.render(date_str, True, (100, 120, 160))

        self.screen.blit(time_surf, (WIDTH // 2 - time_surf.get_width() // 2, 40))
        self.screen.blit(date_surf, (WIDTH // 2 - date_surf.get_width() // 2, 110))

    def _draw_face(self):
        cx = WIDTH // 2
        cy = HEIGHT // 2 + 80

        size = 180

        head_color = {
            "idle": (30, 40, 80),
            "listening": (20, 70, 50),
            "thinking": (80, 60, 20),
            "speaking": (60, 40, 100)
        }[self.state]

        eye_color = {
            "idle": (100, 160, 255),
            "listening": (80, 255, 150),
            "thinking": (255, 200, 80),
            "speaking": (200, 140, 255)
        }[self.state]

        pygame.draw.rect(self.screen, head_color,
                         (cx - size // 2, cy - size // 2, size, size), width=6)

        self._blink += 0.05
        if self._blink > self._next_blink:
            eye_open = False
            if self._blink > self._next_blink + 0.2:
                self._blink = 0
                self._next_blink = random.uniform(2, 5)
        else:
            eye_open = True

        if eye_open:
            pygame.draw.rect(self.screen, eye_color, (cx - 50, cy - 40, 20, 10))
            pygame.draw.rect(self.screen, eye_color, (cx + 30, cy - 40, 20, 10))
        else:
            pygame.draw.line(self.screen, eye_color, (cx - 50, cy - 35), (cx - 30, cy - 35), 3)
            pygame.draw.line(self.screen, eye_color, (cx + 30, cy - 35), (cx + 50, cy - 35), 3)

        self._draw_wave_mouth(cx, cy + 30, eye_color)

    def _draw_wave_mouth(self, cx, cy, color):
        half_width = 40
        settings = {
            "idle": (5, 0.8),
            "listening": (12, 2.5),
            "thinking": (6, 1.2),
            "speaking": (16, 3.5)
        }
        amp, speed = settings[self.state]
        t = self._t * speed
        points = []
        for i in range(half_width + 1):
            u = i / half_width
            envelope = math.cos(u * math.pi / 2)
            y = amp * envelope * math.sin(t + i * 0.4)
            points.append((cx + i, cy + y))
        for i in range(half_width, -1, -1):
            x, y = points[i]
            points.append((cx - (x - cx), y))
        pygame.draw.lines(self.screen, color, False, points, 3)