from dataclasses import dataclass
import queue
import threading

import utils


@dataclass(frozen=True)
class MediaRequest:
    generation: int
    request_id: int
    deck: object


@dataclass(frozen=True)
class MediaResult:
    generation: int
    request_id: int
    media_data: tuple | None
    error: str | None = None
    retryable: bool = False


def _preload_worker(job_q, result_q):
    while True:
        request = job_q.get()
        if request is None:
            break

        try:
            media_data = utils.load_media(request.deck)
            if media_data is None:
                raise ValueError("Deck returned no media.")
            result_q.put(MediaResult(request.generation, request.request_id, media_data))
        except utils.MediaLoadError as exc:
            result_q.put(
                MediaResult(
                    request.generation,
                    request.request_id,
                    None,
                    str(exc),
                    exc.retryable,
                )
            )
        except Exception as exc:
            result_q.put(
                MediaResult(
                    request.generation,
                    request.request_id,
                    None,
                    f"Background preload failed ({exc}).",
                )
            )


class MediaController:
    def __init__(self, max_retry_attempts=2):
        self.deck = None
        self.generation = 0
        self.ready_media = None
        self.pending_request_id = None
        self.last_error = None
        self.retry_attempts = 0
        self.max_retry_attempts = max_retry_attempts
        self._next_request_id = 1
        self._job_q = queue.Queue()
        self._result_q = queue.Queue()
        self._worker = threading.Thread(
            target=_preload_worker,
            args=(self._job_q, self._result_q),
            daemon=True,
        )

    def start(self):
        self._worker.start()

    def stop(self):
        self._job_q.put(None)
        self._worker.join(timeout=1.0)

    def replace_deck(self, deck):
        self.deck = deck
        self.generation += 1
        self.ready_media = None
        self.pending_request_id = None
        self.last_error = None
        self.retry_attempts = 0
        self._drain_queue(self._job_q)
        self._drain_queue(self._result_q)

    def ensure_prefetch(self):
        if (
            self.deck is None
            or self.ready_media is not None
            or self.pending_request_id is not None
            or self.last_error is not None
        ):
            return False

        request_id = self._next_request_id
        self._next_request_id += 1
        self.pending_request_id = request_id
        self._job_q.put(MediaRequest(self.generation, request_id, self.deck))
        return True

    def pump(self):
        while True:
            try:
                result = self._result_q.get_nowait()
            except queue.Empty:
                break

            if result.generation != self.generation:
                continue

            if result.request_id != self.pending_request_id:
                continue

            self.pending_request_id = None
            if result.media_data is None:
                print(result.error)
                if result.retryable and self.retry_attempts < self.max_retry_attempts:
                    self.retry_attempts += 1
                    self.ensure_prefetch()
                else:
                    self.last_error = result.error
                continue

            self.last_error = None
            self.retry_attempts = 0
            self.ready_media = result.media_data

    def has_ready_media(self):
        return self.ready_media is not None

    def has_error(self):
        return self.last_error is not None

    def clear_error(self):
        self.last_error = None
        self.retry_attempts = 0

    def consume_ready_media(self):
        media_data = self.ready_media
        self.ready_media = None
        return media_data

    @staticmethod
    def _drain_queue(target_queue):
        try:
            while True:
                target_queue.get_nowait()
        except queue.Empty:
            return
