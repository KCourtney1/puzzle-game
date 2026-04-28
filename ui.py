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

class TextBox:
    def __init__(self, x, y, width, height, font, text=''):
        self.rect = pygame.Rect(x, y, width, height)
        self.color_active = config.TEXTBOX_COLOR_ACTIVE
        self.color_inactive = config.TEXTBOX_COLOR_INACTIVE
        self.color = self.color_inactive
        self.bg_color = config.TEXTBOX_BG_COLOR
        self.selection_color = config.TEXTBOX_SELECTION_COLOR

        self.font = font
        self.text = text
        self.active = False
        self.title_font = pygame.font.SysFont(None, 24)

        # --- Cursor variables ---
        self.cursor_pos = len(self.text)
        self.selection_start = None

        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_interval = 500
        self.display_offset = 0 # For horizontal scrolling of long text

    def _delete_selection(self):
        """Deletes the currently selected text. Returns True if text was deleted."""
        if self.selection_start is not None and self.selection_start != self.cursor_pos:
            start = min(self.selection_start, self.cursor_pos)
            end = max(self.selection_start, self.cursor_pos)
            self.text = self.text[:start] + self.text[end:]
            self.cursor_pos = start
            self.selection_start = None
            return True
        self.selection_start = None
        return False

    def _get_prev_word_pos(self):
        """Finds the index of the start of the previous word."""
        pos = self.cursor_pos - 1
        while pos >= 0 and self.text[pos] == ' ': pos -= 1 # Skip spaces
        while pos >= 0 and self.text[pos] != ' ': pos -= 1 # Skip characters
        return pos + 1
    
    def _get_next_word_pos(self):
        """Finds the index of the start of the next word."""
        pos = self.cursor_pos
        length = len(self.text)
        while pos < length and self.text[pos] != ' ': pos += 1 # Skip characters
        while pos < length and self.text[pos] == ' ': pos += 1 # Skip spaces
        return pos

    def handle_event(self, event):
        """Processes events. Returns True if Enter was pressed."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.cursor_visible = True
                self.cursor_timer = pygame.time.get_ticks()
                self.selection_start = None # Clear selection on click
                
                # Bonus: Set cursor to where you clicked
                padding = 5
                click_x = event.pos[0] - self.rect.left - padding + self.display_offset
                for i in range(len(self.text) + 1):
                    if self.font.size(self.text[:i])[0] > click_x:
                        self.cursor_pos = max(0, i - 1)
                        break
                else:
                    self.cursor_pos = len(self.text)
            else:
                self.active = False
                self.selection_start = None
            self.color = self.color_active if self.active else self.color_inactive
            
        if event.type == pygame.KEYDOWN:
            if self.active:
                self.cursor_visible = True
                self.cursor_timer = pygame.time.get_ticks()

                # Get modifier keys state
                mods = pygame.key.get_mods()
                ctrl = mods & pygame.KMOD_CTRL or mods & pygame.KMOD_META # Windows/Mac
                shift = mods & pygame.KMOD_SHIFT

                # Handle Shortcuts (Ctrl + A/C/V/X)
                if ctrl and event.key == pygame.K_a:
                    self.selection_start = 0
                    self.cursor_pos = len(self.text)
                    return False
                elif ctrl and event.key == pygame.K_c:
                    if self.selection_start is not None:
                        start, end = min(self.selection_start, self.cursor_pos), max(self.selection_start, self.cursor_pos)
                        pygame.scrap.put(pygame.SCRAP_TEXT, self.text[start:end].encode('utf-8'))
                    return False
                elif ctrl and event.key == pygame.K_x:
                    if self.selection_start is not None:
                        start, end = min(self.selection_start, self.cursor_pos), max(self.selection_start, self.cursor_pos)
                        pygame.scrap.put(pygame.SCRAP_TEXT, self.text[start:end].encode('utf-8'))
                        self._delete_selection()
                    return False
                elif ctrl and event.key == pygame.K_v:
                    self._delete_selection() # Replace selection if exists
                    clipboard_text = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clipboard_text:
                        clipboard_text = clipboard_text.decode('utf-8').strip('\x00') # Clean null bytes
                        self.text = self.text[:self.cursor_pos] + clipboard_text + self.text[self.cursor_pos:]
                        self.cursor_pos += len(clipboard_text)
                    return False

                if event.key == pygame.K_RETURN:
                    self.active = False
                    self.color = self.color_inactive
                    return True
                    
                elif event.key == pygame.K_BACKSPACE:
                    if not self._delete_selection() and self.cursor_pos > 0:
                        # If no selection was deleted, do a normal backspace
                        if ctrl:
                            prev_pos = self._get_prev_word_pos()
                            self.text = self.text[:prev_pos] + self.text[self.cursor_pos:]
                            self.cursor_pos = prev_pos
                        else:
                            self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                            self.cursor_pos -= 1
                        
                elif event.key == pygame.K_DELETE:
                    if not self._delete_selection() and self.cursor_pos < len(self.text):
                        if ctrl:
                            next_pos = self._get_next_word_pos()
                            self.text = self.text[:self.cursor_pos] + self.text[next_pos:]
                        else:
                            self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
                        
                elif event.key == pygame.K_LEFT:
                    if shift and self.selection_start is None: self.selection_start = self.cursor_pos
                    elif not shift: self.selection_start = None
                    
                    if ctrl: self.cursor_pos = self._get_prev_word_pos()
                    else: self.cursor_pos = max(0, self.cursor_pos - 1)
                    
                elif event.key == pygame.K_RIGHT:
                    if shift and self.selection_start is None: self.selection_start = self.cursor_pos
                    elif not shift: self.selection_start = None
                    
                    if ctrl: self.cursor_pos = self._get_next_word_pos()
                    else: self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
                    
                elif event.unicode and event.unicode.isprintable():
                    # If text is highlighted, typing replaces it
                    self._delete_selection()
                    self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                    self.cursor_pos += 1    
        return False

    def draw(self, screen):
        title_surf = self.title_font.render("Search / Tags:", True, config.TEXT_COLOR)
        screen.blit(title_surf, (self.rect.x, self.rect.y - 20))

        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=5)
        
        text_surface = self.font.render(self.text, True, config.TEXT_COLOR)
        
        # --- Camera/Scroll Logic ---
        text_width = text_surface.get_width()
        padding = 5
        visible_width = self.rect.width - (padding * 2)
        
        cursor_rel_x = self.font.size(self.text[:self.cursor_pos])[0]
        
        if cursor_rel_x - self.display_offset < 0:
            self.display_offset = cursor_rel_x
        elif cursor_rel_x - self.display_offset > visible_width:
            self.display_offset = cursor_rel_x - visible_width
            
        max_offset = max(0, text_width - visible_width)
        self.display_offset = max(0, min(self.display_offset, max_offset))
        
        screen.set_clip(self.rect)

        # --- Draw Selection Highlight Box ---
        if self.selection_start is not None and self.selection_start != self.cursor_pos:
            start_idx = min(self.selection_start, self.cursor_pos)
            end_idx = max(self.selection_start, self.cursor_pos)
            
            start_x = self.font.size(self.text[:start_idx])[0]
            end_x = self.font.size(self.text[:end_idx])[0]
            
            sel_rect = pygame.Rect(
                self.rect.left + padding + start_x - self.display_offset,
                self.rect.top + 4, 
                end_x - start_x,
                self.rect.height - 8
            )
            pygame.draw.rect(screen, self.selection_color, sel_rect)
        # ------------------------------------

        text_rect = text_surface.get_rect(
            left=self.rect.left + padding - self.display_offset, 
            centery=self.rect.centery
        )
        screen.blit(text_surface, text_rect)
        
        if self.active:
            current_time = pygame.time.get_ticks()
            if current_time - self.cursor_timer >= self.cursor_interval:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = current_time
                
            if self.cursor_visible:
                cursor_x = self.rect.left + padding + cursor_rel_x - self.display_offset
                cursor_y_top = text_rect.top + 2
                cursor_y_bottom = text_rect.bottom - 2
                pygame.draw.line(screen, config.TEXT_COLOR, (cursor_x, cursor_y_top), (cursor_x, cursor_y_bottom), 2)
        screen.set_clip(None)

class SeekBar:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_dragging = False
        self.progress = 0.0
        self.title_font = pygame.font.SysFont(None, 24)

    def handle_event(self, event):
        """Processes events and returns progress percentage if dragged, else None."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hitbox = self.rect.inflate(0, config.SLIDER_KNOB_RADIUS * 2)
            if hitbox.collidepoint(event.pos):
                self.is_dragging = True
                return self._update_progress(event.pos[0])
                
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                return self._update_progress(event.pos[0])
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                return self._update_progress(event.pos[0])
                
        return None

    def _update_progress(self, mouse_x):
        clamped_x = utils.clamp(mouse_x, self.rect.left, self.rect.right)
        self.progress = (clamped_x - self.rect.left) / self.rect.width
        return self.progress

    def draw(self, screen, current_frame, total_frames):
        # Only auto-update progress if the user isn't actively dragging it
        if not self.is_dragging and total_frames > 1:
            self.progress = current_frame / (total_frames - 1)

        # Draw Label
        title_surf = self.title_font.render("", True, config.TEXT_COLOR)
        screen.blit(title_surf, (self.rect.x, self.rect.y - 20))

        # Track
        pygame.draw.rect(screen, config.SEEKBAR_BG_COLOR, self.rect, border_radius=5)
        
        # Fill
        fill_width = int(self.rect.width * self.progress)
        fill_rect = pygame.Rect(self.rect.left, self.rect.top, fill_width, self.rect.height)
        pygame.draw.rect(screen, config.SEEKBAR_FILL_COLOR, fill_rect, border_radius=5)
        
        # Knob
        knob_x = self.rect.left + fill_width
        knob_y = self.rect.centery
        pygame.draw.circle(screen, config.SEEKBAR_KNOB_COLOR, (knob_x, knob_y), config.SLIDER_KNOB_RADIUS)

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