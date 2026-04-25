import utils
import config
import pygame

class Button:
    def __init__(self, x, y, width, height, text, font, text_color, base_color, press_color, border_color, border_radius=8, cooldown_ms=100):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.text_color = text_color
        self.base_color = base_color
        self.press_color = press_color
        self.border_color = border_color
        self.border_radius = border_radius

        self.is_pressed = False
        self.is_hovered = False

        self.cooldown_ms = cooldown_ms
        self.last_click_time = 0
    
    def handle_event(self, event):
        """Processes events and returns True if the button was clicked."""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False
            
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                current_time = pygame.time.get_ticks()
                if current_time - self.last_click_time >= self.cooldown_ms:
                    self.is_pressed = True
                    self.is_hovered = True 
                    self.last_click_time = current_time
                    return True
                else:
                    return False # Spam detected, ignore the click
            
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_pressed = False
            
        return False
    
    def draw(self, screen):
        """Renders the button with appropriate colors based on its state."""
        current_color = self.press_color if self.is_pressed else self.base_color
        pygame.draw.rect(screen, current_color, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(screen, self.border_color, self.rect, 3, border_radius=self.border_radius)

        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
class VolumeSlider:
    def __init__(self, x, y, width, height, initial_volume, on_change_callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.volume = initial_volume
        self.is_dragging = False
        self.on_change_callback = on_change_callback
        self.font = pygame.font.SysFont(None, 28)
    
    def handle_event(self, event):
        """Processes events and returns True if the slider interacted with it."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hitbox = self.rect.inflate(0, config.SLIDER_KNOB_RADIUS * 2)
            if hitbox.collidepoint(event.pos):
                self.is_dragging = True
                self._update_volume(event.pos[0])
                return True
                
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                self._update_volume(event.pos[0])
                return True # Consume the drag event
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                return True
                
        return False
    
    def _update_volume(self, mouse_x):
        clamped_x = utils.clamp(mouse_x, self.rect.left, self.rect.right)
        self.volume = (clamped_x - self.rect.left) / self.rect.width
        if self.on_change_callback:
            self.on_change_callback(self.volume)

    def draw(self, screen):
        # Track
        pygame.draw.rect(screen, config.SLIDER_BG_COLOR, self.rect, border_radius=5)
        
        # Fill
        fill_width = int(self.rect.width * self.volume)
        fill_rect = pygame.Rect(self.rect.left, self.rect.top, fill_width, self.rect.height)
        pygame.draw.rect(screen, config.SLIDER_FILL_COLOR, fill_rect, border_radius=5)
        
        # Knob
        knob_x = self.rect.left + fill_width
        knob_y = self.rect.centery
        pygame.draw.circle(screen, config.SLIDER_KNOB_COLOR, (knob_x, knob_y), config.SLIDER_KNOB_RADIUS)

        # Text
        vol_text = self.font.render(f"Volume: {int(self.volume * 100)}%", True, config.TEXT_COLOR)
        screen.blit(vol_text, (self.rect.left, self.rect.top - 30))

def draw_loading_overlay(screen, font):
    """Draws an unobtrusive floating banner at the bottom of the puzzle area."""
    text_surf = font.render("Downloading Next Media...", True, config.TEXT_COLOR)
    
    padding_x = 40
    padding_y = 20
    box_width = text_surf.get_width() + padding_x
    box_height = text_surf.get_height() + padding_y
    
    box_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
    pygame.draw.rect(box_surf, (30, 30, 35, 200), box_surf.get_rect(), border_radius=15)
    pygame.draw.rect(box_surf, config.SKIP_BUTTON_BORDER, box_surf.get_rect(), 2, border_radius=15)
    
    #centered at bottom of puzzle area
    center_x = config.SIDEBAR_WIDTH + (config.MAX_WINDOW_SIZE // 2)
    center_y = config.MAX_WINDOW_SIZE - 60
    
    box_rect = box_surf.get_rect(center=(center_x, center_y))
    text_rect = text_surf.get_rect(center=box_rect.center)
    
    screen.blit(box_surf, box_rect)
    screen.blit(text_surf, text_rect)