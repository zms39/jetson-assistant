import pygame
import sys
import math
import time
import random
import datetime

# Screen resolution
WIDTH, HEIGHT = 1024, 600

class DisplayManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Assistant")

        self.font_large = pygame.font.SysFont("monospace", 64)
        self.font_small = pygame.font.SysFont("monospace", 24)

        self.state = "idle"
        self.response_text = ""

        self.clock = pygame.time.Clock()

        # animation timers
        self._t = 0
        self._blink = 0
        self._next_blink = random.uniform(2, 5)

    def set_state(self, state, text=""):
        self.state = state
        self.response_text = text

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

        if self.state in ["speaking", "idle"] and self.response_text:
            self._draw_wrapped_text(self.response_text, (120, 140, 180))

        pygame.display.flip()
        self.clock.tick(30)

    # Clock animations
    def _draw_clock(self):
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%A, %b %d")

        time_surf = self.font_large.render(time_str, True, (180, 200, 230))
        date_surf = self.font_small.render(date_str, True, (100, 120, 160))

        self.screen.blit(time_surf, (WIDTH//2 - time_surf.get_width()//2, 40))
        self.screen.blit(date_surf, (WIDTH//2 - date_surf.get_width()//2, 110))

    # Face animations
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

        # head outline
        pygame.draw.rect(
            self.screen,
            head_color,
            (cx - size//2, cy - size//2, size, size),
            width=6
        )

        # blinking logic
        self._blink += 0.05
        if self._blink > self._next_blink:
            eye_open = False
            if self._blink > self._next_blink + 0.2:
                self._blink = 0
                self._next_blink = random.uniform(2, 5)
        else:
            eye_open = True

        # eyes
        if eye_open:
            pygame.draw.rect(self.screen, eye_color, (cx - 50, cy - 40, 20, 10))
            pygame.draw.rect(self.screen, eye_color, (cx + 30, cy - 40, 20, 10))
        else:
            pygame.draw.line(self.screen, eye_color, (cx - 50, cy - 35), (cx - 30, cy - 35), 3)
            pygame.draw.line(self.screen, eye_color, (cx + 30, cy - 35), (cx + 50, cy - 35), 3)

        # waveform mouth
        self._draw_wave_mouth(cx, cy + 30, eye_color)

    # Waveform details
    def _draw_wave_mouth(self, cx, cy, color):
        half_width = 40

        # state-based behavior
        settings = {
            "idle": (5, 0.8),
            "listening": (12, 2.5),
            "thinking": (6, 1.2),
            "speaking": (16, 3.5)
        }

        amp, speed = settings[self.state]
        t = self._t * speed

        points = []

        # generate right half
        for i in range(half_width + 1):
            u = i / half_width

            # taper edges
            envelope = math.cos(u * math.pi / 2)

            y = amp * envelope * math.sin(t + i * 0.4)

            x = cx + i
            points.append((x, cy + y))

        # mirror left side
        for i in range(half_width, -1, -1):
            x, y = points[i]
            mirrored_x = cx - (x - cx)
            points.append((mirrored_x, y))

        # draw smooth line
        pygame.draw.lines(self.screen, color, False, points, 3)

    # Write text to screen
    def _draw_wrapped_text(self, text, color):
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

        y = HEIGHT - 140
        for line in lines[:3]:
            surf = self.font_small.render(line, True, color)
            self.screen.blit(surf, (WIDTH//2 - surf.get_width()//2, y))
            y += 28