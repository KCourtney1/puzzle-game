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
    if puzzle.audio_path and pygame.mixer.music.get_busy():
        audio_pos_ms = pygame.mixer.music.get_pos()

        if audio_pos_ms >= 0:
            real_audio_time = audio_pos_ms + state.audio_offset_ms
            state.current_frame = puzzle.frame_index_for_time(real_audio_time)
    else:
        state.anim_timer_ms += dt
        while True:
            frame_duration = puzzle.frame_duration_ms(state.current_frame)
            if state.anim_timer_ms < frame_duration:
                break
            state.anim_timer_ms -= frame_duration
            state.current_frame = (state.current_frame + 1) % puzzle.frame_count

def stop_music():
    pygame.mixer.music.stop()
    try:
        pygame.mixer.music.unload()
    except pygame.error:
        pass

def build_puzzle(media_asset, puzzle_area, state, previous_puzzle=None):
    stop_music()
    if previous_puzzle is not None:
        previous_puzzle.close()

    puzzle = puzzle_mod.Puzzle(media_asset, puzzle_area)
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

    next_media_asset = media_controller.consume_ready_media()
    if next_media_asset is None:
        state.waiting_for_media = True
        media_controller.ensure_prefetch()
        return puzzle

    new_puzzle = build_puzzle(next_media_asset, puzzle_area, state, previous_puzzle=puzzle)
    media_controller.ensure_prefetch()
    return new_puzzle

def draw(screen, puzzle, state, controls, font, deck_spec, media_controller=None):
    deck_label = deck_spec.label if deck_spec is not None else "Puzzle"
    show_search = deck_spec.supports_search if deck_spec is not None else False
    show_volume = bool(puzzle.audio_path)

    screen.fill(config.BG_MAIN)
    puzzle.request_frame(
        state.current_frame,
        config.PLAYBACK_PREFETCH_BACKWARD_RADIUS,
        config.PLAYBACK_PREFETCH_FORWARD_RADIUS,
    )
    if state.is_dragging_seek and state.seek_preview_frame is not None:
        puzzle.request_preview(
            state.seek_preview_frame,
            config.SEEK_PREVIEW_SHEET_BACKWARD_RADIUS,
            config.SEEK_PREVIEW_SHEET_FORWARD_RADIUS,
        )
    ui.draw_game_chrome(screen, controls, deck_label)
    pygame.draw.rect(screen, config.BG_PUZZLE, puzzle.puzzle_area)
    
    # Clip the screen so zoomed-in tiles don't spill over the UI
    screen.set_clip(puzzle.puzzle_area)
    puzzle.draw(screen, state.dragged_tile, state.current_frame)
    screen.set_clip(None) # Remove the clip so buttons draw normally

    if state.puzzle_solved:
        controls.next_button.draw(screen)
    else:
        controls.skip_button.draw(screen)

    controls.save_button.draw(screen)
    if show_search:
        controls.search_box.draw(screen)
    if show_volume:
        controls.volume_slider.draw(screen)
    controls.menu_button.draw(screen)

    if puzzle.is_animated:
        controls.seek_bar.draw(screen, state.current_frame, puzzle.frame_count)
        if state.is_dragging_seek and state.seek_preview_frame is not None:
            ui.draw_seek_preview(screen, puzzle, controls, state.seek_preview_frame)

    if state.waiting_for_media:
        status_text = media_controller.get_status()
        ui.draw_loading_overlay(screen, font, status_text)

    pygame.display.flip()

def _deck_search_text(deck):
    if hasattr(deck, "query"):
        return getattr(deck, "query") or ""
    if hasattr(deck, "tags"):
        return getattr(deck, "tags") or ""
    return ""

def _deck_search_title(deck):
    if isinstance(deck, imageDeck.PexelsImageDeck):
        return "Search:"
    return ""

