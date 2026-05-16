import random
import pygame
import config

# Zoom limits
ZOOM_MIN = 0.25
ZOOM_MAX = 4.0
ZOOM_STEP = 0.15  # per scroll tick

class Puzzle:
    def __init__(self, media_asset, puzzle_area):
        self.media = media_asset
        self.puzzle_area = puzzle_area
        self.img_width = self.media.width
        self.img_height = self.media.height

        # Natural (zoom=1) tile dimensions
        self._base_tile_w = self.img_width // config.GRID_SIZE
        self._base_tile_h = self.img_height // config.GRID_SIZE

        # Natural centered offset
        self._base_offset_x = puzzle_area.x + (puzzle_area.width - self.img_width) // 2
        self._base_offset_y = puzzle_area.y + (puzzle_area.height - self.img_height) // 2

        # View state
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0

        # These are set by apply_view() and used everywhere else
        self.offset_x = self._base_offset_x
        self.offset_y = self._base_offset_y
        self.tile_w = self._base_tile_w
        self.tile_h = self._base_tile_h
        self.puzzle_rect = pygame.Rect(
            self.offset_x, self.offset_y,
            self.tile_w * config.GRID_SIZE,
            self.tile_h * config.GRID_SIZE,
        )

        self.tiles = self._create_tiles()

    def apply_view(self):
        """Recompute puzzle_rect and all tile screen rects from current pan/zoom."""
        self.tile_w = max(1, round(self._base_tile_w * self.zoom))
        self.tile_h = max(1, round(self._base_tile_h * self.zoom))
        total_w = self.tile_w * config.GRID_SIZE
        total_h = self.tile_h * config.GRID_SIZE
        self.offset_x = round(self._base_offset_x + self.pan_x + (self._base_tile_w * config.GRID_SIZE - total_w) / 2)
        self.offset_y = round(self._base_offset_y + self.pan_y + (self._base_tile_h * config.GRID_SIZE - total_h) / 2)
        self.puzzle_rect = pygame.Rect(self.offset_x, self.offset_y, total_w, total_h)

        for tile in self.tiles:
            tile.tile_w = self.tile_w
            tile.tile_h = self.tile_h
            tile.offset_x = self.offset_x
            tile.offset_y = self.offset_y
            col, row = tile.current_pos
            tile.rect.topleft = (self.offset_x + col * self.tile_w, self.offset_y + row * self.tile_h)
            tile.rect.width = self.tile_w
            tile.rect.height = self.tile_h

    def zoom_toward(self, mouse_pos, delta):
        """Zoom in/out keeping the point under the mouse fixed."""
        old_zoom = self.zoom
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * (1.0 + delta)))
        if new_zoom == old_zoom:
            return

        # World position of the mouse before zoom (relative to base offset)
        base_origin_x = self._base_offset_x + self.pan_x
        base_origin_y = self._base_offset_y + self.pan_y
        mouse_world_x = (mouse_pos[0] - base_origin_x) / old_zoom
        mouse_world_y = (mouse_pos[1] - base_origin_y) / old_zoom

        self.zoom = new_zoom
        # Adjust pan so mouse_world stays under mouse_pos
        self.pan_x = mouse_pos[0] - self._base_offset_x - mouse_world_x * new_zoom
        self.pan_y = mouse_pos[1] - self._base_offset_y - mouse_world_y * new_zoom
        self.apply_view()

    def clamp_pan(self):
        """Clamp pan so the puzzle can't be dragged fully outside the puzzle area."""
        area = self.puzzle_area
        grid_w = self.tile_w * config.GRID_SIZE
        grid_h = self.tile_h * config.GRID_SIZE

        # Minimum visible overlap — half the grid size, or the full area if the grid is smaller
        min_offset_x = min(area.left, area.right - grid_w)
        max_offset_x = max(area.left, area.right - grid_w)
        
        min_offset_y = min(area.top, area.bottom - grid_h)
        max_offset_y = max(area.top, area.bottom - grid_h)

        clamped_offset_x = max(min_offset_x, min(max_offset_x, self.offset_x))
        clamped_offset_y = max(min_offset_y, min(max_offset_y, self.offset_y))

        if clamped_offset_x != self.offset_x or clamped_offset_y != self.offset_y:
            self.pan_x += clamped_offset_x - self.offset_x
            self.pan_y += clamped_offset_y - self.offset_y
            self.apply_view()

    def reset_view(self):
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self.apply_view()

    def _create_tiles(self):
        """Private helper to build tile source rects and shuffle their positions."""
        tiles = []
        for row in range(config.GRID_SIZE):
            for col in range(config.GRID_SIZE):
                source_rect = pygame.Rect(col * self._base_tile_w, row * self._base_tile_h, self._base_tile_w, self._base_tile_h)
                tiles.append(Tile(source_rect, col, row))

        positions = [(col, row) for row in range(config.GRID_SIZE) for col in range(config.GRID_SIZE)]
        random.shuffle(positions)

        for tile, pos in zip(tiles, positions):
            tile.offset_x = self.offset_x
            tile.offset_y = self.offset_y
            tile.move_to(*pos)

        return tiles

    def swap_tiles(self, tile1, tile2):
        old_pos = tile1.current_pos
        tile1.move_to(*tile2.current_pos)
        tile2.move_to(*old_pos)
        tile1.flash_if_correct()
        tile2.flash_if_correct()

    def is_solved(self):
        return all(t.is_correct() for t in self.tiles)

    @property
    def audio_path(self):
        return self.media.audio_path

    @property
    def source_path(self):
        return self.media.source_path

    @property
    def frame_count(self):
        return self.media.frame_count

    @property
    def is_animated(self):
        return self.media.is_animated

    def frame_duration_ms(self, frame_index):
        return self.media.get_frame_duration_ms(frame_index)

    def frame_index_for_time(self, elapsed_ms):
        return self.media.frame_index_for_time(elapsed_ms)

    def frame_start_ms(self, frame_index):
        return self.media.frame_start_ms(frame_index)

    @property
    def total_duration_ms(self):
        return self.media.total_animation_ms

    def request_frame(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        self.media.request_prefetch(frame_index, backward_radius, forward_radius, immediate_on_jump)

    def request_preview(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        self.media.request_preview_sheet(frame_index, backward_radius, forward_radius, immediate_on_jump)

    def prepare_frame(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        self.media.prepare_frame(frame_index, backward_radius, forward_radius, immediate_on_jump)

    def peek_frame(self, frame_index):
        return self.media.peek_frame(frame_index)

    def peek_preview(self, frame_index):
        return self.media.peek_preview(frame_index)

    def tile_at_position(self, col, row, exclude_tile=None):
        for tile in self.tiles:
            if tile is exclude_tile:
                continue
            if tile.current_pos == (col, row):
                return tile
        return None

    def draw(self, screen, dragged_tile, frame_index):
        current_frame_index = frame_index % self.frame_count
        for tile in self.tiles:
            if tile is not dragged_tile:
                tile.draw(screen, self.media, False, current_frame_index, self.zoom)
        if dragged_tile:
            dragged_tile.draw(screen, self.media, True, current_frame_index, self.zoom)

    def close(self):
        self.media.close()

class Tile:
    def __init__(self, source_rect, col, row):
        self.source_rect = source_rect  # always in original image coords
        self.correct_pos = (col, row)
        self.current_pos = (col, row)

        self.tile_w = source_rect.width
        self.tile_h = source_rect.height
        self.offset_x = 0
        self.offset_y = 0

        self.rect = pygame.Rect((col * self.tile_w), (row * self.tile_h), self.tile_w, self.tile_h)
        self._border_surf_size = None
        self.border_surf = self._build_border_surface()
        self.correct_flash_surf = self._build_flash_surface(config.CORRECT_FLASH_BORDER_COLOR)
        self.incorrect_flash_surf = self._build_flash_surface(config.INCORRECT_FLASH_BORDER_COLOR)
        self.flash_end_time = 0

    def _build_border_surface(self):
        border_surf = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, config.TILE_BORDER_COLOR, border_surf.get_rect(), 2)
        self._border_surf_size = (self.tile_w, self.tile_h)
        return border_surf

    def _build_flash_surface(self, color):
        flash_surf = pygame.Surface((self.tile_w, self.tile_h), pygame.SRCALPHA)
        pygame.draw.rect(flash_surf, color, flash_surf.get_rect())
        return flash_surf

    def _ensure_overlay_surfs(self):
        """Rebuild overlay surfaces if tile size changed due to zoom."""
        if self._border_surf_size != (self.tile_w, self.tile_h):
            self.border_surf = self._build_border_surface()
            self.correct_flash_surf = self._build_flash_surface(config.CORRECT_FLASH_BORDER_COLOR)
            self.incorrect_flash_surf = self._build_flash_surface(config.INCORRECT_FLASH_BORDER_COLOR)

    def move_to(self, col, row):
        self.current_pos = (col, row)
        self.rect.topleft = (
            self.offset_x + (col * self.tile_w),
            self.offset_y + (row * self.tile_h)
        )
        self.rect.width = self.tile_w
        self.rect.height = self.tile_h

    def is_correct(self):
        return self.current_pos == self.correct_pos

    def flash_if_correct(self):
        if self.is_correct():
            self.flash_end_time = pygame.time.get_ticks() + config.FLASH_TIME_MS

    def draw(self, screen, media_asset, is_dragged, frame_index=0, zoom=1.0):
        self._ensure_overlay_surfs()
        dest = self.rect.topleft

        if zoom == 1.0:
            media_asset.blit_region(screen, frame_index, self.source_rect, dest)
        else:
            # Grab the source region and scale it to the current tile screen size
            frame = media_asset.get_frame(frame_index)
            sub = frame.subsurface(self.source_rect)
            scaled = pygame.transform.scale(sub, (self.tile_w, self.tile_h))
            screen.blit(scaled, dest)

        is_correct = self.is_correct()
        now = pygame.time.get_ticks()
        is_flashing = now < self.flash_end_time

        if not is_correct:
            screen.blit(self.border_surf, dest)

        if is_flashing:
            flash_surf = self.correct_flash_surf if is_correct else self.incorrect_flash_surf
            screen.blit(flash_surf, dest)

        if is_dragged:
            pygame.draw.rect(screen, config.SKIP_BUTTON_BORDER, self.rect, 3)
        elif is_flashing:
            border_color = config.CORRECT_FLASH_COLOR if is_correct else config.INCORRECT_FLASH_COLOR
            pygame.draw.rect(screen, border_color, self.rect, 3)
