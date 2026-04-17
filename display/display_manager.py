import pygame
import sys
import math
import time
import random
import datetime

WIDTH, HEIGHT = 1024, 600

PHOSPHOR     = (80, 255, 120)
PHOSPHOR_DIM = (25, 90, 40)
BG           = (4, 10, 6)

CHAR_INTERVAL   = 0.028
SCROLL_INTERVAL = 3.2
MAX_VISIBLE     = 5

ART_KEYWORDS  = {"art mode", "art", "screensaver", "show art", "display art", "dot matrix"}
NEXT_KEYWORDS = {"next animation", "change animation", "switch animation", "next mode", "next art"}

# ---------------------------------------------------------------------------
# Face sprites  (12 cols x 10 rows)
# ---------------------------------------------------------------------------
# idle: small calm eyes, gentle arc smile
FACE_IDLE = [
    "000000000000",
    "001100001100",
    "001100001100",
    "000000000000",
    "000000000000",
    "000000000000",
    "010000000010",
    "001111111100",
    "000000000000",
    "000000000000",
]

# listening: eyebrows high + wide 2x2 eyes + straight attentive mouth
FACE_LISTENING = [
    "001100001100",   # raised eyebrows
    "000000000000",   # deliberate gap — brow lift
    "011110011110",   # wide eyes top
    "011110011110",   # wide eyes bottom
    "000000000000",
    "000000000000",
    "000000000000",
    "001111111100",   # flat attentive mouth
    "000000000000",
    "000000000000",
]

# thinking: neutral eyes only — spinner drawn dynamically below
FACE_THINKING = [
    "000000000000",
    "001100001100",
    "001100001100",
    "000000000000",
    "000000000000",
]

FACES = {
    "idle":      FACE_IDLE,
    "listening": FACE_LISTENING,
    "thinking":  FACE_THINKING,
}

# Speaking: eyes only (rows 0-4), waveform fills the mouth area
SPEAKING_BASE = [
    "000000000000",
    "001100001100",
    "001100001100",
    "000000000000",
    "000000000000",
]

# ---------------------------------------------------------------------------
# Knight sprite — original hooded vessel character  (12 cols x 16 rows, 2 frames)
# Inspired by the hollow-knight aesthetic: twin horns, round mask with oval
# eye sockets, flowing cloak, extended nail.
# ---------------------------------------------------------------------------
# Cols layout (0-indexed 0..11):
#   - Outer head: cols 1, 10
#   - Eye sockets: cols 2-3 (left) and 8-9 (right) — these are DARK (0) within head
#   - Horn tips row 0: cols 2, 9  (outer curve)
#   - Horn base row 1: cols 3, 8  (converging inward toward head)
#   - Full head width: cols 1-10
#   - Nail row (widest cloak row): all 12 cols, col 11 is nail tip

KNIGHT_A = [
    "001000000100",   # 0  horn tips
    "000100001000",   # 1  horn base (converging)
    "011111111110",   # 2  head top
    "011111111110",   # 3  head
    "010011110010",   # 4  eye sockets dark at 2-3 and 8-9
    "010011110010",   # 5  eye sockets
    "011111111110",   # 6  chin
    "000111111000",   # 7  neck
    "001111111100",   # 8  shoulders
    "011111111110",   # 9  upper cloak
    "111111111111",   # 10 cloak widest — rightmost col = nail tip
    "011111111110",   # 11 cloak
    "001111111100",   # 12 cloak taper
    "000111111000",   # 13 cloak hem
    "001100000000",   # 14 legs — right foot forward
    "000010000000",   # 15 left foot back
]

KNIGHT_B = [
    "001000000100",
    "000100001000",
    "011111111110",
    "011111111110",
    "010011110010",
    "010011110010",
    "011111111110",
    "000111111000",
    "001111111100",
    "011111111110",
    "111111111111",
    "011111111110",
    "001111111100",
    "000111111000",
    "000011000000",   # 14 legs — left foot forward
    "001000000000",   # 15 right foot back
]

KNIGHT_FRAMES = [KNIGHT_A, KNIGHT_B]

