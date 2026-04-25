import pygame
import random
import utils
from tile import Tile
from dataclasses import dataclass
import config

@dataclass
class PuzzleData:
    frames: list
    durations: list
    audio_path: str | None
    tiles: list
    screen: pygame.Surface
    button_win: pygame.Rect
    button_skip: pygame.Rect
    tile_w: int
    tile_h: int

def create_puzzle(frames):
    img_width, img_height = frames[0].get_size()
    tile_w = img_width // config.GRID_SIZE
    tile_h = img_height // config.GRID_SIZE

    tiles = []
    for row in range(config.GRID_SIZE):
        for col in range(config.GRID_SIZE):
            rect = pygame.Rect(
                col * tile_w, 
                row * tile_h, 
                tile_w, 
                tile_h
            )

            tile_frames = [frame.subsurface(rect)for frame in frames]
            tiles.append(Tile(tile_frames, col, row))

    # Shuffle positions
    positions = [(col, row)
        for row in range(config.GRID_SIZE)
        for col in range(config.GRID_SIZE)
    ]

    random.shuffle(positions)
    for tile, pos in zip(tiles, positions):
        tile.move_to(*pos)
    return tiles, img_width, img_height, tile_w, tile_h

def new_puzzle(preloaded_media):
    frames, durations, audio_path = preloaded_media
    tiles, img_w, img_h, tile_w, tile_h = create_puzzle(frames)

    screen = pygame.display.set_mode((config.MAX_WINDOW_SIZE + config.SIDEBAR_WIDTH, config.MAX_WINDOW_SIZE))
    offset_x = config.SIDEBAR_WIDTH + (config.MAX_WINDOW_SIZE - img_w) // 2
    offset_y = (config.MAX_WINDOW_SIZE - img_h) // 2

    for t in tiles:
        t.offset_x = offset_x
        t.offset_y = offset_y
        t.move_to(*t.current_pos)

    button_win = utils.create_button(25, 50, 200, 60)
    button_skip = utils.create_button(25, 50, 200, 60)

    return PuzzleData(
        frames, durations, audio_path, tiles, screen, 
        button_win, button_skip, tile_w, tile_h
    )

def swap_tiles(tile1, tile2):
    old_pos = tile1.current_pos

    tile1.move_to(*tile2.current_pos)
    tile2.move_to(*old_pos)

    tile1.flash_if_correct()
    tile2.flash_if_correct()