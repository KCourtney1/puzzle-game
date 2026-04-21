import pygame
import random
import sys
import os
from pathlib import Path

# --- Configuration ---
MAX_WINDOW_SIZE = 900
GRID_SIZE = 5
FPS = 600
FLASH_TIME = FPS//10

def clamp(val, low, high):
    return max(low, min(val, high))

def load_image(deck):
    image_path = deck.next_image()
    img = pygame.image.load(image_path)
    return img

def fit_image_to_screen(img):
    img_width, img_height = img.get_size()

    scale = min(MAX_WINDOW_SIZE / img_width, MAX_WINDOW_SIZE / img_height, 1.0)
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    return pygame.transform.smoothscale(img, (new_width, new_height))

def create_puzzle(img):
    img_width, img_height = img.get_size()
    tile_w = img_width // GRID_SIZE
    tile_h = img_height // GRID_SIZE

    tiles = []
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            rect = pygame.Rect(col * tile_w, row * tile_h, tile_w, tile_h)
            tile_img = img.subsurface(rect).copy()
            tiles.append(Tile(tile_img, col, row))

    # Shuffle positions
    positions = [(col, row)
        for row in range(GRID_SIZE)
        for col in range(GRID_SIZE)
    ]

    random.shuffle(positions)
    for tile, pos in zip(tiles, positions):
        tile.move_to(*pos)
    return tiles, img_width, img_height, tile_w, tile_h

def create_button(width, height):
    button_width = 250
    button_height = 60
    return pygame.Rect(
        (width // 2) - (button_width // 2),
        height - button_height - 10,
        button_width,
        button_height
    )

def new_puzzle(image_deck):
    img = fit_image_to_screen(load_image(image_deck))
    tiles, width, height, tile_w, tile_h = create_puzzle(img)
    screen = pygame.display.set_mode((width, height))
    button_rect = create_button(width, height)
    return img, tiles, screen, button_rect, tile_w, tile_h

def swap_tiles(tile1, tile2):
    old_pos = tile1.current_pos

    tile1.move_to(*tile2.current_pos)
    tile2.move_to(*old_pos)

    tile1.flash_if_correct()
    tile2.flash_if_correct()

def puzzle_is_solved(tiles):
    return all(t.is_correct() for t in tiles)

class ImageDeck:
    def __init__(self):
        image_dir = Path(__file__).parent.resolve() / "images"
        if not image_dir.exists():
            print(f"Error: Folder '{image_dir}' missing!")
            sys.exit()

        valid_ext = {'.png', '.jpg', '.jpeg'}
        self.all_images = [
            f for f in image_dir.iterdir()
                if f.is_file() and f.suffix.lower() in valid_ext
        ]

        if not self.all_images:
            print("Error: No images found!")
            sys.exit()
        self.deck = []
        self.shuffle_deck()

    def shuffle_deck(self):
        """Refill and shuffle the deck."""
        self.deck = self.all_images.copy()
        random.shuffle(self.deck)

    def next_image(self):
        """Get next image from deck."""
        if not self.deck:
            self.shuffle_deck()
        return self.deck.pop()

class Tile:
    def __init__(self, tile_img, col, row):
        self.tile_img = tile_img
        self.correct_pos = (col, row)
        self.current_pos = (col, row)

        self.tile_w = tile_img.get_width()
        self.tile_h = tile_img.get_height()

        self.rect = pygame.Rect((col * self.tile_w), (row * self.tile_h), self.tile_w, self.tile_h)
        self.flash_timer = 0

    def move_to(self, col, row):
        self.current_pos = (col, row)
        self.rect.topleft = (
            col * self.tile_w,
            row * self.tile_h
        )

    def is_correct(self):
        return self.current_pos == self.correct_pos

    def flash_if_correct(self):
        if self.is_correct():
            self.flash_timer = FLASH_TIME

    def draw(self, screen, is_dragged):
        screen.blit(self.tile_img, self.rect.topleft)
        border_surf = pygame.Surface( (self.rect.width, self.rect.height), pygame.SRCALPHA)

        if self.is_correct():
            color = (50, 50, 50, 30)
            thickness = 1
        else:
            color = (50, 50, 50, 100)
            thickness = 2

        pygame.draw.rect(border_surf, color, border_surf.get_rect(), thickness)
        screen.blit(border_surf, self.rect.topleft)

        if is_dragged:
            pygame.draw.rect(screen, (255, 0, 0), self.rect, 3)
        elif self.flash_timer > 0:
            pygame.draw.rect(screen, (0, 255, 0), self.rect, 3)
            self.flash_timer -= 1

def main():
    pygame.init()
    image_deck = ImageDeck()
    img, tiles, screen, button_rect, tile_w, tile_h = new_puzzle(image_deck)
    font = pygame.font.SysFont(None, 48)

    pygame.display.set_caption("Image Puzzle Game")
    pygame.font.init()

    #game loop
    clock = pygame.time.Clock()
    puzzle_solved = False
    running = True
    is_dragging = False
    dragged_tile = None
    offset_x = 0
    offset_y = 0

    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Mouse Down
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if puzzle_solved:
                        if button_rect.collidepoint(event.pos):
                            img, tiles, screen, button_rect, tile_w, tile_h = new_puzzle(image_deck)
                            puzzle_solved = False
                    else:
                        for t in reversed(tiles):
                            if t.rect.collidepoint(event.pos):
                                is_dragging = True
                                dragged_tile = t

                                mouse_x, mouse_y = event.pos
                                offset_x = t.rect.x - mouse_x
                                offset_y = t.rect.y - mouse_y

                                tiles.remove(t)
                                tiles.append(t)
                                break
            # Drag
            elif event.type == pygame.MOUSEMOTION:
                if is_dragging and dragged_tile:
                    mouse_x, mouse_y = event.pos
                    dragged_tile.rect.x = mouse_x + offset_x
                    dragged_tile.rect.y = mouse_y + offset_y
            # Drop
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and is_dragging:
                    center_x, center_y = dragged_tile.rect.center
                    drop_col = clamp((center_x // dragged_tile.tile_w), 0, GRID_SIZE - 1)
                    drop_row = clamp((center_y // dragged_tile.tile_h), 0, GRID_SIZE - 1)

                    target_tile = None
                    for t in tiles:
                        if (t != dragged_tile and t.current_pos == (drop_col, drop_row)):
                            target_tile = t
                            break
                    if target_tile:
                        swap_tiles(dragged_tile, target_tile)
                    else:
                        dragged_tile.move_to(drop_col, drop_row)
                        dragged_tile.flash_if_correct()
                    is_dragging = False
                    dragged_tile = None

                    if puzzle_is_solved(tiles):
                        print("🎉 YOU WIN! 🎉")
                        puzzle_solved = True

        # Draw
        screen.fill((0, 0, 0))
        for t in tiles:
            t.draw(screen, t == dragged_tile)

        # Win Overlay
        if puzzle_solved:
            pygame.draw.rect(screen, (60, 200, 40), button_rect, border_radius=10)
            pygame.draw.rect(screen, (40, 180, 40), button_rect, 3,border_radius=10)
            text_surf = font.render("Next Puzzle", True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=button_rect.center)
            screen.blit(text_surf,text_rect)
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()