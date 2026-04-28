import utils
import config

def handle_events(puzzle, state, controls, media_controller):
    for event in utils.pygame.event.get():
        if event.type == utils.pygame.QUIT:
            state.running = False

        if puzzle.audio_path and controls.volume_slider.handle_event(event):
            continue

        if controls.save_button.handle_event(event):
            success = utils.save_to_local(puzzle.source_path)
            if success: print(f"Saved {puzzle.source_path.name} to local images!")
            else: print("Media is already local or failed to save.")
            continue

        if controls.search_box.handle_event(event):
            search_box = controls.search_box
            new_query = search_box.text.strip()
            print(f"Updating search query to: '{new_query}'")

            # Re-initialize the deck based on the current deck's class type
            current_deck = state.deck
            deck_type = type(current_deck)

            try:
                if deck_type.__name__ == "LocalImageDeck":
                    print("Local deck doesn't support queries.")
                    new_deck = current_deck
                else:
                    new_deck = deck_type(query=new_query if new_query else None)

                state.deck = new_deck
                media_controller.replace_deck(new_deck)
                media_controller.ensure_prefetch()
                _trigger_next_puzzle(state, media_controller)
            except Exception as e:
                print(f"Failed to load new deck: {e}")
            continue

        if len(puzzle.frames) > 1:
            progress = controls.seek_bar.handle_event(event)
            if progress is not None:
                # Calculate the exact frame the user dragged to
                target_frame = int(progress * (len(puzzle.frames) - 1))
                state.current_frame = target_frame

                # If they just released the mouse button, finalize the audio seek
                if event.type == utils.pygame.MOUSEBUTTONUP and event.button == 1:
                    state.is_dragging_seek = False
                    if puzzle.audio_path:
                        # Find exactly how many milliseconds into the video this frame is
                        target_time_ms = puzzle.frame_start_ms(target_frame)
                        state.audio_offset_ms = target_time_ms
                        # Restart audio at the new position
                        utils.pygame.mixer.music.play(-1, start=target_time_ms / 1000.0)
                else:
                    # Keep animation frozen while actively dragging
                    state.is_dragging_seek = True
                continue

        if state.puzzle_solved:
            if controls.next_button.handle_event(event):
                _trigger_next_puzzle(state, media_controller)
                continue
        else:
            if controls.skip_button.handle_event(event):
                _trigger_next_puzzle(state, media_controller)
                continue

        # Tile Interactions
        if event.type == utils.pygame.MOUSEBUTTONDOWN and event.button == 1:
            for t in reversed(puzzle.tiles):
                if t.rect.collidepoint(event.pos):
                    state.dragged_tile = t
                    state.start_pos = t.current_pos
                    state.offset_x = t.rect.x - event.pos[0]
                    state.offset_y = t.rect.y - event.pos[1]
                    puzzle.tiles.append(puzzle.tiles.pop(puzzle.tiles.index(t)))
                    break

        elif event.type == utils.pygame.MOUSEMOTION:
            dragged = state.dragged_tile
            if dragged:
                dragged.rect.x = event.pos[0] + state.offset_x
                dragged.rect.y = event.pos[1] + state.offset_y

        elif event.type == utils.pygame.MOUSEBUTTONUP and event.button == 1:
            dragged = state.dragged_tile
            if dragged is not None:
                if puzzle.puzzle_rect.collidepoint(event.pos):
                    rel_x = dragged.rect.centerx - puzzle.puzzle_rect.left
                    rel_y = dragged.rect.centery - puzzle.puzzle_rect.top
                    col = rel_x // dragged.tile_w
                    row = rel_y // dragged.tile_h
                    drop_col = utils.clamp(col, 0, config.GRID_SIZE - 1)
                    drop_row = utils.clamp(row, 0, config.GRID_SIZE - 1)

                    target_tile = puzzle.tile_at_position(drop_col, drop_row, exclude_tile=dragged)

                    if target_tile:
                        puzzle.swap_tiles(dragged, target_tile)
                    else:
                        dragged.move_to(drop_col, drop_row)
                        dragged.flash_if_correct()
                else:
                    if state.start_pos is not None:
                        dragged.move_to(*state.start_pos)

            state.dragged_tile = None
            state.start_pos = None
            if puzzle.is_solved():
                state.puzzle_solved = True

def _trigger_next_puzzle(state, media_controller):
    """Queues a move to the next puzzle, using preloaded media when available."""
    if state.wants_next_puzzle:
        return

    state.wants_next_puzzle = True
    state.waiting_for_media = not media_controller.has_ready_media()
    media_controller.ensure_prefetch()
    if state.waiting_for_media:
        print("Requested next puzzle! Waiting for background worker...")
