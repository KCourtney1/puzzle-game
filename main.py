import pygame
import threading
import queue
import traceback

import utils
import imageDeck
import puzzle as puzzle_mod
import config

def puzzle_is_solved(tiles):
    return all(t.is_correct() for t in tiles)

def preload_worker(job_q, result_q):
    """Runs in the background to extract the next media file."""
    while True:
        deck = job_q.get()
        if deck is None:
            break

        try:
            media_data = utils.load_media(deck)
            result_q.put(media_data)
        except Exception:
            print("Preload error:")
            traceback.print_exc()

def handle_events(puzzle, state, preload_queue, job_q, deck):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            state["running"] = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if state["puzzle_solved"]:
                    if puzzle.button_rect.collidepoint(event.pos):
                        utils.cleanup_audio(puzzle.audio_path)
                        
                        try:
                            next_media = preload_queue.get()
                        except queue.Empty:
                            print("Preload timeout")
                            return

                        state["next_media"] = next_media
                        state["load_next"] = True
                else:
                    for t in reversed(puzzle.tiles):
                        if t.rect.collidepoint(event.pos):
                            state["dragged_tile"] = t
                            mouse_x, mouse_y = event.pos

                            state["offset_x"] = (t.rect.x - mouse_x)
                            state["offset_y"] = (t.rect.y - mouse_y)

                            puzzle.tiles.append(
                                puzzle.tiles.pop(
                                    puzzle.tiles.index(t)
                                )
                            )
                            break
        elif event.type == pygame.MOUSEMOTION:
            dragged = state["dragged_tile"]
            if dragged:
                mouse_x, mouse_y = event.pos
                dragged.rect.x = (mouse_x + state["offset_x"])
                dragged.rect.y = (mouse_y + state["offset_y"])
        elif event.type == pygame.MOUSEBUTTONUP:
            dragged = state["dragged_tile"]

            if event.button == 1 and dragged:
                center_x, center_y = dragged.rect.center
                col = center_x // dragged.tile_w
                row = center_y // dragged.tile_h

                drop_col = utils.clamp(col, 0, config.GRID_SIZE - 1)
                drop_row = utils.clamp(row, 0, config.GRID_SIZE - 1)
                target_tile = next((t for t in puzzle.tiles
                        if t != dragged and t.current_pos == (drop_col, drop_row)), None
                )

                if target_tile:
                    puzzle_mod.swap_tiles(dragged, target_tile)
                else:
                    dragged.move_to(drop_col, drop_row)
                    dragged.flash_if_correct()

            state["dragged_tile"] = None
            if puzzle_is_solved(puzzle.tiles): state["puzzle_solved"] = True
        
def update_puzzle(puzzle, state, job_q, preload_queue, deck):
    if state.get("load_next"):
        next_media = state["next_media"]
        new_puzzle = puzzle_mod.new_puzzle(next_media)

        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        utils.clear_temp_folders(exclude_path=new_puzzle.audio_path)

        puzzle = new_puzzle
        state["puzzle_solved"] = False
        state["load_next"] = False
        state["current_frame"] = 0
        state["anim_timer"] = 0

        job_q.put(state["deck"])
        if puzzle.audio_path:
            try:
                pygame.mixer.music.load(puzzle.audio_path)
                pygame.mixer.music.play(-1)
            except pygame.error as e:
                print("Audio load failed:", e)
    return puzzle

def update_animation(puzzle, state, dt):
    if puzzle.audio_path and pygame.mixer.music.get_busy():
        audio_pos_ms = pygame.mixer.music.get_pos()

        if audio_pos_ms >= 0:
            frame_dur = puzzle.durations[state["current_frame"]]
            state["current_frame"] = (int(audio_pos_ms / frame_dur)% len(puzzle.frames))
    else:
        state["anim_timer"] += dt
        current_frame = state["current_frame"]
        frame_duration = puzzle.durations[current_frame]
        if state["anim_timer"] >= frame_duration:
            state["anim_timer"] -= frame_duration
            state["current_frame"] = ((current_frame + 1)% len(puzzle.frames))

def draw(puzzle, state, font):
    puzzle.screen.fill((0, 0, 0))

    dragged = state["dragged_tile"]
    frame = state["current_frame"]

    for t in puzzle.tiles:
        t.draw(puzzle.screen, t == dragged, frame)

    if state["puzzle_solved"]:
        pygame.draw.rect(puzzle.screen, (60, 200, 40), puzzle.button_rect, border_radius=10)
        pygame.draw.rect(puzzle.screen, (40, 180, 40), puzzle.button_rect, 3, border_radius=10)

        text_surf = font.render("Next Puzzle", True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=puzzle.button_rect.center)

        puzzle.screen.blit(text_surf, text_rect)
    pygame.display.flip()

def main():
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("Image Puzzle Game")
    font = pygame.font.SysFont(None, 48)

    #deck = imageDeck.LocalImageDeck()
    deck = imageDeck.PexelsImageDeck()

    job_q = queue.Queue()
    preload_queue = queue.Queue()
    worker = threading.Thread(target=preload_worker, args=(job_q, preload_queue), daemon=True)
    worker.start()

    first_media = utils.load_media(deck)
    puzzle = puzzle_mod.new_puzzle(first_media)

    if puzzle.audio_path:
        pygame.mixer.music.load(puzzle.audio_path)
        pygame.mixer.music.play(-1)

    job_q.put(deck)


    #game loop
    clock = pygame.time.Clock()
    state = {
        "running": True,
        "puzzle_solved": False,
        "dragged_tile": None,
        "offset_x": 0,
        "offset_y": 0,
        "anim_timer": 0,
        "current_frame": 0,
        "old_audio": None,
        "deck": deck
    }

    while state["running"]:
        dt = clock.tick(config.FPS)

        update_animation(puzzle, state, dt)
        handle_events(puzzle, state, preload_queue, job_q, deck)

        puzzle = update_puzzle(puzzle, state, job_q, preload_queue, deck)
        if state.get("old_audio"):
            utils.cleanup_audio(state["old_audio"])
            state["old_audio"] = None

        draw(puzzle, state, font)
    
    if puzzle.audio_path:
        utils.cleanup_audio(puzzle.audio_path)
    utils.clear_temp_folders()
    pygame.quit()

if __name__ == "__main__":
    main()