import os
import sys
import random
import pygame
from dataclasses import dataclass
from pathlib import Path

# -----------------------------
# Configuration / Constants
# -----------------------------
SCREEN_WIDTH: int = 800
SCREEN_HEIGHT: int = 600
FPS: int = 60

# Physics
GRAVITY: float = 0.8          # Pixels per frame^2 (scaled by dt)
JUMP_POWER: float = -12.0      # Initial upward velocity on jump
MAX_JUMPS: int = 2             # Double-jump

# Platforms (rooftops)
PLATFORM_WIDTH: int = 150
PLATFORM_HEIGHT: int = 10      # Collision surface thickness
PLATFORM_MIN_Y: int = 250      # Min Y for roof
PLATFORM_MAX_Y: int = 400      # Max Y for roof
PLATFORM_Y_DELTA: int = 50     # Max random delta between consecutive roofs
HORIZONTAL_GAP: int = 180      # Fixed horizontal distance between platforms
SCROLL_SPEED: float = 5.0      # Pixels per frame (scaled by dt)

# Obstacles / Coins
OBSTACLE_CHANCE: float = 0.3
COIN_CHANCE: float = 0.5
OBSTACLE_SIZE = (30, 30)
COIN_SIZE = (20, 20)
COIN_OFFSET_ABOVE_ROOF: int = 30
EDGE_PADDING: int = 20         # Padding from platform edges for spawns

# Colors
SKY_BLUE = (135, 206, 235)
BUILDING_COLOR = (80, 80, 80)
ROOF_COLOR = (120, 120, 120)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

# Assets
ASSETS_DIRNAME = "assets"
STICKMAN_FILE = "stickman.png"
CRATE_FILE = "crate.png"
COIN_FILE = "coin.png"
FONT_SIZE: int = 36
START_TEXT = "Press SPACE to start"
WINDOW_TITLE = "Endless Rooftop Runner"

# -----------------------------
# Data classes
# -----------------------------
@dataclass
class Player:
    rect: pygame.Rect
    jump_power: float = JUMP_POWER
    gravity: float = GRAVITY
    y_velocity: float = 0.0
    is_grounded: bool = False
    jump_count: int = 0
    max_jumps: int = MAX_JUMPS

# -----------------------------
# Utility / Logging
# -----------------------------
def log_error(function_name: str, error_message: str) -> None:
    print(f"ERROR in {function_name}: {error_message}", file=sys.stderr)

def log_info(message: str) -> None:
    print(f"INFO: {message}")

def resource_path() -> Path:
    """Return the absolute path to the assets directory, regardless of run location."""
    try:
        base = Path(__file__).parent
    except NameError:  # When frozen or executed differently
        base = Path(os.getcwd())
    return base / ASSETS_DIRNAME

# -----------------------------
# Asset loading
# -----------------------------
def load_and_scale(image_name: str, size: tuple[int, int]) -> pygame.Surface | None:
    """Loads and scales an image from the assets folder, or returns None if it fails."""
    full_path = resource_path() / image_name
    try:
        if not full_path.exists():
            log_error("load_and_scale", f"File not found: {full_path}")
            return None
        image = pygame.image.load(str(full_path)).convert_alpha()
        return pygame.transform.scale(image, size)
    except Exception as e:
        log_error("load_and_scale", f"Failed to load {full_path}: {e}")
        return None

