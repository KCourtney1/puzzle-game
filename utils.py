from config import *
import pygame
from pathlib import Path
from PIL import Image
import cv2
import tempfile
import os
import random

def clamp(val, low, high):
    return max(low, min(val, high))

def cleanup_audio(audio_path):
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()

    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except PermissionError:
            pass

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
    return [img], [100], None

def load_gif(path):
    frames = []
    durations = []

    pil_img = Image.open(path)
    try:
        while True:
            duration = pil_img.info.get("duration", 100)
            frame_rgba = pil_img.convert("RGBA")
            pygame_image = pygame.image.fromstring(
                frame_rgba.tobytes(),
                frame_rgba.size,
                "RGBA"
            )

            frames.append(pygame_image)
            durations.append(duration)

            pil_img.seek(pil_img.tell() + 1)
    except EOFError:
        pass
    return frames, durations, None

def load_video(path):
    frames = []
    durations = []
    audio_path = None

    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1000/fps if fps > 0 else 33

    total_frames_available = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames_available <= 0: 
        total_frames_available = MAX_VIDEO_FRAMES

    frames_to_extract = min(total_frames_available, MAX_VIDEO_FRAMES)
    video_length_seconds = frames_to_extract / fps if fps > 0 else 5.0
    try:
        from moviepy import VideoFileClip

        clip = VideoFileClip(str(path))
        if clip.duration > video_length_seconds:
            clip = clip.subclipped(0, video_length_seconds)

        if clip.audio is not None:
            game_dir = Path(__file__).parent.resolve()
            temp_dir = game_dir / "temp"
            temp_dir.mkdir(exist_ok=True)

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

    while True:
        ret, frame = cap.read()

        if not ret:
            break #video over

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = frame_rgb.shape
        pygame_image = pygame.image.frombytes(
            frame_rgb.tobytes(),
            (width, height),
            "RGB"
        )
        
        frames.append(pygame_image)
        durations.append(frame_duration)
        if len(frames) >= MAX_VIDEO_FRAMES:
            break
    cap.release()

    if not frames:
        surf = pygame.Surface((400, 400))
        surf.fill((255, 0, 0)) # Red square fallback
        return [surf], [100]
    
    return frames, durations,audio_path

def fit_image_to_screen(frames):
    img_width, img_height = frames[0].get_size()

    scale = min(MAX_WINDOW_SIZE / img_width, MAX_WINDOW_SIZE / img_height, 1.0)
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)

    return [
        pygame.transform.smoothscale(frame,(new_width, new_height))
        for frame in frames
    ]

def create_button(width, height):
    button_width = 250
    button_height = 60
    return pygame.Rect(
        (width // 2) - (button_width // 2),
        height - button_height - 10,
        button_width,
        button_height
    )