# CLOAK_ROWS: these rows get a sine-wave brightness flutter to simulate fabric
CLOAK_ROWS = {9, 10, 11, 12, 13}


# ---------------------------------------------------------------------------
# Dot matrix art engine
# ---------------------------------------------------------------------------
class DotMatrixArt:
    MODES = ["RIPPLE", "SPIRAL", "RAIN", "PULSE", "NOISE", "KNIGHT"]

    def __init__(self, cols=52, rows=26):
        self.cols = cols
        self.rows = rows
        self.dw = WIDTH  // cols
        self.dh = HEIGHT // rows
        self.t = 0.0
        self.mode_idx = 0
        self.mode_timer = 0.0
        self.mode_duration = 10.0

        # Rain
        self.rain_head  = [random.uniform(0, rows) for _ in range(cols)]
        self.rain_speed = [random.uniform(4, 12)   for _ in range(cols)]

        # Noise
        self.noise_phase = [[random.uniform(0, 2*math.pi) for _ in range(cols)]
                            for _ in range(rows)]

        # Knight
        self.knight_x     = -14.0
        self.knight_frame = 0
        self.knight_ft    = 0.0
        self.knight_speed = 5.0          # grid cols per second
        self.knight_row   = rows - 18    # vertical position in grid
        self._gen_stars()

    def _gen_stars(self):
        self.stars = [
            (random.randint(0, self.cols - 1),
             random.randint(0, self.rows // 2 - 2),
             random.uniform(0, math.pi * 2))
            for _ in range(35)
        ]

    def next_mode(self):
        self.mode_idx = (self.mode_idx + 1) % len(self.MODES)
        if self.MODES[self.mode_idx] == "KNIGHT":
            self.knight_x = -14.0
        self.mode_timer = 0.0

    def update(self, dt):
        self.t += dt
        self.mode_timer += dt
        if self.mode_timer >= self.mode_duration:
            self.next_mode()

        mode = self.MODES[self.mode_idx]

        if mode == "RAIN":
            for c in range(self.cols):
                self.rain_head[c] += self.rain_speed[c] * dt
                if self.rain_head[c] >= self.rows:
                    self.rain_head[c] = 0
                    self.rain_speed[c] = random.uniform(4, 12)

        if mode == "KNIGHT":
            self.knight_x += self.knight_speed * dt
            if self.knight_x > self.cols + 14:
                self.knight_x = -14.0
            self.knight_ft += dt
            if self.knight_ft > 0.20:
                self.knight_frame = 1 - self.knight_frame
                self.knight_ft = 0.0

    def _brightness(self, row, col):
        t    = self.t
        mode = self.MODES[self.mode_idx]
        cx, cy = self.cols / 2, self.rows / 2

        if mode == "RIPPLE":
            d = math.sqrt((col - cx) ** 2 + (row - cy) ** 2)
            return 0.5 + 0.5 * math.sin(d * 0.7 - t * 3.5)

        if mode == "SPIRAL":
            a = math.atan2(row - cy, col - cx)
            d = math.sqrt((col - cx) ** 2 + (row - cy) ** 2)
            return 0.5 + 0.5 * math.sin(a * 4 + d * 0.5 - t * 2.5)

        if mode == "RAIN":
            dist = (row - self.rain_head[col]) % self.rows
            return max(0.05, 1.0 - dist / 6) if dist < 6 else 0.03

        if mode == "PULSE":
            return 0.5 + 0.5 * math.sin((col + row) * 0.25 - t * 5)

        if mode == "NOISE":
            ph = self.noise_phase[row][col]
            return 0.5 + 0.5 * math.sin(ph + t * 1.2 + math.sin(t * 0.7 + col * 0.3))

        return 0.0

    def draw(self, screen):
        if self.MODES[self.mode_idx] == "KNIGHT":
            self._draw_knight(screen)
            return

        r_max = min(self.dw, self.dh) // 2 - 1
        for row in range(self.rows):
            for col in range(self.cols):
                b = max(0.0, min(1.0, self._brightness(row, col)))
                if b < 0.04:
                    continue
                px = col * self.dw + self.dw // 2
                py = row * self.dh + self.dh // 2
                pygame.draw.circle(screen,
                                   (int(80 * b), int(255 * b), int(120 * b)),
                                   (px, py), max(1, int(r_max * b)))

    def _draw_knight(self, screen):
        r = min(self.dw, self.dh) // 2 - 1

        def dot(col, row, b=1.0, flutter=False):
            if col < 0 or col >= self.cols or row < 0 or row >= self.rows:
                return
            b = max(0.0, min(1.0, b))
            if b < 0.05:
                return
            if flutter:
                # cloak pixels ripple slightly
                b = max(0.4, min(1.0, b + 0.18 * math.sin(self.t * 5 + row * 1.4)))
            px = int(col * self.dw + self.dw // 2)
            py = int(row * self.dh + self.dh // 2)
            pygame.draw.circle(screen,
                               (int(80 * b), int(255 * b), int(120 * b)),
                               (px, py), max(1, r))

        # Stars
        for sx, sy, ph in self.stars:
            dot(sx, sy, 0.25 + 0.2 * math.sin(self.t * 1.4 + ph))

        # Dim crescent moon (upper right)
        mc, mr = self.cols - 6, 3
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                if dr * dr + dc * dc <= 5:
                    dot(mc + dc, mr + dr, 0.7)
        # crescent shadow (hollow out right side)
        for dr in range(-1, 2):
            for dc in range(1, 3):
                dot(mc + dc, mr + dr, 0.0)  # no-op since b<0.05

        # Ground
        for c in range(self.cols):
            dot(c, self.rows - 2,
                0.4 + 0.08 * math.sin(self.t * 0.6 + c * 0.3))
            dot(c, self.rows - 1, 0.15)

        # Cloak trail (ghost pixels behind character)
        ox = int(self.knight_x)
        oy = self.knight_row
        for ri in CLOAK_ROWS:
            for trail in range(1, 4):
                dot(ox - trail, oy + ri,
                    0.18 / trail,
                    flutter=True)

        # Knight sprite
        sprite = KNIGHT_FRAMES[self.knight_frame]
        for ri, row_str in enumerate(sprite):
            for ci, ch in enumerate(row_str):
                if ch == "1":
                    dot(ox + ci, oy + ri, 1.0, flutter=(ri in CLOAK_ROWS))


# ---------------------------------------------------------------------------
# Main display manager
# ---------------------------------------------------------------------------
class DisplayManager:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Assistant")
        pygame.mouse.set_visible(False)

        self.font_large = pygame.font.SysFont("monospace", 62)
        self.font_small = pygame.font.SysFont("monospace", 22)
        self.font_tiny  = pygame.font.SysFont("monospace", 15)

        self.state         = "idle"
        self.response_text = ""
        self._lines        = []
        self._scroll_idx   = 0
        self._chars_shown  = 0
        self._type_done    = False
        self._last_char_t  = 0.0
        self._last_scroll_t= 0.0

        self.art_mode = False
        self._dot_art = DotMatrixArt()

        self._t          = 0.0
        self._last_t     = time.time()
        self._blink_acc  = 0.0
        self._next_blink = random.uniform(2.5, 5.0)
        self._blink_open = True

        self._scanlines = self._build_scanlines()
        self._vignette  = self._build_vignette()
        self.clock = pygame.time.Clock()

        # Loading cat image for thinking state
        cat_path = "/home/cwru26ai/assistant/assets/loadingCat.png"
        try:
            raw = pygame.image.load(cat_path).convert()
            iw, ih = raw.get_size()
            scale  = min(240 / iw, 300 / ih)
            self._cat_img = pygame.transform.scale(
                raw, (int(iw * scale), int(ih * scale)))
        except Exception as e:
            print(f"[display] Could not load loadingCat.png: {e}")
            self._cat_img = None

    def _build_scanlines(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for y in range(0, HEIGHT, 2):
            pygame.draw.line(s, (0, 0, 0, 55), (0, y), (WIDTH, y))
        return s

    def _build_vignette(self):
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(140):
            alpha = int(200 * ((140 - i) / 140) ** 2)
            pygame.draw.rect(s, (0, 0, 0, alpha), (i, i, WIDTH - 2*i, HEIGHT - 2*i), 1)
        return s

    # ------------------------------------------------------------------
    def set_state(self, state, text=""):
        self.state = state
        if text != self.response_text:
            self.response_text = text
            self._lines        = self._wrap(text)
            self._scroll_idx   = 0
            self._chars_shown  = 0
            self._type_done    = False
            self._last_char_t  = time.time()
            self._last_scroll_t= time.time()

    def toggle_art_mode(self):
        self.art_mode = not self.art_mode

    def next_art_mode(self):
        self._dot_art.next_mode()

    # ------------------------------------------------------------------
    def update(self):
        now = time.time()
        dt  = min(now - self._last_t, 0.05)
        self._last_t = now
        self._t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_a:
                    self.art_mode = not self.art_mode
                if event.key == pygame.K_n and self.art_mode:
                    self._dot_art.next_mode()

        self.screen.fill(BG)

        if self.art_mode:
            self._dot_art.update(dt)
            self._dot_art.draw(self.screen)
            label = self.font_tiny.render(
                f"[ DOT MATRIX  //  {DotMatrixArt.MODES[self._dot_art.mode_idx]} ]",
                True, PHOSPHOR_DIM)
            self.screen.blit(label, (14, 10))
        else:
            self._tick_blink(dt)
            self._draw_clock()
            self._draw_face()
            self._tick_teletype(now)
            if self._lines:
                self._draw_teletype()

        self.screen.blit(self._scanlines, (0, 0))
        self.screen.blit(self._vignette,  (0, 0))
        pygame.display.flip()
        self.clock.tick(30)

    # ------------------------------------------------------------------
    def _tick_blink(self, dt):
        if self.state != "idle":
            self._blink_open = True
            return
        self._blink_acc += dt
        if self._blink_open and self._blink_acc >= self._next_blink:
            self._blink_open = False
        if not self._blink_open and self._blink_acc >= self._next_blink + 0.15:
            self._blink_open = True
            self._blink_acc  = 0.0
            self._next_blink = random.uniform(2.5, 5.0)

    def _draw_clock(self):
        now   = datetime.datetime.now()
        t_surf = self.font_large.render(now.strftime("%H:%M"), True, PHOSPHOR)
        d_surf = self.font_tiny.render(now.strftime("%A, %b %d"), True, PHOSPHOR_DIM)
        self.screen.blit(t_surf, (WIDTH // 2 - t_surf.get_width() // 2, 28))
        self.screen.blit(d_surf, (WIDTH // 2 - d_surf.get_width() // 2, 98))

    def _draw_face(self):
        cell = 14
        cols = 12
        cx   = WIDTH  // 2
        cy   = HEIGHT // 2 + 55
        ox   = cx - (cols * cell) // 2

        if self.state == "speaking":
            sprite = SPEAKING_BASE
            rows   = len(sprite)
            oy     = cy - (rows * cell) // 2 - (5 * cell) // 2

            for r, row_str in enumerate(sprite):
                for c, ch in enumerate(row_str):
                    if ch != "1":
                        continue
                    flicker = 0.90 + 0.10 * random.random()
                    pygame.draw.rect(self.screen,
                                     tuple(int(v * flicker) for v in PHOSPHOR),
                                     (ox + c*cell + 1, oy + r*cell + 1, cell-2, cell-2))

            wave_y  = oy + rows * cell + cell
            wave_hw = (cols * cell) // 2 - 4
            self._draw_wave(cx, wave_y, wave_hw)

        elif self.state == "thinking":
            self._draw_cat_thinking(cx, cy)

        else:
            sprite = FACES.get(self.state, FACE_IDLE)
            rows   = len(sprite)
            oy     = cy - (rows * cell) // 2

            for r, row_str in enumerate(sprite):
                for c, ch in enumerate(row_str):
                    if ch != "1":
                        continue
                    px = ox + c * cell
                    py = oy + r * cell
                    if not self._blink_open and self.state == "idle" and r in (1, 2):
                        if r == 1:
                            pygame.draw.rect(self.screen, PHOSPHOR,
                                             (px + 1, py + cell // 2, cell - 2, 2))
                        continue
                    flicker = 0.90 + 0.10 * random.random()
                    pygame.draw.rect(self.screen,
                                     tuple(int(v * flicker) for v in PHOSPHOR),
                                     (px + 1, py + 1, cell - 2, cell - 2))

    def _draw_cat_thinking(self, cx, cy):
        """Blit the loadingCat.png image centered on the face position."""
        if self._cat_img is None:
            return
        iw, ih = self._cat_img.get_size()
        self.screen.blit(self._cat_img, (cx - iw // 2, cy - ih // 2))

    def _draw_spinner(self, cx, cy, radius=28):
        """Classic OS-style tick spinner — 12 short radiating lines, sweeping head."""
        n          = 12
        speed      = 1.8        # revolutions per second
        inner_r    = radius * 0.45
        outer_r    = radius
        tick_width = 3
        head_idx   = int(self._t * speed * n) % n

        for i in range(n):
            diff = (head_idx - i) % n
            # full bright at head, fade over ~8 ticks, black after that
            b = max(0.0, 1.0 - diff / 8.0)
            if b < 0.06:
                continue
            b = min(1.0, b + 0.04 * random.random())
            angle = i * 2 * math.pi / n - math.pi / 2   # start at 12 o'clock
            x1 = int(cx + inner_r * math.cos(angle))
            y1 = int(cy + inner_r * math.sin(angle))
            x2 = int(cx + outer_r * math.cos(angle))
            y2 = int(cy + outer_r * math.sin(angle))
            color = tuple(int(v * b) for v in PHOSPHOR)
            pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), tick_width)

    def _draw_wave(self, cx, cy, half_width):
        amp = 9
        t   = self._t * 7.0
        pts = []
        for i in range(half_width + 1):
            env = math.cos(i / half_width * math.pi / 2)
            pts.append((cx + i, cy + amp * env * math.sin(t + i * 0.35)))
        for i in range(half_width, -1, -1):
            x, y = pts[i]
            pts.append((cx - (x - cx), y))
        pygame.draw.lines(self.screen, PHOSPHOR, False, pts, 3)

    # ------------------------------------------------------------------
    def _wrap(self, text):
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w) if cur else w
            if self.font_small.size(test)[0] < WIDTH - 120:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def _tick_teletype(self, now):
        if not self._type_done:
            if now - self._last_char_t >= CHAR_INTERVAL:
                self._chars_shown += 1
                self._last_char_t  = now
                if self._chars_shown >= sum(len(l) + 1 for l in self._lines):
                    self._type_done = True
            return
        total = len(self._lines)
        if (total > MAX_VISIBLE and
                self._scroll_idx + MAX_VISIBLE < total and
                now - self._last_scroll_t >= SCROLL_INTERVAL):
            self._scroll_idx   += 1
            self._last_scroll_t = now

    def _draw_teletype(self):
        visible   = self._lines[self._scroll_idx: self._scroll_idx + MAX_VISIBLE]
        skipped   = sum(len(l) + 1 for l in self._lines[:self._scroll_idx])
        remaining = max(0, self._chars_shown - skipped)
        y = HEIGHT - 158
        cursor_drawn = False

        for line in visible:
            shown     = line[:remaining]
            remaining = max(0, remaining - len(line) - 1)
            if shown:
                surf = self.font_small.render(shown, True, PHOSPHOR)
                self.screen.blit(surf, (WIDTH // 2 - self.font_small.size(line)[0] // 2, y))
            if not cursor_drawn and not self._type_done:
                if int(time.time() * 5) % 2 == 0:
                    cx = (WIDTH // 2 - self.font_small.size(line)[0] // 2
                          + self.font_small.size(shown)[0])
                    pygame.draw.rect(self.screen, PHOSPHOR, (cx, y + 2, 11, 18))
                cursor_drawn = True
            y += 30

        total = len(self._lines)
        if total > MAX_VISIBLE:
            pages = total - MAX_VISIBLE + 1
            dx    = WIDTH // 2 - (pages * 14) // 2
            for i in range(pages):
                pygame.draw.circle(self.screen,
                                   PHOSPHOR if i == self._scroll_idx else PHOSPHOR_DIM,
                                   (dx + i * 14, HEIGHT - 165), 3)