def start_selected_deck(state, controls, media_controller, puzzle_area):
    deck = imageDeck.create_deck(state.selected_deck_key)
    state.deck = deck
    state.menu_error = None

    controls.search_box.set_title(_deck_search_title(deck))
    controls.search_box.set_text(_deck_search_text(deck))
    media_controller.replace_deck(deck)

    first_media_asset = utils.load_media(deck)
    if first_media_asset is None:
        raise ValueError("Could not load initial media from the selected deck.")

    puzzle = build_puzzle(first_media_asset, puzzle_area, state)
    media_controller.ensure_prefetch()
    state.screen = "game"
    return puzzle

def return_to_main_menu(state, controls, media_controller, puzzle):
    if state.deck is not None:
        for spec in imageDeck.get_deck_specs():
            if isinstance(state.deck, spec.factory):
                state.selected_deck_key = spec.key
                break

    stop_music()
    if puzzle is not None:
        puzzle.close()
    utils.clear_temp_folders()
    media_controller.replace_deck(None)
    state.deck = None
    state.menu_error = None
    state.screen = "menu"
    state.reset_for_new_puzzle()
    controls.search_box.set_title("Search / Tags:")
    controls.search_box.set_text("")

def main():
    pygame.init()
    pygame.mixer.init()
    pygame.key.set_repeat(300, 50)
    pygame.display.set_caption("Image Puzzle Game")

    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), vsync=1)
    pygame.scrap.init()
    puzzle_area = pygame.Rect(
        config.PUZZLE_AREA_X,
        config.PUZZLE_AREA_Y,
        config.PUZZLE_AREA_WIDTH,
        config.PUZZLE_AREA_HEIGHT,
    )

    font = pygame.font.SysFont(None, 48)
    state = GameState()

    def volume_callback(volume):
        pygame.mixer.music.set_volume(volume)
        state.volume = volume

    controls = ui.create_game_ui(font, volume_callback, state.volume)
    menu_ui = ui.create_menu_ui(imageDeck.get_deck_specs())

    media_controller = MediaController()
    media_controller.start()

    pygame.mixer.music.set_volume(state.volume)
    puzzle = None
    clock = pygame.time.Clock()

    while state.running:
        dt = clock.tick(0)

        if state.screen == "menu":
            should_start = events.handle_menu_events(state, menu_ui)
            if should_start:
                try:
                    puzzle = start_selected_deck(state, controls, media_controller, puzzle_area)
                except BaseException as exc:
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    stop_music()
                    media_controller.replace_deck(None)
                    state.menu_error = str(exc)
            ui.draw_main_menu(screen, menu_ui, state, imageDeck.DECK_SPECS_BY_KEY)
            continue

        deck_spec = imageDeck.get_deck_spec_for_instance(state.deck)
        show_search = deck_spec.supports_search if deck_spec is not None else False
        show_volume = bool(puzzle.audio_path)
        # layout_game_sidebar only needs to run when the sidebar flags change,
        # not on every frame — so we track the last values and skip if unchanged.
        layout_key = (show_search, show_volume)
        if not hasattr(main, '_last_layout_key') or main._last_layout_key != layout_key:
            main._last_layout_key = layout_key
            ui.layout_game_sidebar(controls, show_search, show_volume)
        media_controller.pump()
        update_animation(puzzle, state, dt)
        action = events.handle_events(puzzle, state, controls, media_controller)
        if action == "menu":
            main._last_layout_key = None
            return_to_main_menu(state, controls, media_controller, puzzle)
            puzzle = None
            ui.draw_main_menu(screen, menu_ui, state, imageDeck.DECK_SPECS_BY_KEY)
            continue
        puzzle = maybe_advance_puzzle(puzzle, state, media_controller, puzzle_area)
        draw(screen, puzzle, state, controls, font, deck_spec, media_controller)

    stop_music()
    if puzzle is not None:
        puzzle.close()
    media_controller.stop()
    utils.clear_temp_folders()
    pygame.quit()

if __name__ == "__main__":
    main()
