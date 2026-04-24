import pygame
from config import FLASH_TIME

class Tile:
    def __init__(self, tile_frames, col, row):
        self.tile_frames = tile_frames
        self.correct_pos = (col, row)
        self.current_pos = (col, row)

        self.tile_w = tile_frames[0].get_width()
        self.tile_h = tile_frames[0].get_height()

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

    def draw(self, screen, is_dragged, frame_index = 0):
        current_img = self.tile_frames[frame_index % len(self.tile_frames)]

        screen.blit(current_img, self.rect.topleft)
        border_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        if self.is_correct():
            color = (50, 50, 50, 0)
            thickness = 1
        else:
            color = (50, 50, 50, 180)
            thickness = 2

        pygame.draw.rect(border_surf, color, border_surf.get_rect(), thickness)
        screen.blit(border_surf, self.rect.topleft)

        if is_dragged:
            pygame.draw.rect(screen, (255, 0, 0), self.rect, 3)
        elif self.flash_timer > 0:
            pygame.draw.rect(screen, (0, 255, 0), self.rect, 3)
            self.flash_timer -= 1