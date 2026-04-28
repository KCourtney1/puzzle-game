import pygame

import utils
import imageDeck
import puzzle as puzzle_mod
import events
import config
import ui
from game_state import GameState
from media_controller import MediaController

def update_animation(puzzle, state, dt):
    if state.is_dragging_seek:
        return

    if puzzle.audio_path and pygame.mixer.music.get_busy():
        audio_pos_ms = pygame.mixer.music.get_pos()

        if audio_pos_ms >= 0:
            real_audio_time = audio_pos_ms + state.audio_offset_ms
            state.current_frame = puzzle.frame_index_for_time(real_audio_time)
    else:
        state.anim_timer_ms += dt
        while True:
            frame_duration = max(1, int(puzzle.durations[state.current_frame]))
            if state.anim_timer_ms < frame_duration:
                break
            state.anim_timer_ms -= frame_duration
            state.current_frame = (state.current_frame + 1) % len(puzzle.frames)

def stop_music():
    pygame.mixer.music.stop()
    try:
        pygame.mixer.music.unload()
    except pygame.error:
        pass

def build_puzzle(media_data, puzzle_area, state):
    puzzle = puzzle_mod.Puzzle(media_data, puzzle_area)
    stop_music()
    utils.clear_temp_folders(exclude_paths=[puzzle.audio_path, puzzle.source_path])
    state.reset_for_new_puzzle()
    if puzzle.audio_path:
        try:
            pygame.mixer.music.load(puzzle.audio_path)
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(state.volume)
        except pygame.error as exc:
            print("Audio load failed:", exc)
    return puzzle

def maybe_advance_puzzle(puzzle, state, media_controller, puzzle_area):
    media_controller.pump()
    if media_controller.has_error():
        state.waiting_for_media = False
        state.wants_next_puzzle = False
        media_controller.clear_error()
        return puzzle

    if not state.wants_next_puzzle:
        return puzzle

    next_media = media_controller.consume_ready_media()
    if next_media is None:
        state.waiting_for_media = True
        media_controller.ensure_prefetch()
        return puzzle

    new_puzzle = build_puzzle(next_media, puzzle_area, state)
    media_controller.ensure_prefetch()
    return new_puzzle

def draw(screen, puzzle, state, controls, font):
    screen.fill(config.BG_MAIN)
    pygame.draw.rect(screen, config.BG_PUZZLE, puzzle.puzzle_area)
    puzzle.draw(screen, state.dragged_tile, state.current_frame)

    controls.save_button.draw(screen)
    if puzzle.audio_path:
        controls.volume_slider.draw(screen)

    if state.puzzle_solved:
        controls.next_button.draw(screen)
    else:
        controls.skip_button.draw(screen)

    controls.search_box.draw(screen)
    if len(puzzle.frames) > 1:
        controls.seek_bar.draw(screen, state.current_frame, len(puzzle.frames))

    if state.waiting_for_media:
        ui.draw_loading_overlay(screen, font)

    pygame.display.flip()

def main():
    pygame.init()
    pygame.mixer.init()
    pygame.key.set_repeat(300, 50)
    pygame.display.set_caption("Image Puzzle Game")
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    puzzle_area = pygame.Rect(config.SIDEBAR_WIDTH, 0, config.MAX_WINDOW_SIZE, config.MAX_WINDOW_SIZE)

    font = pygame.font.SysFont(None, 48)
    state = GameState()

    def volume_callback(volume):
        pygame.mixer.music.set_volume(volume)
        state.volume = volume

    controls = ui.create_game_ui(font, volume_callback, state.volume)

    #deck = imageDeck.LocalImageDeck()
    deck = imageDeck.PexelsImageDeck()
    state.deck = deck

    media_controller = MediaController()
    media_controller.start()
    media_controller.replace_deck(deck)

    pygame.mixer.music.set_volume(state.volume)
    first_media = utils.load_media(deck)
    if first_media is None:
        raise ValueError("Could not load initial media from the selected deck.")
    puzzle = build_puzzle(first_media, puzzle_area, state)
    pygame.scrap.init()
    media_controller.ensure_prefetch()
    clock = pygame.time.Clock()

    while state.running:
        dt = clock.tick(config.FPS)

        media_controller.pump()
        update_animation(puzzle, state, dt)
        events.handle_events(puzzle, state, controls, media_controller)
        puzzle = maybe_advance_puzzle(puzzle, state, media_controller, puzzle_area)
        draw(screen, puzzle, state, controls, font)

    stop_music()
    media_controller.stop()
    utils.clear_temp_folders()
    pygame.quit()

if __name__ == "__main__":
    main()
