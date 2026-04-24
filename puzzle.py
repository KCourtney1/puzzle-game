import pygame
import random
import utils
import tile
from dataclasses import dataclass
from config import GRID_SIZE

@dataclass
class PuzzleData:
    frames: list
    durations: list
    audio_path: str | None
    tiles: list
    screen: pygame.Surface
    button_rect: pygame.Rect
    tile_w: int
    tile_h: int

def create_puzzle(frames):
    img_width, img_height = frames[0].get_size()
    tile_w = img_width // GRID_SIZE
    tile_h = img_height // GRID_SIZE

    tiles = []
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            rect = pygame.Rect(
                col * tile_w, 
                row * tile_h, 
                tile_w, 
                tile_h
            )

            tile_frames = [frame.subsurface(rect)for frame in frames]
            tiles.append(tile.Tile(tile_frames, col, row))

    # Shuffle positions
    positions = [(col, row)
        for row in range(GRID_SIZE)
        for col in range(GRID_SIZE)
    ]

    random.shuffle(positions)
    for tile, pos in zip(tiles, positions):
        tile.move_to(*pos)
    return tiles, img_width, img_height, tile_w, tile_h

def new_puzzle(preloaded_media):
    frames, durations, audio_path = preloaded_media
    
    tiles, width, height, tile_w, tile_h = create_puzzle(frames)
    screen = pygame.display.set_mode((width, height))
    button_rect = utils.create_button(width, height)

    return PuzzleData(
        frames, 
        durations, 
        audio_path, 
        tiles, screen, 
        button_rect, 
        tile_w, 
        tile_h
    )

def swap_tiles(tile1, tile2):
    old_pos = tile1.current_pos

    tile1.move_to(*tile2.current_pos)
    tile2.move_to(*old_pos)

    tile1.flash_if_correct()
    tile2.flash_if_correct()