# -----------------------------
# Game functions
# -----------------------------
def spawn_platform(platforms: list[pygame.Rect],
                   obstacles: list[pygame.Rect],
                   coins: list[pygame.Rect],
                   last_platform_y: int,
                   x: int) -> tuple[int, int]:
    """Spawn a single platform at x, choosing y based on last_platform_y, and maybe spawn obstacle/coin.

    Returns (next_spawn_x, new_last_platform_y).
    """
    try:
        # Pick a new roof y near the previous one, within range
        y = random.randint(
            max(PLATFORM_MIN_Y, last_platform_y - PLATFORM_Y_DELTA),
            min(PLATFORM_MAX_Y, last_platform_y + PLATFORM_Y_DELTA)
        )

        platform = pygame.Rect(x, y, PLATFORM_WIDTH, PLATFORM_HEIGHT)
        platforms.append(platform)
        log_info(f"Platform spawned @ x={x}, y={y}")

        # Avoid spawning obstacles/coins on the first few screens
        if x > SCREEN_WIDTH // 4:
            if random.random() < OBSTACLE_CHANCE:
                obstacle_x = x + random.randint(EDGE_PADDING, PLATFORM_WIDTH - OBSTACLE_SIZE[0] - EDGE_PADDING)
                obstacle_y = y - OBSTACLE_SIZE[1]
                obstacles.append(pygame.Rect(obstacle_x, obstacle_y, *OBSTACLE_SIZE))
                log_info(f"Obstacle spawned @ x={obstacle_x}, y={obstacle_y}")

            if random.random() < COIN_CHANCE:
                coin_x = x + random.randint(EDGE_PADDING, PLATFORM_WIDTH - COIN_SIZE[0] - EDGE_PADDING)
                coin_y = y - COIN_SIZE[1] - COIN_OFFSET_ABOVE_ROOF
                coins.append(pygame.Rect(coin_x, coin_y, *COIN_SIZE))
                log_info(f"Coin spawned @ x={coin_x}, y={coin_y}")

        next_x = x + PLATFORM_WIDTH + HORIZONTAL_GAP
        return next_x, y
    except Exception as e:
        log_error("spawn_platform", str(e))
        return x + PLATFORM_WIDTH + HORIZONTAL_GAP, last_platform_y

def reset_game(player: Player,
               platforms: list[pygame.Rect],
               obstacles: list[pygame.Rect],
               coins: list[pygame.Rect]) -> tuple[int, int, int, bool]:
    """Reset all game entities and return (last_platform_x, last_platform_y, score, started)."""
    platforms.clear()
    obstacles.clear()
    coins.clear()

    score = 0
    started = False

    # Initial platform centered horizontally; place roof at 70% of screen height
    initial_platform_x = SCREEN_WIDTH // 2 - PLATFORM_WIDTH // 2
    initial_platform_y = int(SCREEN_HEIGHT * 0.7)

    # Place the first platform explicitly
    platforms.append(pygame.Rect(initial_platform_x, initial_platform_y, PLATFORM_WIDTH, PLATFORM_HEIGHT))

    # Position player on the initial platform roof
    player.rect.x = initial_platform_x + PLATFORM_WIDTH // 2 - player.rect.width // 2
    player.rect.y = initial_platform_y - player.rect.height
    player.y_velocity = 0
    player.is_grounded = True
    player.jump_count = 0

    # Spawn the next platform so generation is continuous
    next_x = initial_platform_x + PLATFORM_WIDTH + HORIZONTAL_GAP
    last_platform_x, last_platform_y = spawn_platform(platforms, obstacles, coins, initial_platform_y, next_x)

    return last_platform_x, last_platform_y, score, started

