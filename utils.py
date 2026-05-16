import config
import pygame
from pathlib import Path
from PIL import Image
import cv2
import tempfile
import os
import shutil
import random

from media_asset import EagerMediaAsset, StreamingVideoAsset


class MediaLoadError(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


def clamp(val, low, high):
    return max(low, min(val, high))

def get_scaled_size(width, height):
    """Scale to the usable puzzle canvas while maintaining aspect ratio."""
    scale = min(config.PUZZLE_AREA_WIDTH / width, config.PUZZLE_AREA_HEIGHT / height)
    return max(1, round(width * scale)), max(1, round(height * scale))

def create_button(pos_x, pos_y, button_width, button_height):
    return pygame.Rect(
        pos_x,
        pos_y,
        button_width,
        button_height
    )

def clear_temp_folders(exclude_paths=None):
    """Removes all files from the temp directories except the currently active audio."""
    game_dir = Path(__file__).parent.resolve()
    temp_root = game_dir / "temp"
    
    if not temp_root.exists():
        return

    target_excludes = []
    if exclude_paths:
        for p in exclude_paths:
            if p:
                target_excludes.append(Path(p).resolve())
    
    for folder in temp_root.iterdir():
        if folder.is_dir():
            for file in folder.iterdir():
                if file.resolve() in target_excludes:
                    continue
                try:
                    file.unlink()
                except Exception:
                    pass
            
            # try:
            #     if not any(folder.iterdir()):
            #         folder.rmdir()
            # except Exception as e:
            #     print(f"Folder cleanup failed: {e}")

def cleanup_audio(audio_path):
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()

    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except PermissionError:
            print("Audio still locked, skipping delete.")

def load_media(deck, status_callback=None):
    if status_callback:
        status_callback("Downloading Next Media...")

    path = deck.next_image()
    if path is None:
        return None
    if status_callback:
        status_callback("Loading Next Media...")
        
    ext = path.suffix.lower()
    if ext == '.gif':
        return load_gif(path)
    elif ext == '.webp':
        return load_webp(path)
    elif ext == '.mp4':
        return load_video(path)
    return load_img(path)

def load_img(path):
    img = pygame.image.load(path)

    new_w, new_h = get_scaled_size(img.get_width(), img.get_height())
    if (new_w, new_h) != img.get_size():
        img = pygame.transform.smoothscale(img, (new_w, new_h))
    return EagerMediaAsset([img], [100], None, path)

def load_gif(path):
    frames = []
    durations = []
    pil_img = Image.open(path)

    new_w, new_h = get_scaled_size(pil_img.width, pil_img.height)
    try:
        while True:
            duration = pil_img.info.get("duration", 100)
            frame_rgba = pil_img.convert("RGBA")
            pygame_image = pygame.image.fromstring(
                frame_rgba.tobytes(),
                frame_rgba.size,
                "RGBA"
            )

            if (new_w, new_h) != pygame_image.get_size():
                pygame_image = pygame.transform.smoothscale(pygame_image, (new_w, new_h))

            frames.append(pygame_image)
            durations.append(duration)
            pil_img.seek(pil_img.tell() + 1)
    except EOFError:
        pass
    return EagerMediaAsset(frames, durations, None, path)

def _pil_frame_to_surface(frame_rgba, target_size):
    pygame_image = pygame.image.fromstring(
        frame_rgba.tobytes(),
        frame_rgba.size,
        "RGBA"
    )

    if target_size != pygame_image.get_size():
        pygame_image = pygame.transform.smoothscale(pygame_image, target_size)

    return pygame_image

def load_webp(path):
    frames = []
    durations = []
    pil_img = Image.open(path)

    new_w, new_h = get_scaled_size(pil_img.width, pil_img.height)
    target_size = (new_w, new_h)

    frame_count = getattr(pil_img, "n_frames", 1)
    if frame_count <= 1 and not getattr(pil_img, "is_animated", False):
        frame_rgba = pil_img.convert("RGBA")
        pygame_image = _pil_frame_to_surface(frame_rgba, target_size)
        return EagerMediaAsset([pygame_image], [100], None, path)

    try:
        while True:
            duration = pil_img.info.get("duration", 100)
            frame_rgba = pil_img.convert("RGBA")
            pygame_image = _pil_frame_to_surface(frame_rgba, target_size)
            frames.append(pygame_image)
            durations.append(duration)
            pil_img.seek(pil_img.tell() + 1)
    except EOFError:
        pass

    if not frames:
        frame_rgba = pil_img.convert("RGBA")
        pygame_image = _pil_frame_to_surface(frame_rgba, target_size)
        return EagerMediaAsset([pygame_image], [100], None, path)

    return EagerMediaAsset(frames, durations, None, path)

def load_video(path):
    audio_path = None

    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1000 / fps if fps > 0 else 33

    total_frames_available = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames_available <= 0: 
        total_frames_available = config.MAX_VIDEO_FRAMES

    frames_to_extract = min(total_frames_available, config.MAX_VIDEO_FRAMES)
    video_length_seconds = frames_to_extract / fps if fps > 0 else 5.0

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    new_w, new_h = get_scaled_size(orig_w, orig_h)
    try:
        from moviepy import VideoFileClip

        clip = VideoFileClip(str(path))
        if clip.duration > video_length_seconds:
            clip = clip.subclipped(0, video_length_seconds)

        if clip.audio is not None:
            game_dir = Path(__file__).parent.resolve()
            temp_dir = game_dir / "temp" / "temp_video"
            temp_dir.mkdir(parents=True, exist_ok=True)

            tmp = tempfile.NamedTemporaryFile(
                dir=temp_dir,
                suffix=".wav",
                delete=False
            )
            audio_path = tmp.name
            clip.audio.write_audiofile(
                audio_path,
                logger=None
            )
        clip.close()
    except ImportError:
        print("Install moviepy for audio support")
    except Exception as e:
        print(f"Audio extraction failed: {e}")

    if orig_w <= 0 or orig_h <= 0:
        surf = pygame.Surface((400, 400))
        surf.fill((255, 0, 0))
        return EagerMediaAsset([surf], [100], None, path)

    return StreamingVideoAsset(
        video_path=path,
        audio_path=audio_path,
        width=new_w,
        height=new_h,
        frame_count=frames_to_extract,
        frame_duration_ms=frame_duration,
        native_width=orig_w,
        native_height=orig_h,
    )

def save_to_local(source_path):
    if not source_path:
        return False
    
    if config.CUSTOM_PATH:
        save_dir = Path(config.CUSTOM_PATH).resolve()
    else:
        game_dir = Path(__file__).parent.resolve()
        save_dir = game_dir / "images"
    save_dir.mkdir(parents=True, exist_ok=True)

    if save_dir in source_path.resolve().parents:
        return False
    
    dest_path = save_dir / source_path.name
    try:
        shutil.copy2(source_path, dest_path)
        return True
    except Exception as e:
        print(f"Failed to save file: {e}")
        return False
