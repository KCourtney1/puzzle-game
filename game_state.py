from dataclasses import dataclass
from typing import Any

import config


@dataclass
class GameState:
    running: bool = True
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
    audio_offset_ms: float = 0.0
    wants_next_puzzle: bool = False
    waiting_for_media: bool = False

    def reset_for_new_puzzle(self):
        self.puzzle_solved = False
        self.dragged_tile = None
        self.start_pos = None
        self.offset_x = 0
        self.offset_y = 0
        self.anim_timer_ms = 0.0
        self.current_frame = 0
        self.is_dragging_seek = False
        self.audio_offset_ms = 0.0
        self.wants_next_puzzle = False
        self.waiting_for_media = False
