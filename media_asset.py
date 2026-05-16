import bisect
from collections import OrderedDict
from dataclasses import dataclass
import threading

import cv2
import pygame

import config


@dataclass
class PreviewSheet:
    surface: pygame.Surface
    frame_indices: list[int]
    frame_rects: dict[int, pygame.Rect]

    @property
    def start_frame(self):
        return self.frame_indices[0] if self.frame_indices else 0

    @property
    def end_frame(self):
        return self.frame_indices[-1] if self.frame_indices else -1

    def covers(self, frame_index):
        return frame_index in self.frame_rects


class BaseMediaAsset:
    def __init__(self, durations, audio_path, source_path, width, height):
        self.durations = [max(1.0, float(duration)) for duration in durations]
        self.audio_path = audio_path
        self.source_path = source_path
        self.width = width
        self.height = height
        self.frame_starts = self._build_frame_starts()
        self.total_animation_ms = max(
            self.frame_starts[-1] + self.durations[-1],
            1.0,
        )

    @property
    def frame_count(self):
        raise NotImplementedError

    @property
    def is_animated(self):
        return self.frame_count > 1

    def get_frame(self, frame_index):
        raise NotImplementedError

    def peek_frame(self, frame_index):
        return self.get_frame(frame_index)

    def peek_preview(self, frame_index):
        return self.peek_frame(frame_index)

    def get_frame_duration_ms(self, frame_index):
        clamped_index = max(0, min(frame_index, self.frame_count - 1))
        return self.durations[clamped_index]

    def frame_index_for_time(self, elapsed_ms):
        wrapped_ms = elapsed_ms % self.total_animation_ms
        return max(0, bisect.bisect_right(self.frame_starts, wrapped_ms) - 1)

    def frame_start_ms(self, frame_index):
        clamped_index = max(0, min(frame_index, self.frame_count - 1))
        return self.frame_starts[clamped_index]

    def blit_region(self, screen, frame_index, source_rect, dest):
        screen.blit(self.get_frame(frame_index), dest, source_rect)

    def request_prefetch(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        """Hint that this frame and nearby frames will be needed soon."""

    def request_preview_sheet(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        self.request_prefetch(frame_index, backward_radius, forward_radius, immediate_on_jump)

    def prepare_frame(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        self.request_prefetch(frame_index, backward_radius, forward_radius, immediate_on_jump)
        return self.get_frame(frame_index)

    def close(self):
        """Release any external resources. Eager assets have nothing to do."""

    def _build_frame_starts(self):
        frame_starts = []
        elapsed_ms = 0.0
        for duration in self.durations:
            frame_starts.append(elapsed_ms)
            elapsed_ms += duration
        return frame_starts


class EagerMediaAsset(BaseMediaAsset):
    def __init__(self, frames, durations, audio_path, source_path):
        if not frames:
            raise ValueError("EagerMediaAsset requires at least one frame.")

        self.frames = frames
        width, height = frames[0].get_size()
        super().__init__(durations, audio_path, source_path, width, height)

    @property
    def frame_count(self):
        return len(self.frames)

    def get_frame(self, frame_index):
        return self.frames[frame_index % len(self.frames)]


class StreamingVideoAsset(BaseMediaAsset):
    def __init__(
        self,
        video_path,
        audio_path,
        width,
        height,
        frame_count,
        frame_duration_ms,
        native_width,
        native_height,
        cache_size=None,
    ):
        self.video_path = video_path
        self._frame_count = max(1, int(frame_count))
        self._frame_duration_ms = max(1.0, float(frame_duration_ms))
        self._native_width = max(1, int(native_width))
        self._native_height = max(1, int(native_height))
        self._target_size = (max(1, int(width)), max(1, int(height)))
        self._cache_size = max(1, cache_size or config.VIDEO_STREAM_CACHE_FRAMES)
        self._capture = None
        self._cache = OrderedDict()
        self._last_decoded_index = -1
        self._cache_lock = threading.Lock()
        self._prefetch_capture = None
        self._prefetch_last_index = -1
        self._prefetch_target = 0
        self._prefetch_backward_radius = 0
        self._prefetch_forward_radius = 0
        self._prefetch_window_start = 0
        self._prefetch_window_end = -1
        self._prefetch_generation = 0
        self._preview_capture = None
        self._preview_last_index = -1
        self._preview_last_warm_index = -1
        self._preview_priority_frame = -1  # single frame to decode first before building sheet
        self._preview_thumb_size = (
            max(1, config.SEEK_PREVIEW_WIDTH - 8),
            max(1, config.SEEK_PREVIEW_HEIGHT - 8),
        )
        self._preview_cache = OrderedDict()
        self._preview_thumb_cache = OrderedDict()
        self._preview_cache_lock = threading.Lock()
        self._preview_target = 0
        self._preview_backward_radius = 0
        self._preview_forward_radius = 0
        self._preview_window_start = 0
        self._preview_window_end = -1
        self._preview_generation = 0
        self._stop_event = threading.Event()
        self._prefetch_cv = threading.Condition()
        self._preview_cv = threading.Condition()

        super().__init__(
            [self._frame_duration_ms] * self._frame_count,
            audio_path,
            video_path,
            self._target_size[0],
            self._target_size[1],
        )

        self._prefetch_thread = threading.Thread(
            target=self._prefetch_loop,
            daemon=True,
            name=f"stream-prefetch-{self.video_path.name}",
        )
        self._prefetch_thread.start()
        self._preview_thread = threading.Thread(
            target=self._preview_loop,
            daemon=True,
            name=f"stream-preview-{self.video_path.name}",
        )
        self._preview_thread.start()

    @property
    def frame_count(self):
        return self._frame_count

    def get_frame(self, frame_index):
        clamped_index = max(0, min(int(frame_index), self._frame_count - 1))
        with self._cache_lock:
            cached = self._cache.get(clamped_index)
            if cached is not None:
                self._cache.move_to_end(clamped_index)
                return cached
            # Cache miss — return nearest available frame to avoid blocking the main thread.
            # The prefetch thread will fill the real frame shortly.
            if self._cache:
                best = min(self._cache.keys(), key=lambda k: abs(k - clamped_index))
                return self._cache[best]

        # Absolute cache miss (empty cache) — must decode synchronously.
        frame = self._decode_frame(clamped_index)
        with self._cache_lock:
            self._cache[clamped_index] = frame
            self._cache.move_to_end(clamped_index)
            self._trim_cache_locked()
        return frame

    def request_prefetch(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        clamped_index = max(0, min(int(frame_index), self._frame_count - 1))
        requested_backward = max(0, int(backward_radius))
        requested_forward = requested_backward if forward_radius is None else max(0, int(forward_radius))
        with self._cache_lock:
            target_cached = clamped_index in self._cache

        should_warm_sync = False
        with self._prefetch_cv:
            in_window = self._prefetch_window_start <= clamped_index <= self._prefetch_window_end
            if (
                in_window
                and target_cached
                and requested_backward <= self._prefetch_backward_radius
                and requested_forward <= self._prefetch_forward_radius
            ):
                return

            if (
                in_window
                and requested_backward <= self._prefetch_backward_radius
                and requested_forward <= self._prefetch_forward_radius
            ):
                window_start = self._prefetch_window_start
                window_end = self._prefetch_window_end
                requested_backward = self._prefetch_backward_radius
                requested_forward = self._prefetch_forward_radius
            else:
                window_start = max(0, clamped_index - requested_backward)
                window_end = min(self._frame_count - 1, clamped_index + requested_forward)
                should_warm_sync = immediate_on_jump and not in_window and not target_cached

            self._prefetch_target = clamped_index
            self._prefetch_backward_radius = requested_backward
            self._prefetch_forward_radius = requested_forward
            self._prefetch_window_start = window_start
            self._prefetch_window_end = window_end
            self._prefetch_generation += 1
            self._prefetch_cv.notify()

        if should_warm_sync:
            self._warm_frame_sync(clamped_index)

    def request_preview_sheet(self, frame_index, backward_radius=0, forward_radius=None, immediate_on_jump=False):
        clamped_index = max(0, min(int(frame_index), self._frame_count - 1))
        requested_backward = max(0, int(backward_radius))
        requested_forward = requested_backward if forward_radius is None else max(0, int(forward_radius))
        window_start, window_end = self._build_preview_window(
            clamped_index,
            requested_backward,
            requested_forward,
        )

        with self._preview_cache_lock:
            cached_sheet = self._find_preview_sheet_locked(clamped_index)
            thumb_cached = clamped_index in self._preview_thumb_cache
            if cached_sheet is not None:
                return

        should_set_priority = False
        with self._preview_cv:
            current_window_covers_target = self._preview_window_start <= clamped_index <= self._preview_window_end
            current_window_covers_request = (
                current_window_covers_target
                and window_start >= self._preview_window_start
                and window_end <= self._preview_window_end
            )
            if not current_window_covers_request:
                self._preview_target = clamped_index
                self._preview_backward_radius = requested_backward
                self._preview_forward_radius = requested_forward
                self._preview_window_start = window_start
                self._preview_window_end = window_end
                self._preview_generation += 1

            # Always update priority frame so the thread decodes it first
            if immediate_on_jump and clamped_index != self._preview_last_warm_index:
                self._preview_last_warm_index = clamped_index
                self._preview_priority_frame = clamped_index
                should_set_priority = True

            self._preview_cv.notify()

    def peek_frame(self, frame_index):
        clamped_index = max(0, min(int(frame_index), self._frame_count - 1))
        with self._cache_lock:
            cached = self._cache.get(clamped_index)
            if cached is not None:
                self._cache.move_to_end(clamped_index)
            return cached

    def peek_preview(self, frame_index):
        clamped_index = max(0, min(int(frame_index), self._frame_count - 1))
        with self._preview_cache_lock:
            sheet_key, sheet = self._find_preview_sheet_entry_locked(clamped_index)
            if sheet is not None:
                self._preview_cache.move_to_end(sheet_key)
                thumb_rect = sheet.frame_rects.get(clamped_index)
                if thumb_rect is not None:
                    return sheet.surface.subsurface(thumb_rect)

            cached_thumb = self._preview_thumb_cache.get(clamped_index)
            if cached_thumb is not None:
                self._preview_thumb_cache.move_to_end(clamped_index)
            return cached_thumb

    def close(self):
        self._stop_event.set()
        with self._prefetch_cv:
            self._prefetch_cv.notify_all()
        with self._preview_cv:
            self._preview_cv.notify_all()
        if hasattr(self, "_prefetch_thread") and self._prefetch_thread.is_alive():
            self._prefetch_thread.join(timeout=1.0)
        if hasattr(self, "_preview_thread") and self._preview_thread.is_alive():
            self._preview_thread.join(timeout=1.0)
        if self._capture is not None:
            self._capture.release()
            self._capture = None
        if self._prefetch_capture is not None:
            self._prefetch_capture.release()
            self._prefetch_capture = None
        if self._preview_capture is not None:
            self._preview_capture.release()
            self._preview_capture = None
        with self._cache_lock:
            self._cache.clear()
        with self._preview_cache_lock:
            self._preview_cache.clear()
            self._preview_thumb_cache.clear()
        self._last_decoded_index = -1
        self._prefetch_last_index = -1
        self._preview_last_index = -1

    def _warm_frame_sync(self, frame_index):
        clamped_index = max(0, min(int(frame_index), self._frame_count - 1))
        with self._cache_lock:
            cached = self._cache.get(clamped_index)
            if cached is not None:
                self._cache.move_to_end(clamped_index)
                return cached

        frame = self._decode_frame(clamped_index)
        with self._cache_lock:
            self._cache[clamped_index] = frame
            self._cache.move_to_end(clamped_index)
            self._trim_cache_locked()
        return frame

    def _decode_frame(self, frame_index):
        capture = self._ensure_capture()
        frame, resolved_index = self._read_frame(capture, self._last_decoded_index, frame_index)
        if frame is None:
            return self._empty_surface()
        self._last_decoded_index = resolved_index
        return self._frame_to_surface(frame)

    def _ensure_capture(self):
        if self._capture is None:
            self._capture = cv2.VideoCapture(str(self.video_path))
        return self._capture

    def _ensure_prefetch_capture(self):
        if self._prefetch_capture is None:
            self._prefetch_capture = cv2.VideoCapture(str(self.video_path))
        return self._prefetch_capture

    def _ensure_preview_capture(self):
        if self._preview_capture is None:
            self._preview_capture = cv2.VideoCapture(str(self.video_path))
        return self._preview_capture

    def _prefetch_loop(self):
        active_generation = -1

        while not self._stop_event.is_set():
            with self._prefetch_cv:
                if active_generation == self._prefetch_generation:
                    self._prefetch_cv.wait(timeout=0.05)
                    if self._stop_event.is_set():
                        break
                target_index = self._prefetch_target
                window_start = self._prefetch_window_start
                window_end = self._prefetch_window_end
                generation = self._prefetch_generation

            active_generation = generation
            for frame_index in self._build_prefetch_plan(target_index, window_start, window_end):
                if self._stop_event.is_set():
                    return

                with self._prefetch_cv:
                    if active_generation != self._prefetch_generation:
                        break

                with self._cache_lock:
                    if frame_index in self._cache:
                        self._cache.move_to_end(frame_index)
                        continue

                capture = self._ensure_prefetch_capture()
                frame, resolved_index = self._read_frame(capture, self._prefetch_last_index, frame_index)
                self._prefetch_last_index = resolved_index
                surface = self._empty_surface() if frame is None else self._frame_to_surface(frame)
                with self._cache_lock:
                    self._cache[frame_index] = surface
                    self._cache.move_to_end(frame_index)
                    self._trim_cache_locked()

    def _preview_loop(self):
        active_generation = -1

        while not self._stop_event.is_set():
            with self._preview_cv:
                if active_generation == self._preview_generation and self._preview_priority_frame == -1:
                    self._preview_cv.wait(timeout=0.05)
                    if self._stop_event.is_set():
                        break
                target_index = self._preview_target
                window_start = self._preview_window_start
                window_end = self._preview_window_end
                generation = self._preview_generation
                priority_frame = self._preview_priority_frame
                self._preview_priority_frame = -1  # consume it

            active_generation = generation

            # --- Priority path: decode the single hovered frame immediately ---
            if priority_frame >= 0:
                with self._preview_cache_lock:
                    already_have = (
                        self._find_preview_sheet_locked(priority_frame) is not None
                        or priority_frame in self._preview_thumb_cache
                    )
                if not already_have:
                    capture = self._ensure_preview_capture()
                    frame, last_index = self._read_frame(capture, self._preview_last_index, priority_frame)
                    self._preview_last_index = last_index
                    surf = self._empty_preview_surface() if frame is None else self._frame_to_preview_surface(frame)
                    with self._preview_cache_lock:
                        self._preview_thumb_cache[priority_frame] = surf
                        self._preview_thumb_cache.move_to_end(priority_frame)
                        self._trim_preview_thumb_cache_locked()

            # --- Full sheet path ---
            frame_indices = self._build_preview_sheet_indices(target_index, window_start, window_end)
            if not frame_indices:
                continue

            with self._preview_cache_lock:
                cached_sheet = self._find_preview_sheet_locked(target_index)
                if cached_sheet is not None:
                    continue

            # Build the sheet one thumb at a time so we can bail on generation change
            capture = self._ensure_preview_capture()
            cols = max(1, config.SEEK_PREVIEW_SHEET_COLUMNS)
            thumb_width, thumb_height = self._preview_thumb_size
            rows = (len(frame_indices) + cols - 1) // cols
            sheet_surface = pygame.Surface((cols * thumb_width, rows * thumb_height))
            sheet_surface.fill(config.MENU_CARD_COLOR)
            frame_rects = {}

            aborted = False
            for position, frame_index in enumerate(frame_indices):
                if self._stop_event.is_set():
                    return
                with self._preview_cv:
                    if self._preview_generation != active_generation:
                        aborted = True
                        break

                with self._preview_cache_lock:
                    cached_thumb = self._preview_thumb_cache.get(frame_index)
                if cached_thumb is not None:
                    preview_surface = cached_thumb
                else:
                    raw, self._preview_last_index = self._read_frame(capture, self._preview_last_index, frame_index)
                    preview_surface = self._empty_preview_surface() if raw is None else self._frame_to_preview_surface(raw)

                col = position % cols
                row = position // cols
                thumb_rect = pygame.Rect(col * thumb_width, row * thumb_height, thumb_width, thumb_height)
                sheet_surface.blit(preview_surface, thumb_rect.topleft)
                frame_rects[frame_index] = thumb_rect

            if aborted or not frame_rects:
                continue

            preview_sheet = PreviewSheet(sheet_surface, frame_indices, frame_rects)
            with self._preview_cache_lock:
                cache_key = (preview_sheet.start_frame, preview_sheet.end_frame)
                self._preview_cache[cache_key] = preview_sheet
                self._preview_cache.move_to_end(cache_key)
                for frame_index in frame_indices:
                    self._preview_thumb_cache.pop(frame_index, None)
                self._trim_preview_cache_locked()

    def _read_frame(self, capture, last_index, frame_index):
        sequential = last_index != -1 and frame_index == last_index + 1
        wrapped = last_index == self._frame_count - 1 and frame_index == 0

        if sequential:
            ret, frame = capture.read()
        elif wrapped:
            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = capture.read()
        else:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = capture.read()

        if not ret:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = capture.read()

        if not ret and frame_index != 0:
            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = capture.read()
            frame_index = 0

        if not ret:
            return None, 0

        return frame, frame_index

    def _frame_to_surface(self, frame):
        if self._target_size != (self._native_width, self._native_height):
            frame = cv2.resize(frame, self._target_size, interpolation=cv2.INTER_AREA)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return pygame.image.frombytes(
            frame_rgb.tobytes(),
            self._target_size,
            "RGB"
        ).convert()

    def _empty_surface(self):
        surface = pygame.Surface(self._target_size)
        surface.fill((255, 0, 0))
        return surface

    def _frame_to_preview_surface(self, frame):
        thumb_width, thumb_height = self._preview_thumb_size
        frame_height, frame_width = frame.shape[:2]
        scale = min(thumb_width / frame_width, thumb_height / frame_height)
        scaled_width = max(1, round(frame_width * scale))
        scaled_height = max(1, round(frame_height * scale))
        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        resized_frame = cv2.resize(frame, (scaled_width, scaled_height), interpolation=interpolation)
        frame_rgb = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        preview_surface = pygame.Surface(self._preview_thumb_size)
        preview_surface.fill(config.MENU_CARD_COLOR)
        scaled_surface = pygame.image.frombytes(
            frame_rgb.tobytes(),
            (scaled_width, scaled_height),
            "RGB",
        ).convert()
        offset_x = (thumb_width - scaled_width) // 2
        offset_y = (thumb_height - scaled_height) // 2
        preview_surface.blit(scaled_surface, (offset_x, offset_y))
        return preview_surface.convert()

    def _empty_preview_surface(self):
        preview_surface = pygame.Surface(self._preview_thumb_size)
        preview_surface.fill(config.MENU_CARD_COLOR)
        return preview_surface

    def _build_prefetch_plan(self, center_index, window_start, window_end):
        if window_end < window_start:
            return []

        plan = []
        if window_start <= center_index <= window_end:
            plan.append(center_index)

        for forward_index in range(center_index + 1, window_end + 1):
            plan.append(forward_index)

        for backward_index in range(center_index - 1, window_start - 1, -1):
            plan.append(backward_index)

        return plan

    def _trim_cache_locked(self):
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def _build_preview_window(self, center_index, backward_radius, forward_radius):
        desired_count = min(
            self._frame_count,
            max(1, config.SEEK_PREVIEW_SHEET_THUMBS),
            max(1, backward_radius + forward_radius + 1),
        )
        window_start = max(0, center_index - backward_radius)
        window_end = min(self._frame_count - 1, center_index + forward_radius)

        current_count = window_end - window_start + 1
        if current_count < desired_count:
            missing = desired_count - current_count
            extend_forward = min(self._frame_count - 1 - window_end, missing)
            window_end += extend_forward
            missing -= extend_forward
            if missing > 0:
                window_start = max(0, window_start - missing)

        return window_start, window_end

    def _build_preview_sheet_indices(self, center_index, window_start, window_end):
        if window_end < window_start:
            return []

        frame_indices = list(range(window_start, window_end + 1))
        max_count = max(1, config.SEEK_PREVIEW_SHEET_THUMBS)
        return frame_indices[:max_count]

    def _find_preview_sheet_locked(self, frame_index, window_start=None, window_end=None):
        _, sheet = self._find_preview_sheet_entry_locked(frame_index, window_start, window_end)
        return sheet

    def _find_preview_sheet_entry_locked(self, frame_index, window_start=None, window_end=None):
        for cache_key, preview_sheet in reversed(list(self._preview_cache.items())):
            if not preview_sheet.covers(frame_index):
                continue
            if window_start is not None and window_end is not None:
                if preview_sheet.start_frame > window_start or preview_sheet.end_frame < window_end:
                    continue
            return cache_key, preview_sheet
        return None, None

    def _trim_preview_cache_locked(self):
        while len(self._preview_cache) > max(1, config.SEEK_PREVIEW_CACHE_SHEETS):
            self._preview_cache.popitem(last=False)

    def _trim_preview_thumb_cache_locked(self):
        while len(self._preview_thumb_cache) > max(8, config.SEEK_PREVIEW_SHEET_THUMBS):
            self._preview_thumb_cache.popitem(last=False)
