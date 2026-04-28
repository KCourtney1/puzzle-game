import utils
import config
import queue

def handle_events(puzzle, state, preload_queue, job_q, deck):
    for event in utils.pygame.event.get():
        if event.type == utils.pygame.QUIT:
            state["running"] = False

        if puzzle.audio_path and puzzle.slider.handle_event(event):
            continue

        if puzzle.button_save.handle_event(event):
            success = utils.save_to_local(puzzle.source_path)
            if success: print(f"Saved {puzzle.source_path.name} to local images!")
            else: print("Media is already local or failed to save.")
            continue
        
        search_box = state.get("search_box")
        if search_box and search_box.handle_event(event):
            new_query = search_box.text.strip()
            print(f"Updating search query to: '{new_query}'")
            
            # Clear old queued images safely
            try:
                while True: job_q.get_nowait()
            except queue.Empty: pass
            
            try:
                while True: preload_queue.get_nowait()
            except queue.Empty: pass

            # Re-initialize the deck based on the current deck's class type
            current_deck = state["deck"]
            deck_type = type(current_deck)
            
            try:
                if deck_type.__name__ == "LocalImageDeck":
                    print("Local deck doesn't support queries.")
                    new_deck = current_deck
                else:
                    new_deck = deck_type(query=new_query if new_query else None)
                
                # Assign the new deck and force a skip to grab the new images
                state["deck"] = new_deck
                _trigger_next_puzzle(puzzle, state, preload_queue)
                job_q.put(new_deck)
            except Exception as e:
                print(f"Failed to load new deck: {e}")
            continue

        seek_bar = state.get("seek_bar")
        if seek_bar and len(puzzle.frames) > 1:
            progress = seek_bar.handle_event(event)
            if progress is not None:
                # Calculate the exact frame the user dragged to
                target_frame = int(progress * (len(puzzle.frames) - 1))
                state["current_frame"] = target_frame
                
                # If they just released the mouse button, finalize the audio seek
                if event.type == utils.pygame.MOUSEBUTTONUP and event.button == 1:
                    state["is_dragging_seek"] = False
                    if puzzle.audio_path:
                        # Find exactly how many milliseconds into the video this frame is
                        target_time_ms = sum(puzzle.durations[:target_frame])
                        state["audio_offset_ms"] = target_time_ms
                        # Restart audio at the new position
                        utils.pygame.mixer.music.play(-1, start=target_time_ms / 1000.0)
                else:
                    # Keep animation frozen while actively dragging
                    state["is_dragging_seek"] = True
                continue

        if state["puzzle_solved"]:
            if puzzle.button_win.handle_event(event):
                _trigger_next_puzzle(puzzle, state, preload_queue)
                continue
        else:
            if puzzle.button_skip.handle_event(event):
                _trigger_next_puzzle(puzzle, state, preload_queue)
                continue
        
        #Tile Interactions
        if event.type == utils.pygame.MOUSEBUTTONDOWN and event.button == 1:
            for t in reversed(puzzle.tiles):
                if t.rect.collidepoint(event.pos):
                    state["dragged_tile"] = t
                    state["start_pos"] = t.current_pos
                    state["offset_x"] = t.rect.x - event.pos[0]
                    state["offset_y"] = t.rect.y - event.pos[1]
                    puzzle.tiles.append(puzzle.tiles.pop(puzzle.tiles.index(t)))
                    break
                    
        elif event.type == utils.pygame.MOUSEMOTION:
            dragged = state.get("dragged_tile")
            if dragged:
                dragged.rect.x = event.pos[0] + state["offset_x"]
                dragged.rect.y = event.pos[1] + state["offset_y"]
        
        elif event.type == utils.pygame.MOUSEBUTTONUP and event.button == 1:
            dragged = state.get("dragged_tile")
            if dragged is not None:
                puzzle_rect = utils.pygame.Rect(dragged.offset_x, dragged.offset_y, 
                                          puzzle.tile_w * config.GRID_SIZE, 
                                          puzzle.tile_h * config.GRID_SIZE)
                if puzzle_rect.collidepoint(event.pos):
                    rel_x = dragged.rect.centerx - dragged.offset_x
                    rel_y = dragged.rect.centery - dragged.offset_y
                    col = rel_x // dragged.tile_w
                    row = rel_y // dragged.tile_h
                    drop_col = utils.clamp(col, 0, config.GRID_SIZE - 1)
                    drop_row = utils.clamp(row, 0, config.GRID_SIZE - 1)
                    
                    target_tile = next((t for t in puzzle.tiles
                            if t != dragged and t.current_pos == (drop_col, drop_row)), None)

                    if target_tile: puzzle.swap_tiles(dragged, target_tile)
                    else:
                        dragged.move_to(drop_col, drop_row)
                        dragged.flash_if_correct()
                else:
                    if state["start_pos"] is not None: dragged.move_to(*state["start_pos"])
                    
            state["dragged_tile"] = None
            state["start_pos"] = None
            if puzzle.is_solved(): 
                state["puzzle_solved"] = True

def _trigger_next_puzzle(puzzle, state, preload_queue):
    """Helper to handle fetching the next media item from the queue safely."""
    
    if state.get("load_next") or state.get("waiting_for_media"):
        return
    state["waiting_for_media"] = True
    print("Requested next puzzle! Waiting for background worker...")