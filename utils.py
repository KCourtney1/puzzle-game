from config import *
import pygame
import random
import sys
from pathlib import Path

def clamp(val, low, high):
    return max(low, min(val, high))

def load_image(deck):
    image_path = deck.next_image()
    img = pygame.image.load(image_path)
    return img

def fit_image_to_screen(img):
    img_width, img_height = img.get_size()

    scale = min(MAX_WINDOW_SIZE / img_width, MAX_WINDOW_SIZE / img_height, 1.0)
    new_width = int(img_width * scale)
    new_height = int(img_height * scale)
    return pygame.transform.smoothscale(img, (new_width, new_height))

def create_button(width, height):
    button_width = 250
    button_height = 60
    return pygame.Rect(
        (width // 2) - (button_width // 2),
        height - button_height - 10,
        button_width,
        button_height
    )