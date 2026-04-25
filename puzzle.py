import pygame
import random
import config
import ui

class Puzzle:
    def __init__(self, preloaded_media, font, current_volume, volume_callback):
        self.frames, self.durations, self.audio_path, self.source_path = preloaded_media
        
        self.img_width, self.img_height = self.frames[0].get_size()
        self.tile_w = self.img_width // config.GRID_SIZE
        self.tile_h = self.img_height // config.GRID_SIZE

        self.screen = pygame.display.set_mode((config.MAX_WINDOW_SIZE + config.SIDEBAR_WIDTH, config.MAX_WINDOW_SIZE))
        self.offset_x = config.SIDEBAR_WIDTH + (config.MAX_WINDOW_SIZE - self.img_width) // 2
        self.offset_y = (config.MAX_WINDOW_SIZE - self.img_height) // 2

        self.tiles = self._create_tiles()

        self.button_win = ui.Button(config.WIN_BUTTON_X, config.WIN_BUTTON_Y, config.WIN_BUTTON_WIDTH, config.WIN_BUTTON_HEIGHT, "Next Puzzle", font, config.TEXT_COLOR, config.WIN_BUTTON_COLOR, config.WIN_BUTTON_PRESS_COLOR, config.WIN_BUTTON_BORDER, 10)
        self.button_skip = ui.Button(config.SKIP_BUTTON_X, config.SKIP_BUTTON_Y, config.SKIP_BUTTON_WIDTH, config.SKIP_BUTTON_HEIGHT, "Skip", font, config.TEXT_COLOR, config.SKIP_BUTTON_COLOR, config.SKIP_BUTTON_PRESS_COLOR, config.SKIP_BUTTON_BORDER)
        self.button_save = ui.Button(config.SAVE_BUTTON_X, config.SAVE_BUTTON_Y, config.SAVE_BUTTON_WIDTH, config.SAVE_BUTTON_HEIGHT, "Save", font, config.TEXT_COLOR, config.SAVE_BUTTON_COLOR, config.SAVE_BUTTON_PRESS_COLOR, config.SAVE_BUTTON_BORDER)
        self.slider = ui.VolumeSlider(config.SLIDER_X, config.SLIDER_Y, config.SLIDER_WIDTH, config.SLIDER_HEIGHT, current_volume, volume_callback)

    def _create_tiles(self):
        """Private helper to chop up the image and shuffle the tiles."""
        tiles = []
        for row in range(config.GRID_SIZE):
            for col in range(config.GRID_SIZE):
                rect = pygame.Rect(col * self.tile_w, row * self.tile_h, self.tile_w, self.tile_h)
                tile_frames = [frame.subsurface(rect) for frame in self.frames]
                tiles.append(Tile(tile_frames, col, row))

        # Shuffle positions
        positions = [(col, row) for row in range(config.GRID_SIZE) for col in range(config.GRID_SIZE)]
        random.shuffle(positions)
        
        for tile, pos in zip(tiles, positions):
            tile.offset_x = self.offset_x
            tile.offset_y = self.offset_y
            tile.move_to(*pos)
            
        return tiles

    def swap_tiles(self, tile1, tile2):
        """Swaps two tiles and triggers their flash animations."""
        old_pos = tile1.current_pos

        tile1.move_to(*tile2.current_pos)
        tile2.move_to(*old_pos)

        tile1.flash_if_correct()
        tile2.flash_if_correct()

    def is_solved(self):
        """Checks if all tiles are in their correct positions."""
        return all(t.is_correct() for t in self.tiles)

class Tile:
    def __init__(self, tile_frames, col, row):
        self.tile_frames = tile_frames
        self.correct_pos = (col, row)
        self.current_pos = (col, row)

        self.tile_w = tile_frames[0].get_width()
        self.tile_h = tile_frames[0].get_height()
        self.offset_x = 0
        self.offset_y = 0

        self.rect = pygame.Rect((col * self.tile_w), (row * self.tile_h), self.tile_w, self.tile_h)
        self.flash_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        self.border_surf = pygame.Surface((self.rect.width, self.rect.height),pygame.SRCALPHA)
        self.flash_timer = 0
        

    def move_to(self, col, row):
        self.current_pos = (col, row)
        self.rect.topleft = (
            self.offset_x + (col * self.tile_w),
            self.offset_y + (row * self.tile_h)
        )

    def is_correct(self):
        return self.current_pos == self.correct_pos

    def flash_if_correct(self):
        if self.is_correct():
            self.flash_timer = config.FLASH_TIME

    def draw(self, screen, is_dragged, frame_index=0):
        current_img = self.tile_frames[frame_index % len(self.tile_frames)]
        screen.blit(current_img, self.rect.topleft)
        is_correct = self.is_correct()

        # Only draw the grid border if it's NOT correct
        if not is_correct:
            pygame.draw.rect(self.border_surf, config.TILE_BORDER_COLOR, self.border_surf.get_rect(), 2)
            screen.blit(self.border_surf, self.rect.topleft)

        # Handle the "Snap" flash overlay
        if self.flash_timer > 0:
            if is_correct:
                flash_color = config.CORRECT_FLASH_BORDER_COLOR
            else:
                flash_color = config.INCORRECT_FLASH_BORDER_COLOR
            pygame.draw.rect(self.flash_surf, flash_color, self.flash_surf.get_rect())
            screen.blit(self.flash_surf, self.rect.topleft)

        # Draw Outer Borders (Drag or Flash)
        if is_dragged:
            pygame.draw.rect(screen, config.SKIP_BUTTON_BORDER, self.rect, 3)
        elif self.flash_timer > 0:
            border_color = config.CORRECT_FLASH_COLOR if is_correct else config.INCORRECT_FLASH_COLOR
            pygame.draw.rect(screen, border_color, self.rect, 3)
            self.flash_timer -= 1