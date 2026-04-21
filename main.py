from utils import *
from imageDeck import ImageDeck
from tile import Tile
from puzzle import *

def puzzle_is_solved(tiles):
    return all(t.is_correct() for t in tiles)

def main():
    pygame.init()
    image_deck = ImageDeck()
    img, tiles, screen, button_rect, tile_w, tile_h = new_puzzle(image_deck)
    font = pygame.font.SysFont(None, 48)

    pygame.display.set_caption("Image Puzzle Game")

    #game loop
    clock = pygame.time.Clock()
    running = True
    puzzle_solved = False
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
                                dragged_tile = t
                                mouse_x, mouse_y = event.pos
                                offset_x = t.rect.x - mouse_x
                                offset_y = t.rect.y - mouse_y

                                tiles.append(tiles.pop(tiles.index(t)))
                                break
            # Drag
            elif event.type == pygame.MOUSEMOTION:
                if dragged_tile:
                    mouse_x, mouse_y = event.pos
                    dragged_tile.rect.x = mouse_x + offset_x
                    dragged_tile.rect.y = mouse_y + offset_y
            # Drop
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and dragged_tile:
                    center_x, center_y = dragged_tile.rect.center
                    col = center_x // dragged_tile.tile_w
                    row = center_y // dragged_tile.tile_h
                    drop_col = clamp(col, 0, GRID_SIZE - 1)
                    drop_row = clamp(row, 0, GRID_SIZE - 1)

                    target_tile = next(
                        (t for t in tiles if t != dragged_tile and t.current_pos == (drop_col, drop_row)), None
                    )
                    if target_tile:
                        swap_tiles(dragged_tile, target_tile)
                    else:
                        dragged_tile.move_to(drop_col, drop_row)
                        dragged_tile.flash_if_correct()
                    dragged_tile = None

                    if puzzle_is_solved(tiles):
                        puzzle_solved = True
        # Draw
        screen.fill((0, 0, 0))
        for t in tiles:
            t.draw(screen, t == dragged_tile)
        # Win Overlay
        if puzzle_solved:
            #button
            pygame.draw.rect(screen, (60, 200, 40), button_rect, border_radius=10)
            pygame.draw.rect(screen, (40, 180, 40), button_rect, 3,border_radius=10)
            text_surf = font.render("Next Puzzle", True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=button_rect.center)
            screen.blit(text_surf,text_rect)
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()