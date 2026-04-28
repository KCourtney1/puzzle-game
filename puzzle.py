import bisect
import random
import pygame
import config

class Puzzle:
    def __init__(self, preloaded_media, puzzle_area):
        self.frames, self.durations, self.audio_path, self.source_path = preloaded_media
        self.puzzle_area = puzzle_area
        self.img_width, self.img_height = self.frames[0].get_size()
        self.tile_w = self.img_width // config.GRID_SIZE
        self.tile_h = self.img_height // config.GRID_SIZE

        self.offset_x = puzzle_area.x + (puzzle_area.width - self.img_width) // 2
        self.offset_y = puzzle_area.y + (puzzle_area.height - self.img_height) // 2
        self.puzzle_rect = pygame.Rect(
            self.offset_x,
            self.offset_y,
            self.tile_w * config.GRID_SIZE,
            self.tile_h * config.GRID_SIZE,
        )
        self.frame_starts = self._build_frame_starts()
        self.total_animation_ms = max(
            self.frame_starts[-1] + max(1, int(self.durations[-1])),
            1,
        )

        self.tiles = self._create_tiles()

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

    def _build_frame_starts(self):
        frame_starts = []
        elapsed_ms = 0
        for duration in self.durations:
            frame_starts.append(elapsed_ms)
            elapsed_ms += max(1, int(duration))
        return frame_starts

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

    def frame_index_for_time(self, elapsed_ms):
        wrapped_ms = elapsed_ms % self.total_animation_ms
        return max(0, bisect.bisect_right(self.frame_starts, wrapped_ms) - 1)

    def frame_start_ms(self, frame_index):
        clamped_index = max(0, min(frame_index, len(self.frame_starts) - 1))
        return self.frame_starts[clamped_index]

    def tile_at_position(self, col, row, exclude_tile=None):
        for tile in self.tiles:
            if tile is exclude_tile:
                continue
            if tile.current_pos == (col, row):
                return tile
        return None

    def draw(self, screen, dragged_tile, frame_index):
        for tile in self.tiles:
            if tile is not dragged_tile:
                tile.draw(screen, False, frame_index)
        if dragged_tile:
            dragged_tile.draw(screen, True, frame_index)

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
        self.border_surf = self._build_border_surface()
        self.correct_flash_surf = self._build_flash_surface(config.CORRECT_FLASH_BORDER_COLOR)
        self.incorrect_flash_surf = self._build_flash_surface(config.INCORRECT_FLASH_BORDER_COLOR)
        self.flash_timer = 0

    def _build_border_surface(self):
        border_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, config.TILE_BORDER_COLOR, border_surf.get_rect(), 2)
        return border_surf

    def _build_flash_surface(self, color):
        flash_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(flash_surf, color, flash_surf.get_rect())
        return flash_surf

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
            screen.blit(self.border_surf, self.rect.topleft)

        # Handle the "Snap" flash overlay
        if self.flash_timer > 0:
            flash_surf = self.correct_flash_surf if is_correct else self.incorrect_flash_surf
            screen.blit(flash_surf, self.rect.topleft)

        # Draw Outer Borders (Drag or Flash)
        if is_dragged:
            pygame.draw.rect(screen, config.SKIP_BUTTON_BORDER, self.rect, 3)
        elif self.flash_timer > 0:
            border_color = config.CORRECT_FLASH_COLOR if is_correct else config.INCORRECT_FLASH_COLOR
            pygame.draw.rect(screen, border_color, self.rect, 3)
            self.flash_timer -= 1
