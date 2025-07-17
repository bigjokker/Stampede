import pygame
import random
import math
import asyncio
import sys
import os
import ctypes

# Set Windows audio driver workaround before init
if os.name == 'nt':
    os.environ['SDL_AUDIODRIVER'] = 'directsound'

pygame.init()

# Screen setup
WIDTH = 800
HEIGHT = 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stampede - Middle Gameplay Area")

# Colors
WHITE = (255, 255, 255)
TAN = (210, 180, 140)
LIGHT_BROWN = (245, 222, 179)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# Gameplay boundaries
TOP_LIMIT = 100
BOTTOM_LIMIT = 500
LANE_SPACING = 50
LANES = [TOP_LIMIT + i * LANE_SPACING for i in range((BOTTOM_LIMIT - TOP_LIMIT) // LANE_SPACING)]

# Load sprites (assume preloaded in pygbag.toml, no existence checks)
sprite_files = {
    "cowboy_stand.png": (80, 80),
    "cowboy_move_1.png": (80, 80),
    "cowboy_move_2.png": (80, 80),
    "cattle_slow_1.png": (100, 60),
    "cattle_slow_2.png": (100, 60),
    "cattle_fast_1.png": (100, 60),
    "cattle_fast_2.png": (100, 60),
    "cattle_fastest_1.png": (100, 60),
    "cattle_fastest_2.png": (100, 60),
    "desert_bg.png": (800, 600),
    "cactus_1.png": (25, 25),
    "cactus_2.png": (25, 25),
    "cactus_3.png": (25, 25),
    "rope_segment.png": (10, 5),
    "lasso_loop.png": (30, 30),
    "cattle_black.png": (100, 60),
    "skull.png": (50, 50)
}

try:
    for filename, size in sprite_files.items():
        sprite_files[filename] = pygame.transform.scale(pygame.image.load(filename), size)
except Exception as e:
    # Fallback surfaces if loading fails
    COWBOY_STAND = pygame.Surface((80, 80))
    COWBOY_STAND.fill((255, 0, 0))
    COWBOY_FRAMES = [pygame.Surface((80, 80)) for _ in range(2)]
    for frame in COWBOY_FRAMES: frame.fill((255, 0, 0))
    CATTLE_SLOW_FRAMES = [pygame.Surface((100, 60)) for _ in range(2)]
    for frame in CATTLE_SLOW_FRAMES: frame.fill((139, 69, 19))
    CATTLE_FAST_FRAMES = [pygame.Surface((100, 60)) for _ in range(2)]
    for frame in CATTLE_FAST_FRAMES: frame.fill((165, 42, 42))
    CATTLE_FASTEST_FRAMES = [pygame.Surface((100, 60)) for _ in range(2)]
    for frame in CATTLE_FASTEST_FRAMES: frame.fill((200, 0, 0))
    BACKGROUND = pygame.Surface((WIDTH, HEIGHT))
    BACKGROUND.fill((100, 100, 100))
    OBSTACLE_FRAMES = [pygame.Surface((25, 25)) for _ in range(3)]
    for frame in OBSTACLE_FRAMES: frame.fill((0, 255, 0))
    ROPE_SEGMENT = pygame.Surface((10, 5))
    ROPE_SEGMENT.fill(TAN)
    LASSO_LOOP = pygame.Surface((30, 30))
    LASSO_LOOP.fill(TAN)
    POWER_UP = pygame.Surface((100, 60))
    POWER_UP.fill((0, 0, 0))
    SKULL = pygame.Surface((50, 50))
    SKULL.fill((255, 255, 255))
else:
    COWBOY_STAND = sprite_files["cowboy_stand.png"]
    COWBOY_FRAMES = [sprite_files["cowboy_move_1.png"], sprite_files["cowboy_move_2.png"]]
    CATTLE_SLOW_FRAMES = [sprite_files["cattle_slow_1.png"], sprite_files["cattle_slow_2.png"]]
    CATTLE_FAST_FRAMES = [sprite_files["cattle_fast_1.png"], sprite_files["cattle_fast_2.png"]]
    CATTLE_FASTEST_FRAMES = [sprite_files["cattle_fastest_1.png"], sprite_files["cattle_fastest_2.png"]]
    BACKGROUND = sprite_files["desert_bg.png"]
    OBSTACLE_FRAMES = [sprite_files["cactus_1.png"], sprite_files["cactus_2.png"], sprite_files["cactus_3.png"]]
    ROPE_SEGMENT = sprite_files["rope_segment.png"]
    LASSO_LOOP = sprite_files["lasso_loop.png"]
    POWER_UP = sprite_files["cattle_black.png"]
    SKULL = sprite_files["skull.png"]

# Load sounds with platform-specific extension
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)

# Reset audio to default device on Windows (local only)
if os.name == 'nt' and sys.platform != "emscripten":
    try:
        MMDEVAPI = ctypes.windll.winmm
        MMDEVAPI.waveOutMessage(0, 0x400 + 11, 0, 0)  # DRV_QUERYDEVICEINTERFACE (simplified reset)
    except Exception as e:
        print(f"Audio reset failed: {e}")

sound_ext = ".ogg" if sys.platform == "emscripten" else ".wav"
try:
    LASSO_SOUND = pygame.mixer.Sound("lasso" + sound_ext)
    POINT_SOUND = pygame.mixer.Sound("point" + sound_ext)
    HIT_SOUND = pygame.mixer.Sound("hit" + sound_ext)
    YEHA_SOUND = pygame.mixer.Sound("yeha" + sound_ext)
    YEHA_CHANNEL = pygame.mixer.Channel(0)
except Exception as e:
    print(f"Sound loading failed: {e}")
    # Stub sounds if failed
    class StubSound:
        def play(self): pass
        def stop(self): pass
    LASSO_SOUND = StubSound()
    POINT_SOUND = StubSound()
    HIT_SOUND = StubSound()
    YEHA_SOUND = StubSound()

# Conditional import for browser storage
if sys.platform == "emscripten":
    from platform import window

# Helper functions
def load_high_score():
    if sys.platform == "emscripten":
        high_score_str = window.localStorage.getItem("stampede_high_score")
        return int(high_score_str) if high_score_str else 0
    else:
        try:
            with open("high_score.txt", "r") as file:
                return int(file.read().strip())
        except (FileNotFoundError, ValueError):
            return 0

def save_high_score(score):
    if sys.platform == "emscripten":
        window.localStorage.setItem("stampede_high_score", str(score))
    else:
        with open("high_score.txt", "w") as file:
            file.write(str(score))

def load_start_score():
    return 0

# Player class
class Player:
    def __init__(self):
        self.width = 80
        self.height = 80
        self.x = 50
        self.y = (TOP_LIMIT + BOTTOM_LIMIT) // 2
        self.speed = 10
        self.lassolength = 0
        self.lassomax = 180
        self.lasso_loop_radius = 15
        self.frames = COWBOY_FRAMES
        self.stand_frame = COWBOY_STAND
        self.frame_index = 0
        self.frame_timer = 0
        self.lasso_active = False
        self.touch_start_pos = None
        self.is_dragging = False

        self.fixed_angle = math.degrees(math.atan2(30, 180))
        self.rotated_segment = pygame.transform.rotate(ROPE_SEGMENT, -self.fixed_angle)
        self.rotated_loop = pygame.transform.rotate(LASSO_LOOP, -self.fixed_angle)

    def handle_touch_down(self, pos):
        self.touch_start_pos = pos
        self.is_dragging = False

    def handle_touch_move(self, pos):
        if self.touch_start_pos:
            dx = abs(pos[0] - self.touch_start_pos[0])
            dy = abs(pos[1] - self.touch_start_pos[1])
            if dy > 10 or dx > 10:  # Threshold to detect drag
                self.is_dragging = True
            if self.is_dragging:
                target_y = pos[1] - self.height // 2
                self.y = max(TOP_LIMIT, min(target_y, BOTTOM_LIMIT - self.height))

    def handle_touch_up(self, pos):
        if self.touch_start_pos and not self.is_dragging:
            # It's a tap, activate lasso if possible
            if self.lassolength == 0:
                LASSO_SOUND.play()
                self.lassolength = 1
                self.lasso_active = True
        self.touch_start_pos = None
        self.is_dragging = False

    def move(self):
        keys = pygame.key.get_pressed()
        # Keyboard controls (for desktop testing)
        if keys[pygame.K_UP] and self.y > TOP_LIMIT:
            self.y -= self.speed
        if keys[pygame.K_DOWN] and self.y < BOTTOM_LIMIT - self.height:
            self.y += self.speed
        if keys[pygame.K_SPACE] and self.lassolength == 0:
            LASSO_SOUND.play()
            self.lassolength = 1
            self.lasso_active = True

        # Lasso extension logic
        if self.lasso_active:
            if self.lassolength < self.lassomax:
                self.lassolength += 15
            else:
                self.lassolength = 0
                self.lasso_active = False

        self.frame_timer += 1
        if self.frame_timer >= 10:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % 2

    def draw(self, game_state):
        if game_state == "start":
            screen.blit(self.stand_frame, (self.x, self.y))
        else:
            screen.blit(self.frames[self.frame_index], (self.x, self.y))
            if self.lassolength > 0:
                start_x = self.x + self.width
                start_y = self.y + 10
                end_x = start_x + self.lassolength
                end_y = start_y + (30 * self.lassolength / self.lassomax)
                dx = end_x - start_x
                dy = end_y - start_y
                segment_length = 10
                num_segments = self.lassolength // segment_length
                for i in range(num_segments):
                    t = (i + 0.5) * (segment_length / self.lassolength)
                    seg_x = start_x + dx * t
                    seg_y = start_y + dy * t
                    screen.blit(self.rotated_segment, self.rotated_segment.get_rect(center=(seg_x, seg_y)))
                screen.blit(self.rotated_loop, self.rotated_loop.get_rect(center=(end_x, end_y)))

# Cattle class
class Cattle:
    def __init__(self, type_="slow"):
        self.width = 100
        self.height = 60
        self.x = WIDTH
        free_lanes = [lane for lane in LANES if lane not in occupied_lanes]
        self.y = random.choice(free_lanes) if free_lanes else -100
        if self.y >= 0:
            occupied_lanes.add(self.y)
        if type_ == "fastest":
            self.base_speed = random.uniform(4.5, 5.5)
            self.points = 15
            self.frames = CATTLE_FASTEST_FRAMES
        elif type_ == "fast":
            self.base_speed = random.uniform(3.5, 4.5)
            self.points = 10
            self.frames = CATTLE_FAST_FRAMES
        else:
            self.base_speed = random.uniform(2.5, 3.5)
            self.points = 5
            self.frames = CATTLE_SLOW_FRAMES
        self.speed = self.base_speed
        self.frame_index = 0
        self.frame_timer = 0
        self.hit_cowboy = False

    def move(self):
        if self.hit_cowboy:
            self.x += self.speed * 5
            if self.x >= WIDTH:
                self.speed = self.base_speed
                self.hit_cowboy = False
        else:
            self.x -= self.speed
        if self.speed > 0:
            self.frame_timer += 1
            frame_rate = 10 if self.speed < 3 else 7
            if self.frame_timer >= frame_rate:
                self.frame_timer = 0
                self.frame_index = (self.frame_index + 1) % 2

    def remove(self):
        if self.y in occupied_lanes:
            occupied_lanes.remove(self.y)

    def draw(self):
        if self.y >= 0:
            screen.blit(self.frames[self.frame_index], (self.x, self.y))

# PowerUp class
class PowerUp:
    def __init__(self):
        self.width = 100
        self.height = 60
        self.x = WIDTH
        free_lanes = [lane for lane in LANES if lane not in occupied_lanes]
        self.y = random.choice(free_lanes) if free_lanes else -100
        if self.y >= 0:
            occupied_lanes.add(self.y)
        self.speed = 2.0
        self.sprite = POWER_UP

    def move(self):
        self.x -= self.speed

    def remove(self):
        if self.y in occupied_lanes:
            occupied_lanes.remove(self.y)

    def draw(self):
        if self.y >= 0:
            screen.blit(self.sprite, (self.x, self.y))

# Obstacle class
class Obstacle:
    def __init__(self):
        self.width = 25
        self.height = 25
        self.x = WIDTH
        free_lanes = [lane for lane in LANES if lane not in occupied_lanes]
        self.y = random.choice(free_lanes) if free_lanes else -100
        if self.y >= 0:
            occupied_lanes.add(self.y)
        self.speed = 2
        self.frames = OBSTACLE_FRAMES
        self.frame_index = 0
        self.frame_timer = 0

    def move(self):
        self.x -= self.speed
        self.frame_timer += 1
        if self.frame_timer >= 10:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % 3

    def remove(self):
        if self.y in occupied_lanes:
            occupied_lanes.remove(self.y)

    def draw(self):
        if self.y >= 0:
            screen.blit(self.frames[self.frame_index], (self.x, self.y))

# Skull class
class Skull:
    def __init__(self):
        self.width = 50
        self.height = 50
        self.x = WIDTH
        free_lanes = [lane for lane in LANES if lane not in occupied_lanes]
        self.y = random.choice(free_lanes) if free_lanes else -100
        if self.y >= 0:
            occupied_lanes.add(self.y)
        self.speed = 2
        self.sprite = SKULL

    def move(self):
        self.x -= self.speed

    def remove(self):
        if self.y in occupied_lanes:
            occupied_lanes.remove(self.y)

    def draw(self):
        if self.y >= 0:
            screen.blit(self.sprite, (self.x, self.y))

occupied_lanes = set()

async def main():
    global occupied_lanes
    # Game variables
    player = Player()
    cattle_list = []
    obstacles = []
    power_ups = []
    skulls = []
    score = 0
    lives = 3
    font = pygame.font.Font(None, 36)
    game_over_font = pygame.font.Font(None, 74)
    title_font = pygame.font.SysFont("impact", 100)
    clock = pygame.time.Clock()
    spawn_timer = 0
    obstacle_spawn_timer = 0
    hit_sound_timer = 0
    hit_sound_interval = random.randint(120, 240)
    play_time = 0
    difficulty = 1.0
    high_score = load_high_score()
    game_state = "start"
    MAX_CATTLE = 8
    power_up_milestones = {350, 500, 750, 1000}
    spawned_milestones = set()
    power_up_active = False
    last_skull_score = 0

    # Start/restart button for touch
    button_font = pygame.font.Font(None, 40)
    start_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 100, 200, 60)  # For start/restart

    # Game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                save_high_score(high_score)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if game_state == "start":
                    game_state = "play"
                    score = load_start_score()
                elif game_state == "game_over":
                    player = Player()
                    cattle_list = []
                    obstacles = []
                    power_ups = []
                    skulls = []
                    occupied_lanes.clear()
                    score = load_start_score()
                    lives = 3
                    spawn_timer = 0
                    obstacle_spawn_timer = 0
                    hit_sound_timer = 0
                    play_time = 0
                    difficulty = 1.0
                    spawned_milestones.clear()
                    power_up_active = False
                    last_skull_score = 0
                    game_state = "play"
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                if game_state == "start" or game_state == "game_over":
                    if start_rect.collidepoint(pos):
                        if game_state == "start":
                            game_state = "play"
                            score = load_start_score()
                        elif game_state == "game_over":
                            player = Player()
                            cattle_list = []
                            obstacles = []
                            power_ups = []
                            skulls = []
                            occupied_lanes.clear()
                            score = load_start_score()
                            lives = 3
                            spawn_timer = 0
                            obstacle_spawn_timer = 0
                            hit_sound_timer = 0
                            play_time = 0
                            difficulty = 1.0
                            spawned_milestones.clear()
                            power_up_active = False
                            last_skull_score = 0
                            game_state = "play"
                elif game_state == "play":
                    player.handle_touch_down(pos)
            if event.type == pygame.MOUSEMOTION and game_state == "play":
                if pygame.mouse.get_pressed()[0]:
                    pos = event.pos
                    player.handle_touch_move(pos)
            if event.type == pygame.MOUSEBUTTONUP and game_state == "play":
                pos = event.pos
                player.handle_touch_up(pos)

        if game_state == "start":
            screen.blit(BACKGROUND, (0, 0))
            player.draw(game_state)
            title_text = title_font.render("STAMPEDE", True, LIGHT_BROWN)
            title_rect = title_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
            screen.blit(title_text, title_rect)
            # Draw start button
            pygame.draw.rect(screen, GREEN, start_rect)
            start_text = button_font.render("START", True, BLACK)
            screen.blit(start_text, start_text.get_rect(center=start_rect.center))
        elif game_state == "play":
            play_time += 1

            spawn_timer += 1
            spawn_rate = max(30, int(60 / difficulty))
            if spawn_timer >= spawn_rate and len(cattle_list) < MAX_CATTLE:
                roll = random.random()
                if score >= 400:
                    fastest_chance = min(0.3, 0.1 + 0.2 * (play_time - 1800) / 1800) if play_time > 1800 else 0.1
                    if roll < fastest_chance:
                        new_cattle = Cattle("fastest")
                    elif roll < fastest_chance + 0.4:
                        new_cattle = Cattle("fast")
                    else:
                        new_cattle = Cattle("slow")
                else:
                    fast_chance = min(0.4, 0.4 * max(0, play_time - 900) / 900) if play_time > 900 else 0.0
                    new_cattle = Cattle("fast" if roll < fast_chance else "slow")
                if new_cattle.y >= 0:
                    cattle_list.append(new_cattle)
                spawn_timer = 0
                difficulty = min(difficulty + 0.01, 2.5)

            for milestone in power_up_milestones:
                if score >= milestone and milestone not in spawned_milestones:
                    new_power_up = PowerUp()
                    if new_power_up.y >= 0:
                        power_ups.append(new_power_up)
                        spawned_milestones.add(milestone)
                        power_up_active = True
                        HIT_SOUND.stop()

            obstacle_spawn_timer += 1
            if obstacle_spawn_timer >= 180:
                new_obstacle = Obstacle()
                if new_obstacle.y >= 0:
                    obstacles.append(new_obstacle)
                obstacle_spawn_timer = 0

            if score >= last_skull_score + 250 and not any(s.x > WIDTH - 100 for s in skulls):
                new_skull = Skull()
                if new_skull.y >= 0:
                    skulls.append(new_skull)
                    last_skull_score = score

            if len(cattle_list) > 0 and not power_up_active:
                hit_sound_timer += 1
                if hit_sound_timer >= hit_sound_interval:
                    HIT_SOUND.play()
                    hit_sound_interval = random.randint(120, 240)
                    hit_sound_timer = 0

            player.move()
            
            for cattle in cattle_list[:]:
                cattle.move()
                if player.lassolength > 0:
                    lasso_end_x = player.x + player.width + player.lassolength
                    lasso_end_y = player.y + 10 + (30 * player.lassolength / player.lassomax)
                    lasso_end = (lasso_end_x, lasso_end_y)
                    cattle_rect = pygame.Rect(cattle.x, cattle.y, cattle.width, cattle.height)
                    if cattle_rect.clipline((player.x + player.width, player.y + 10), lasso_end):
                        score += cattle.points
                        high_score = max(high_score, score)
                        cattle.remove()
                        cattle_list.remove(cattle)
                        POINT_SOUND.play()
                        continue
                if (cattle.x < player.x + player.width and 
                    cattle.y < player.y + player.height and 
                    cattle.y + cattle.height > player.y and 
                    not cattle.hit_cowboy):
                    cattle.hit_cowboy = True
                    continue
                if cattle.x < 0 and not cattle.hit_cowboy:
                    lives -= 1
                    cattle.remove()
                    cattle_list.remove(cattle)
                    HIT_SOUND.play()

            for power_up in power_ups[:]:
                power_up.move()
                if player.lassolength > 0:
                    lasso_end_x = player.x + player.width + player.lassolength
                    lasso_end_y = player.y + 10 + (30 * player.lassolength / player.lassomax)
                    lasso_end = (lasso_end_x, lasso_end_y)
                    power_up_rect = pygame.Rect(power_up.x, power_up.y, power_up.width, power_up.height)
                    if power_up_rect.clipline((player.x + player.width, player.y + 10), lasso_end):
                        lives += 1
                        power_up.remove()
                        power_ups.remove(power_up)
                        if not power_ups:
                            power_up_active = False
                        LASSO_SOUND.stop()
                        POINT_SOUND.stop()
                        HIT_SOUND.stop()
                        YEHA_CHANNEL.play(YEHA_SOUND)
                        continue
                if power_up.x < -power_up.width:
                    power_up.remove()
                    power_ups.remove(power_up)
                    if not power_ups:
                        power_up_active = False

            for obstacle in obstacles[:]:
                obstacle.move()
                if (obstacle.x < player.x + player.width and 
                    obstacle.x + obstacle.width > player.x and
                    obstacle.y < player.y + player.height and 
                    obstacle.y + obstacle.height > player.y):
                    lives -= 1
                    obstacle.remove()
                    obstacles.remove(obstacle)
                    if not power_up_active:
                        HIT_SOUND.play()
                if obstacle.x < -obstacle.width:
                    obstacle.remove()
                    obstacles.remove(obstacle)

            for skull in skulls[:]:
                skull.move()
                if (skull.x < player.x + player.width and 
                    skull.x + skull.width > player.x and
                    skull.y < player.y + player.height and 
                    skull.y + skull.height > player.y):
                    lives -= 1
                    skull.remove()
                    skulls.remove(skull)
                    if not power_up_active:
                        HIT_SOUND.play()
                elif skull.x < -skull.width:
                    skull.remove()
                    skulls.remove(skull)

            if lives <= 0:
                game_state = "game_over"
                save_high_score(high_score)

            screen.blit(BACKGROUND, (0, 0))
            player.draw(game_state)
            for cattle in cattle_list:
                cattle.draw()
            for power_up in power_ups:
                power_up.draw()
            for obstacle in obstacles:
                obstacle.draw()
            for skull in skulls:
                skull.draw()

            score_text = font.render(f"Score: {score}", True, WHITE)
            high_score_text = font.render(f"High: {high_score}", True, WHITE)
            lives_text = font.render(f"Lives: {lives}", True, WHITE)
            spacing = 50
            total_width = score_text.get_width() + high_score_text.get_width() + lives_text.get_width() + 2 * spacing
            start_x = (WIDTH - total_width) // 2
            screen.blit(score_text, (start_x, 10))
            screen.blit(high_score_text, (start_x + score_text.get_width() + spacing, 10))
            screen.blit(lives_text, (start_x + score_text.get_width() + high_score_text.get_width() + 2 * spacing, 10))

        elif game_state == "game_over":
            screen.blit(BACKGROUND, (0, 0))
            player.draw("play")
            for entity in cattle_list + power_ups + obstacles + skulls:
                entity.draw()

            score_text = font.render(f"Score: {score}", True, WHITE)
            high_score_text = font.render(f"High: {high_score}", True, WHITE)
            lives_text = font.render(f"Lives: {lives}", True, WHITE)
            spacing = 50
            total_width = score_text.get_width() + high_score_text.get_width() + lives_text.get_width() + 2 * spacing
            start_x = (WIDTH - total_width) // 2
            screen.blit(score_text, (start_x, 10))
            screen.blit(high_score_text, (start_x + score_text.get_width() + spacing, 10))
            screen.blit(lives_text, (start_x + score_text.get_width() + high_score_text.get_width() + 2 * spacing, 10))

            game_over_text = game_over_font.render("GAME OVER", True, WHITE)
            screen.blit(game_over_text, game_over_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 25)))

            # Draw restart button
            pygame.draw.rect(screen, GREEN, start_rect)
            restart_text = button_font.render("RESTART", True, BLACK)
            screen.blit(restart_text, restart_text.get_rect(center=start_rect.center))

        pygame.display.flip()
        clock.tick(60)
        await asyncio.sleep(0)

    pygame.quit()

asyncio.run(main())