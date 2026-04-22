from utils import *
from puzzle import *
from tile import Tile
from imageDeck import ImageDeck
import threading
import queue

def puzzle_is_solved(tiles):
    return all(t.is_correct() for t in tiles)

def preload_worker(deck, q):
    """Runs in the background to extract the next media file."""
    media_data = load_media(deck)
    q.put(media_data)

def main():
    pygame.init()
    pygame.mixer.init()
    font = pygame.font.SysFont(None, 48)
    pygame.display.set_caption("Image Puzzle Game")

    image_deck = ImageDeck()
    first_media = load_media(image_deck)
    puzzle = new_puzzle(first_media)

    if puzzle.audio_path:
        pygame.mixer.music.load(puzzle.audio_path)
        pygame.mixer.music.play(-1) # -1 tells Pygame to loop indefinitely

    preload_queue = queue.Queue()
    threading.Thread(target=preload_worker, args=(image_deck, preload_queue), daemon=True).start()

    #game loop
    clock = pygame.time.Clock()
    running = True
    puzzle_solved = False

    dragged_tile = None
    offset_x = 0
    offset_y = 0

    anim_timer = 0
    current_frame = 0

    while running:
        dt = clock.tick(FPS)

        #AUDIO/VIDEO SYNC LOGIC
        if puzzle.audio_path and pygame.mixer.music.get_busy():
            # Slave video directly to the background audio thread's timer
            audio_pos_ms = pygame.mixer.music.get_pos()
            if audio_pos_ms >= 0:
                frame_dur = puzzle.durations[0]
                # Frame index = (Elapsed Time / Time Per Frame) % Total Frames
                current_frame = int(audio_pos_ms / frame_dur) % len(puzzle.frames)
        else:
            # Fallback for GIFs / silent media (Standard dt accumulation)
            anim_timer += dt
            current_frame_duration = puzzle.durations[current_frame]

            if anim_timer >= current_frame_duration:
                anim_timer -= current_frame_duration
                current_frame = (current_frame + 1) % len(puzzle.frames)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Mouse Down
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if puzzle_solved:
                        if puzzle.button_rect.collidepoint(event.pos):
                            cleanup_audio(puzzle.audio_path)

                            next_media = preload_queue.get()
                            puzzle = new_puzzle(next_media)

                            threading.Thread(target=preload_worker, args=(image_deck, preload_queue), daemon=True).start()

                            puzzle_solved = False
                            current_frame = 0
                            anim_timer = 0

                            if puzzle.audio_path:
                                pygame.mixer.music.load(puzzle.audio_path)
                                pygame.mixer.music.play(-1)
                    else:
                        for t in reversed(puzzle.tiles):
                            if t.rect.collidepoint(event.pos):
                                dragged_tile = t
                                mouse_x, mouse_y = event.pos
                                offset_x = t.rect.x - mouse_x
                                offset_y = t.rect.y - mouse_y

                                puzzle.tiles.append(
                                    puzzle.tiles.pop(
                                        puzzle.tiles.index(t)
                                    )
                                )
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
                        (t for t in puzzle.tiles 
                            if t != dragged_tile and t.current_pos == (drop_col, drop_row)), 
                        None
                    )

                    if target_tile:
                        swap_tiles(dragged_tile, target_tile)
                    else:
                        dragged_tile.move_to(drop_col, drop_row)
                        dragged_tile.flash_if_correct()
                    dragged_tile = None

                    if puzzle_is_solved(puzzle.tiles):
                        puzzle_solved = True
        # Draw
        puzzle.screen.fill((0, 0, 0))
        for t in puzzle.tiles:
            t.draw(puzzle.screen,t == dragged_tile,current_frame)

        # Win Overlay
        if puzzle_solved:
            #button
            pygame.draw.rect(
                puzzle.screen, 
                (60, 200, 40), 
                puzzle.button_rect,
                border_radius=10
            )

            pygame.draw.rect(
                puzzle.screen,
                (40, 180, 40),
                puzzle.button_rect,
                3,
                border_radius=10
            )

            text_surf = font.render("Next Puzzle", True, (255, 255, 255))
            text_rect = text_surf.get_rect(center = puzzle.button_rect.center)
            puzzle.screen.blit(text_surf,text_rect)
        pygame.display.flip()
    pygame.quit()

if __name__ == "__main__":
    main()