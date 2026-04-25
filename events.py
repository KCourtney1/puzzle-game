import utils
import config

def handle_events(puzzle, state, preload_queue, job_q, deck):
    for event in utils.pygame.event.get():
        if event.type == utils.pygame.QUIT:
            state["running"] = False

        if puzzle.slider.handle_event(event):
            continue

        if puzzle.button_save.handle_event(event):
            success = utils.save_to_local(puzzle.source_path)
            if success: print(f"Saved {puzzle.source_path.name} to local images!")
            else: print("Media is already local or failed to save.")
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