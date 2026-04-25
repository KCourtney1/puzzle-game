import pygame
import config

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