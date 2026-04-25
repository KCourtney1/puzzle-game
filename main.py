import pygame
import threading
import queue
import traceback

import utils
import imageDeck
import puzzle as puzzle_mod
import events
import config
import ui

def preload_worker(job_q, result_q):
    """Runs in the background to extract the next media file."""
    while True:
        deck = job_q.get()
        if deck is None:
            break

        while True:
            try:
                media_data = utils.load_media(deck)
                if media_data is not None:
                    result_q.put(media_data)
                    break
            except Exception as e:
                print(f"Background preload failed ({e}). Fetching next image...")
                # traceback.print_exc()
                import time
                time.sleep(1)
        
def update_puzzle(puzzle, state, job_q, preload_queue, deck, font):
    if state.get("waiting_for_media"):
        try:
            next_media = preload_queue.get_nowait()
            state["next_media"] = next_media
            state["load_next"] = True
            state["waiting_for_media"] = False
        except queue.Empty:
            # Still downloading! Do nothing and check again on the next frame.
            pass

    if state.get("load_next"):
        next_media = state["next_media"]

        def volume_callback(volume):
            pygame.mixer.music.set_volume(volume)
            state["volume"] = volume

        new_puzzle = puzzle_mod.Puzzle(next_media, font, state["volume"], volume_callback)

        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        utils.clear_temp_folders(exclude_paths=[new_puzzle.audio_path, new_puzzle.source_path])

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

def update_volume(mouse_x, puzzle, state):
    clamped_x = utils.clamp(mouse_x, puzzle.slider_rect.left, puzzle.slider_rect.right)
    pct = (clamped_x - puzzle.slider_rect.left) / puzzle.slider_rect.width
    state["volume"] = pct
    pygame.mixer.music.set_volume(pct)

def draw(puzzle, state, font):
    puzzle.screen.fill(config.BG_MAIN)
    puzzle_area = pygame.Rect(config.SIDEBAR_WIDTH, 0, config.MAX_WINDOW_SIZE, config.MAX_WINDOW_SIZE)
    pygame.draw.rect(puzzle.screen, config.BG_PUZZLE, puzzle_area)

    dragged = state["dragged_tile"]
    frame = state["current_frame"]

    # --- Draw Tiles ---
    for t in puzzle.tiles:
        if t != dragged:
            t.draw(puzzle.screen, False, frame)
    if dragged:
        dragged.draw(puzzle.screen, True, frame)

    # --- Draw UI Objects ---
    puzzle.slider.draw(puzzle.screen)
    puzzle.button_save.draw(puzzle.screen)
    
    if state["puzzle_solved"]:
        puzzle.button_win.draw(puzzle.screen)
    else:
        puzzle.button_skip.draw(puzzle.screen)

    if state.get("waiting_for_media"):
        ui.draw_loading_overlay(puzzle.screen, font)

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

    state = {
        "running": True,
        "puzzle_solved": False,
        "dragged_tile": None,
        "start_pos": None,
        "offset_x": 0,
        "offset_y": 0,
        "anim_timer": 0,
        "current_frame": 0,
        "old_audio": None,
        "deck": deck,
        "volume": config.INITIAL_VOLUME
    }

    def volume_callback(vol):
        pygame.mixer.music.set_volume(vol)
        state["volume"] = vol
    
    pygame.mixer.music.set_volume(state["volume"])
    first_media = utils.load_media(deck)
    puzzle = puzzle_mod.Puzzle(first_media, font, state["volume"], volume_callback)

    if puzzle.audio_path:
        pygame.mixer.music.load(puzzle.audio_path)
        pygame.mixer.music.play(-1)

    job_q.put(deck)
    clock = pygame.time.Clock()

    while state["running"]:
        dt = clock.tick(config.FPS)

        update_animation(puzzle, state, dt)
        events.handle_events(puzzle, state, preload_queue, job_q, deck)

        puzzle = update_puzzle(puzzle, state, job_q, preload_queue, deck, font)
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