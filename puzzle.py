from utils import *
from tile import Tile

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