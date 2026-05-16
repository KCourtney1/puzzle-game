from dataclasses import dataclass
from typing import Any

import config


@dataclass
class GameState:
    running: bool = True
    screen: str = "menu"
    menu_tab: str = "decks"
    selected_deck_key: str = "local"
    menu_error: str | None = None
    puzzle_solved: bool = False
    dragged_tile: Any = None
    start_pos: tuple[int, int] | None = None
    offset_x: int = 0
    offset_y: int = 0
    anim_timer_ms: float = 0.0
    current_frame: int = 0
    deck: Any = None
    volume: float = config.INITIAL_VOLUME
    is_dragging_seek: bool = False
    seek_preview_frame: int | None = None
    audio_offset_ms: float = 0.0
    wants_next_puzzle: bool = False
    waiting_for_media: bool = False
    is_panning: bool = False
    pan_mouse_x: int = 0
    pan_mouse_y: int = 0
    last_middle_click_time: int = 0

    def reset_for_new_puzzle(self):
        self.puzzle_solved = False
        self.dragged_tile = None
        self.start_pos = None
        self.offset_x = 0
        self.offset_y = 0
        self.anim_timer_ms = 0.0
        self.current_frame = 0
        self.is_dragging_seek = False
        self.seek_preview_frame = None
        self.audio_offset_ms = 0.0
        self.wants_next_puzzle = False
        self.waiting_for_media = False
        self.is_panning = False
        self.pan_mouse_x = 0
        self.pan_mouse_y = 0
        self.last_middle_click_time = 0
