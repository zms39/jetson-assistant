import pygame
import sys

WIDTH, HEIGHT = 1024, 600

class DisplayManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Assistant")
        self.font_large = pygame.font.SysFont("monospace", 48)
        self.font_small = pygame.font.SysFont("monospace", 24)
        self.state = "idle"
        self.response_text = ""
        self.clock = pygame.time.Clock()

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

        self.screen.fill((10, 10, 20))  # dark background

        if self.state == "idle":
            self._draw_idle()
        elif self.state == "listening":
            self._draw_text("Listening...", (100, 200, 255))
        elif self.state == "thinking":
            self._draw_text("Thinking...", (255, 200, 50))
        elif self.state == "speaking":
            self._draw_wrapped_text(self.response_text, (255, 255, 255))

        pygame.display.flip()
        self.clock.tick(30)

    def _draw_idle(self):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M")
        date = datetime.datetime.now().strftime("%A, %B %d")
        time_surf = self.font_large.render(now, True, (180, 180, 200))
        date_surf = self.font_small.render(date, True, (100, 100, 120))
        self.screen.blit(time_surf, (WIDTH//2 - time_surf.get_width()//2, HEIGHT//2 - 40))
        self.screen.blit(date_surf, (WIDTH//2 - date_surf.get_width()//2, HEIGHT//2 + 30))

    def _draw_text(self, text, color):
        surf = self.font_large.render(text, True, color)
        self.screen.blit(surf, (WIDTH//2 - surf.get_width()//2, HEIGHT//2 - 30))

    def _draw_wrapped_text(self, text, color):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + " " + word if current else word
            if self.font_small.size(test)[0] < WIDTH - 80:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)

        y = HEIGHT//2 - (len(lines) * 32)//2
        for line in lines:
            surf = self.font_small.render(line, True, color)
            self.screen.blit(surf, (40, y))
            y += 32
