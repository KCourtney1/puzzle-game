import config
import pygame
from pathlib import Path
from PIL import Image
import cv2
import tempfile
import os
import shutil
import random

def clamp(val, low, high):
    return max(low, min(val, high))

def get_scaled_size(width, height):
    """Scale relative to the MAX_WINDOW_SIZE (the puzzle area), not the whole screen while maintaining aspect ratio"""
    scale = min(config.MAX_WINDOW_SIZE / width, config.MAX_WINDOW_SIZE / height, 1.0)
    return int(width * scale), int(height * scale)

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

def load_media(deck):
    path = deck.next_image()
    ext = path.suffix.lower()

    if ext == '.gif':
        return load_gif(path)
    elif ext == '.mp4':
        return load_video(path)
    return load_img(path)

def load_img(path):
    img = pygame.image.load(path)

    new_w, new_h = get_scaled_size(img.get_width(), img.get_height())
    if (new_w, new_h) != img.get_size():
        img = pygame.transform.smoothscale(img, (new_w, new_h))
    return [img], [100], None, path

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
    return frames, durations, None, path

def load_video(path):
    frames = []
    durations = []
    audio_path = None

    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1000/fps if fps > 0 else 33

    total_frames_available = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames_available <= 0: 
        total_frames_available = config.MAX_VIDEO_FRAMES

    frames_to_extract = min(total_frames_available, config.MAX_VIDEO_FRAMES)
    video_length_seconds = frames_to_extract / fps if fps > 0 else 5.0
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

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    new_w, new_h = get_scaled_size(orig_w, orig_h)
    while True:
        ret, frame = cap.read()
        if not ret:
            break #video over

        if (new_w, new_h) != (orig_w, orig_h):
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pygame_image = pygame.image.frombytes(
            frame_rgb.tobytes(),
            (new_w, new_h),
            "RGB"
        )
        
        frames.append(pygame_image)
        durations.append(frame_duration)
        if len(frames) >= config.MAX_VIDEO_FRAMES:
            break
    cap.release()

    if not frames:
        surf = pygame.Surface((400, 400))
        surf.fill((255, 0, 0)) # Red square fallback
        return [surf], [100], None, path
    
    return frames, durations, audio_path, path

def save_to_local(source_path):
    if not source_path:
        return False
    
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