# -----------------------------
# Main game
# -----------------------------
def main() -> None:
    # Init Pygame
    try:
        pygame.init()
        log_info("Pygame initialized.")
    except Exception as e:
        log_error("pygame.init", str(e))
        sys.exit(1)

    # Window
    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        log_info(f"Screen: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    except Exception as e:
        log_error("pygame.display.set_mode", str(e))
        pygame.quit()
        sys.exit(1)

    # Font
    try:
        font = pygame.font.Font(None, FONT_SIZE)
    except Exception as e:
        log_error("pygame.font.Font", str(e))
        font = None

    # Assets
    stickman_image = load_and_scale(STICKMAN_FILE, (30, 50))
    crate_image = load_and_scale(CRATE_FILE, OBSTACLE_SIZE)
    coin_image = load_and_scale(COIN_FILE, COIN_SIZE)

    # Game state containers
    player = Player(rect=pygame.Rect(SCREEN_WIDTH // 2, 0, 30, 50))
    platforms: list[pygame.Rect] = []
    obstacles: list[pygame.Rect] = []
    coins: list[pygame.Rect] = []

    last_platform_x, last_platform_y, score, game_started = reset_game(player, platforms, obstacles, coins)

    clock = pygame.time.Clock()
    running = True

    while running:
        try:
            dt = clock.tick(FPS) / 1000.0

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    if not game_started:
                        game_started = True
                        log_info("Game started")
                    elif player.jump_count < player.max_jumps:
                        player.y_velocity = player.jump_power
                        player.jump_count += 1
                        player.is_grounded = False
                        log_info("Player jumped")

            if game_started:
                # Apply gravity & movement (scaled by dt and FPS to keep old feel)
                player.y_velocity += player.gravity * dt * FPS
                dy = player.y_velocity * dt * FPS

                old_bottom = player.rect.bottom
                player.rect.y += int(dy)
                player.is_grounded = False

                # Landing check
                if dy > 0:
                    for platform in platforms:
                        if player.rect.colliderect(platform) and old_bottom <= platform.top:
                            player.rect.bottom = platform.top
                            player.y_velocity = 0
                            player.is_grounded = True
                            player.jump_count = 0
                            break

                # Scroll world
                scroll = SCROLL_SPEED * dt * FPS
                for obj_list in (platforms, obstacles, coins):
                    for item in obj_list:
                        item.x -= int(scroll)
                last_platform_x -= int(scroll)

                # Spawn new platform if needed
                if last_platform_x < SCREEN_WIDTH:
                    last_platform_x, last_platform_y = spawn_platform(
                        platforms, obstacles, coins, last_platform_y, last_platform_x
                    )

                # Remove off-screen objects
                for obj_list in (platforms, obstacles, coins):
                    obj_list[:] = [item for item in obj_list if item.right > 0]

                # Coin collection
                for coin in coins[:]:
                    if player.rect.colliderect(coin):
                        coins.remove(coin)
                        score += 1
                        log_info(f"Coin collected! Score: {score}")

                # Obstacle collision
                for obstacle in obstacles[:]:
                    if player.rect.colliderect(obstacle):
                        log_info("Hit obstacle. Game Over!")
                        last_platform_x, last_platform_y, score, game_started = reset_game(
                            player, platforms, obstacles, coins
                        )
                        break

                # Fell off screen
                if player.rect.top > SCREEN_HEIGHT:
                    log_info("Fell off screen. Game Over!")
                    last_platform_x, last_platform_y, score, game_started = reset_game(
                        player, platforms, obstacles, coins
                    )

            # -----------------
            # Drawing
            # -----------------
            screen.fill(SKY_BLUE)

            # Player
            if stickman_image:
                screen.blit(stickman_image, player.rect)
            else:
                pygame.draw.rect(screen, BLUE, player.rect)

            # Buildings & roofs
            for platform in platforms:
                building_rect = pygame.Rect(platform.x, platform.y, platform.width, SCREEN_HEIGHT - platform.y)
                pygame.draw.rect(screen, BUILDING_COLOR, building_rect)
                pygame.draw.rect(screen, ROOF_COLOR, platform)

            # Obstacles
            for obstacle in obstacles:
                if crate_image:
                    screen.blit(crate_image, obstacle)
                else:
                    pygame.draw.rect(screen, BLACK, obstacle)

            # Coins
            for coin in coins:
                if coin_image:
                    screen.blit(coin_image, coin)
                else:
                    pygame.draw.rect(screen, YELLOW, coin)

            # HUD
            if font:
                score_text = font.render(f"Score: {score}", True, BLACK)
                screen.blit(score_text, (10, 10))
                if not game_started:
                    start_text = font.render(START_TEXT, True, BLACK)
                    text_rect = start_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
                    screen.blit(start_text, text_rect)
            else:
                print(f"Score: {score}")
                if not game_started:
                    print(START_TEXT)

            pygame.display.flip()

        except Exception as e:
            log_error("Game Loop", str(e))
            running = False

    try:
        pygame.quit()
        log_info("Pygame quit successfully.")
    except Exception as e:
        log_error("pygame.quit", str(e))


if __name__ == "__main__":
    # Allow running by double-click. If Python is associated with .py, this will start the game.
    main()
