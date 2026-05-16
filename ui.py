from dataclasses import dataclass

import utils
import config
import pygame

_loading_overlay_cache = {}
_seek_preview_surface_cache = {}  # (frame_index, src_w, src_h) -> scaled Surface
_chrome_label_cache = {}  # deck_label -> (meta_surf, title_surf)


@dataclass
class GameUI:
    next_button: "Button"
    skip_button: "Button"
    save_button: "Button"
    menu_button: "Button"
    volume_slider: "VolumeSlider"
    search_box: "TextBox"
    seek_bar: "SeekBar"
    title_font: object
    meta_font: object


@dataclass
class MenuUI:
    deck_cards: list["DeckCard"]
    start_button: "Button"
    decks_tab_btn: "Button"
    options_tab_btn: "Button"
    tasks_tab_btn: "Button"
    title_font: object
    subtitle_font: object
    body_font: object


def create_game_ui(font, on_volume_change, initial_volume):
    button_font = pygame.font.SysFont(None, 34)
    input_font = pygame.font.SysFont(None, 30)
    title_font = pygame.font.SysFont(None, 38)
    meta_font = pygame.font.SysFont(None, 24)
    next_text = "Next" if config.GRID_SIZE == 1 else "Next Puzzle"
    return GameUI(
        next_button=Button(
            config.WIN_BUTTON_X,
            config.WIN_BUTTON_Y,
            config.WIN_BUTTON_WIDTH,
            config.WIN_BUTTON_HEIGHT,
            next_text,
            button_font,
            config.TEXT_COLOR,
            config.WIN_BUTTON_COLOR,
            config.WIN_BUTTON_PRESS_COLOR,
            config.WIN_BUTTON_BORDER,
            10,
        ),
        skip_button=Button(
            config.SKIP_BUTTON_X,
            config.SKIP_BUTTON_Y,
            config.SKIP_BUTTON_WIDTH,
            config.SKIP_BUTTON_HEIGHT,
            "Skip",
            button_font,
            config.TEXT_COLOR,
            config.SKIP_BUTTON_COLOR,
            config.SKIP_BUTTON_PRESS_COLOR,
            config.SKIP_BUTTON_BORDER,
        ),
        save_button=Button(
            config.SAVE_BUTTON_X,
            config.SAVE_BUTTON_Y,
            config.SAVE_BUTTON_WIDTH,
            config.SAVE_BUTTON_HEIGHT,
            "Save",
            button_font,
            config.TEXT_COLOR,
            config.SAVE_BUTTON_COLOR,
            config.SAVE_BUTTON_PRESS_COLOR,
            config.SAVE_BUTTON_BORDER,
        ),
        menu_button=Button(
            config.MENU_BUTTON_X,
            config.MENU_BUTTON_Y,
            config.MENU_BUTTON_WIDTH,
            config.MENU_BUTTON_HEIGHT,
            "Main Menu",
            button_font,
            config.TEXT_COLOR,
            config.MENU_BUTTON_COLOR,
            config.MENU_BUTTON_PRESS_COLOR,
            config.MENU_BUTTON_BORDER,
        ),
        volume_slider=VolumeSlider(
            config.SLIDER_X,
            config.SLIDER_Y,
            config.SLIDER_WIDTH,
            config.SLIDER_HEIGHT,
            initial_volume,
            on_volume_change,
        ),
        search_box=TextBox(
            config.TEXTBOX_X,
            config.TEXTBOX_Y,
            config.TEXTBOX_WIDTH,
            config.TEXTBOX_HEIGHT,
            input_font,
        ),
        seek_bar=SeekBar(
            config.SEEKBAR_X,
            config.SEEKBAR_Y,
            config.SEEKBAR_WIDTH,
            config.SEEKBAR_HEIGHT,
        ),
        title_font=title_font,
        meta_font=meta_font,
    )

def create_menu_ui(deck_specs):
    title_font = pygame.font.SysFont(None, 76)
    subtitle_font = pygame.font.SysFont(None, 34)
    body_font = pygame.font.SysFont(None, 28)
    card_title_font = pygame.font.SysFont(None, 36)
    card_body_font = pygame.font.SysFont(None, 26)
    tab_font = pygame.font.SysFont(None, 36)

    deck_cards = []
    for index, spec in enumerate(deck_specs):
        row = index // 2
        col = index % 2
        x = config.MENU_GRID_X + col * (config.MENU_CARD_WIDTH + config.MENU_CARD_GAP)
        y = config.MENU_GRID_Y + config.MENU_CARD_GAP + row * (config.MENU_CARD_HEIGHT + config.MENU_CARD_GAP)
        deck_cards.append(
            DeckCard(
                x,
                y,
                config.MENU_CARD_WIDTH,
                config.MENU_CARD_HEIGHT,
                spec.key,
                spec.label,
                spec.description,
                spec.supports_search,
                card_title_font,
                card_body_font,
            )
        )

    decks_tab_btn = Button(
        config.MENU_GRID_X, config.TAB_Y, config.TAB_W, config.TAB_H, "Decks", tab_font,
        config.TEXT_COLOR, config.MENU_CARD_COLOR, config.MENU_CARD_PRESS_COLOR, config.MENU_CARD_BORDER
    )

    tasks_tab_btn = Button(
        config.MENU_GRID_X + config.TAB_W + 20, config.TAB_Y, config.TAB_W, config.TAB_H, "Tasks", tab_font,
        config.TEXT_COLOR, config.MENU_CARD_COLOR, config.MENU_CARD_PRESS_COLOR, config.MENU_CARD_BORDER
    )

    options_tab_btn = Button(
        config.MENU_GRID_X + (2 *  config.TAB_W) + 40, config.TAB_Y, config.TAB_W, config.TAB_H, "Options", tab_font,
        config.TEXT_COLOR, config.MENU_CARD_COLOR, config.MENU_CARD_PRESS_COLOR, config.MENU_CARD_BORDER
    )
    
    return MenuUI(
        deck_cards=deck_cards,
        start_button=Button(
            config.MENU_INFO_X,
            config.MENU_START_MIN_Y,
            240,
            58,
            "Start Puzzle",
            body_font,
            config.TEXT_COLOR,
            config.MENU_START_BUTTON_COLOR,
            config.MENU_START_BUTTON_PRESS_COLOR,
            config.MENU_START_BUTTON_BORDER,
        ),
        decks_tab_btn=decks_tab_btn,
        options_tab_btn=options_tab_btn,
        tasks_tab_btn=tasks_tab_btn,
        title_font=title_font,
        subtitle_font=subtitle_font,
        body_font=body_font,
    )


class DeckCard:
    def __init__(self, x, y, width, height, key, title, description, supports_search, title_font, body_font):
        self.rect = pygame.Rect(x, y, width, height)
        self.key = key
        self.title = title
        self.description = description
        self.supports_search = supports_search
        self.title_font = title_font
        self.body_font = body_font
        self.content_width = self.rect.width - 36
        self.title_surf = self.title_font.render(self.title, True, config.TEXT_COLOR)
        self.description_surfs = [
            self.body_font.render(line, True, config.MENU_SUBTEXT_COLOR)
            for line in _fit_wrapped_lines(self.body_font, self.description, self.content_width, 2)
        ]
        footer_text = "Search in sidebar" if self.supports_search else "Local folder deck"
        footer_line = _fit_wrapped_lines(self.body_font, footer_text, self.content_width, 1)[0]
        self.footer_surf = self.body_font.render(footer_line, True, config.MENU_SUBTEXT_COLOR)

        self.is_pressed = False
        self.is_hovered = False
        self.cooldown_ms = 100
        self.last_click_time = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                current_time = pygame.time.get_ticks()
                if current_time - self.last_click_time >= self.cooldown_ms:
                    self.last_click_time = current_time
                    self.is_pressed = True
                    self.is_hovered = True
                    return True
            return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_pressed = False

        return False

    def draw(self, screen, selected=False):
        if self.is_pressed:
            fill_color = config.MENU_CARD_PRESS_COLOR
        elif selected:
            fill_color = config.MENU_CARD_SELECTED_COLOR
        elif self.is_hovered:
            fill_color = config.MENU_CARD_HOVER_COLOR
        else:
            fill_color = config.MENU_CARD_COLOR

        border_color = config.MENU_CARD_SELECTED_BORDER if selected else config.MENU_CARD_BORDER

        pygame.draw.rect(screen, fill_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=8)

        text_clip_rect = self.rect.inflate(-12, -12)
        screen.set_clip(text_clip_rect)
        screen.blit(self.title_surf, (self.rect.x + 18, self.rect.y + 18))
        for index, surf in enumerate(self.description_surfs):
            screen.blit(surf, (self.rect.x + 18, self.rect.y + 62 + (index * 24)))
        screen.blit(self.footer_surf, (self.rect.x + 18, self.rect.bottom - 34))
        screen.set_clip(None)


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
        self.text_surf = self.font.render(self.text, True, self.text_color)
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)

    def set_position(self, x, y):
        self.rect.topleft = (x, y)
        self.text_rect = self.text_surf.get_rect(center=self.rect.center)
    
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
        screen.blit(self.text_surf, self.text_rect)
    
class VolumeSlider:
    def __init__(self, x, y, width, height, initial_volume, on_change_callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.volume = initial_volume
        self.is_dragging = False
        self.on_change_callback = on_change_callback
        self.font = pygame.font.SysFont(None, 28)
        self._label_pct = None
        self._label_surf = None

    def set_position(self, x, y):
        self.rect.topleft = (x, y)
    
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
        vol_pct = int(self.volume * 100)
        if vol_pct != self._label_pct:
            self._label_pct = vol_pct
            self._label_surf = self.font.render(f"Volume: {vol_pct}%", True, config.TEXT_COLOR)
        screen.blit(self._label_surf, (self.rect.left, self.rect.top - 30))

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
        self.title_surf = self.title_font.render("Search / Tags:", True, config.TEXT_COLOR)

        # --- Cursor variables ---
        self.cursor_pos = len(self.text)
        self.selection_start = None

        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_interval = 500
        self.display_offset = 0 # For horizontal scrolling of long text
        self._cached_text = None
        self._cached_text_surf = None

    def set_text(self, text):
        self.text = text or ''
        self.cursor_pos = len(self.text)
        self.selection_start = None
        self.display_offset = 0
        self.active = False
        self.color = self.color_inactive

    def set_title(self, title):
        self.title_surf = self.title_font.render(title, True, config.TEXT_COLOR)

    def set_position(self, x, y):
        self.rect.topleft = (x, y)

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
        screen.blit(self.title_surf, (self.rect.x, self.rect.y - 20))

        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=5)
        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=5)
        
        if self.text != self._cached_text:
            self._cached_text = self.text
            self._cached_text_surf = self.font.render(self.text, True, config.TEXT_COLOR)
        text_surface = self._cached_text_surf
        
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

def _wrap_text(font, text, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        trial_line = word if not current_line else f"{current_line} {word}"
        if font.size(trial_line)[0] <= max_width:
            current_line = trial_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines

def _ellipsize_text(font, text, max_width):
    if font.size(text)[0] <= max_width:
        return text

    trimmed = text
    while trimmed and font.size(f"{trimmed}...")[0] > max_width:
        trimmed = trimmed[:-1].rstrip()

    return f"{trimmed}..." if trimmed else "..."

def _fit_wrapped_lines(font, text, max_width, max_lines):
    lines = _wrap_text(font, text, max_width)
    if len(lines) <= max_lines:
        return lines

    fitted = lines[:max_lines - 1]
    remaining = " ".join(lines[max_lines - 1:])
    fitted.append(_ellipsize_text(font, remaining, max_width))
    return fitted

def layout_game_sidebar(controls, show_search, show_volume):
    current_y = config.WIN_BUTTON_Y

    controls.next_button.set_position(config.WIN_BUTTON_X, current_y)
    controls.skip_button.set_position(config.SKIP_BUTTON_X, current_y)
    current_y += config.WIN_BUTTON_HEIGHT + 14

    controls.save_button.set_position(config.SAVE_BUTTON_X, current_y)
    current_y += config.SAVE_BUTTON_HEIGHT

    if show_search:
        current_y += 14
        controls.search_box.set_position(config.TEXTBOX_X, current_y + 20)
        current_y = controls.search_box.rect.bottom

    if show_volume:
        current_y += 14
        controls.volume_slider.set_position(config.SLIDER_X, current_y + 30)

def _format_time_ms(ms):
    total_seconds = max(0, int(ms // 1000))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

def draw_seek_preview(screen, puzzle, controls, preview_frame):
    preview_rect = pygame.Rect(
        0,
        0,
        config.SEEK_PREVIEW_WIDTH,
        config.SEEK_PREVIEW_HEIGHT + config.SEEK_PREVIEW_FOOTER_HEIGHT,
    )
    anchor_x = controls.seek_bar.rect.left + int(controls.seek_bar.progress * controls.seek_bar.rect.width)
    preview_rect.midbottom = (anchor_x, controls.seek_bar.rect.top - config.SEEK_PREVIEW_GAP)

    min_left = config.PUZZLE_PANEL_X + 14
    max_right = config.PUZZLE_PANEL_X + config.PUZZLE_PANEL_WIDTH - 14
    preview_rect.left = max(min_left, preview_rect.left)
    preview_rect.right = min(max_right, preview_rect.right)
    if preview_rect.left < min_left:
        preview_rect.left = min_left
    if preview_rect.right > max_right:
        preview_rect.right = max_right

    image_rect = pygame.Rect(
        preview_rect.x,
        preview_rect.y,
        config.SEEK_PREVIEW_WIDTH,
        config.SEEK_PREVIEW_HEIGHT,
    )
    footer_rect = pygame.Rect(
        preview_rect.x,
        preview_rect.bottom - config.SEEK_PREVIEW_FOOTER_HEIGHT,
        config.SEEK_PREVIEW_WIDTH,
        config.SEEK_PREVIEW_FOOTER_HEIGHT,
    )

    pygame.draw.rect(screen, config.MENU_PANEL_COLOR, preview_rect, border_radius=8)
    pygame.draw.rect(screen, config.MENU_PANEL_BORDER, preview_rect, 2, border_radius=8)
    pygame.draw.rect(screen, config.MENU_CARD_PRESS_COLOR, footer_rect, border_radius=8)

    frame_surface = puzzle.peek_preview(preview_frame)
    if frame_surface is None:
        frame_surface = puzzle.peek_frame(preview_frame)
    inset_rect = image_rect.inflate(-8, -8)
    if frame_surface is not None:
        src_w, src_h = frame_surface.get_size()
        if src_w == inset_rect.width and src_h == inset_rect.height:
            preview_surface_rect = frame_surface.get_rect(center=inset_rect.center)
            screen.blit(frame_surface, preview_surface_rect)
        else:
            scale = min(inset_rect.width / src_w, inset_rect.height / src_h)
            scaled_w = max(1, round(src_w * scale))
            scaled_h = max(1, round(src_h * scale))
            cache_key = (preview_frame, src_w, src_h)
            preview_surface = _seek_preview_surface_cache.get(cache_key)
            if preview_surface is None:
                preview_surface = pygame.transform.smoothscale(frame_surface, (scaled_w, scaled_h))
                # Keep cache small — only the most recent few frames matter
                if len(_seek_preview_surface_cache) > 16:
                    _seek_preview_surface_cache.pop(next(iter(_seek_preview_surface_cache)))
                _seek_preview_surface_cache[cache_key] = preview_surface
            preview_surface_rect = preview_surface.get_rect(center=inset_rect.center)
            screen.blit(preview_surface, preview_surface_rect)
    else:
        pygame.draw.rect(screen, config.MENU_CARD_COLOR, inset_rect, border_radius=6)
        loading_surf = controls.meta_font.render("Loading preview...", True, config.MENU_SUBTEXT_COLOR)
        loading_rect = loading_surf.get_rect(center=inset_rect.center)
        screen.blit(loading_surf, loading_rect)

    timestamp = _format_time_ms(puzzle.frame_start_ms(preview_frame))
    if puzzle.total_duration_ms > 0:
        timestamp = f"{timestamp} / {_format_time_ms(puzzle.total_duration_ms)}"
    time_surf = controls.meta_font.render(timestamp, True, config.TEXT_COLOR)
    time_rect = time_surf.get_rect(center=footer_rect.center)
    screen.blit(time_surf, time_rect)

def draw_game_chrome(screen, controls, deck_label):
    sidebar_rect = pygame.Rect(
        config.SIDEBAR_PANEL_X,
        config.SIDEBAR_PANEL_Y,
        config.SIDEBAR_PANEL_WIDTH,
        config.SIDEBAR_PANEL_HEIGHT,
    )
    puzzle_panel_rect = pygame.Rect(
        config.PUZZLE_PANEL_X,
        config.PUZZLE_PANEL_Y,
        config.PUZZLE_PANEL_WIDTH,
        config.PUZZLE_PANEL_HEIGHT,
    )
    footer_rect = pygame.Rect(
        config.PUZZLE_PANEL_X + 1,
        config.PUZZLE_PANEL_Y + config.PUZZLE_PANEL_HEIGHT - config.PUZZLE_FOOTER_HEIGHT,
        config.PUZZLE_PANEL_WIDTH - 2,
        config.PUZZLE_FOOTER_HEIGHT - 1,
    )

    pygame.draw.rect(screen, config.MENU_PANEL_COLOR, sidebar_rect, border_radius=8)
    pygame.draw.rect(screen, config.MENU_PANEL_BORDER, sidebar_rect, 2, border_radius=8)
    pygame.draw.rect(screen, config.MENU_PANEL_COLOR, puzzle_panel_rect, border_radius=8)
    pygame.draw.rect(screen, config.MENU_PANEL_BORDER, puzzle_panel_rect, 2, border_radius=8)
    pygame.draw.rect(screen, config.MENU_CARD_PRESS_COLOR, footer_rect, border_radius=8)
    pygame.draw.line(
        screen,
        config.MENU_PANEL_BORDER,
        (footer_rect.left + 16, footer_rect.top),
        (footer_rect.right - 16, footer_rect.top),
        2,
    )

    cached = _chrome_label_cache.get(deck_label)
    if cached is None:
        meta_surf = controls.meta_font.render("Current Deck", True, config.MENU_SUBTEXT_COLOR)
        title_surf = controls.title_font.render(deck_label, True, config.TEXT_COLOR)
        _chrome_label_cache.clear()  # only ever need one entry
        _chrome_label_cache[deck_label] = (meta_surf, title_surf)
    else:
        meta_surf, title_surf = cached
    screen.blit(meta_surf, (config.CONTROL_X, config.SIDEBAR_PANEL_Y + 18))
    screen.blit(title_surf, (config.CONTROL_X, config.SIDEBAR_PANEL_Y + 42))
    pygame.draw.line(
        screen,
        config.MENU_PANEL_BORDER,
        (config.CONTROL_X, config.SIDEBAR_PANEL_Y + 94),
        (config.CONTROL_X + config.CONTROL_WIDTH, config.SIDEBAR_PANEL_Y + 94),
        2,
    )

def draw_main_menu(screen, menu_ui, state, deck_specs_by_key):
    screen.fill(config.BG_MAIN)

    divider_x = config.MENU_GRID_X - 32
    left_panel_rect = pygame.Rect(32, 72, divider_x - 56, config.WINDOW_HEIGHT - 144)
    left_content_rect = left_panel_rect.inflate(-28, -28)

    pygame.draw.rect(screen, config.MENU_PANEL_COLOR, left_panel_rect, border_radius=8)
    pygame.draw.rect(screen, config.MENU_PANEL_BORDER, left_panel_rect, 2, border_radius=8)
    pygame.draw.line(screen, config.MENU_PANEL_BORDER, (divider_x, 72), (divider_x, config.WINDOW_HEIGHT - 72), 2)

    selected_spec = deck_specs_by_key[state.selected_deck_key]
    title_lines = _wrap_text(menu_ui.title_font, "Puzzle Decks", left_content_rect.width)
    subtitle_lines = _wrap_text(
        menu_ui.subtitle_font,
        "Pick a source, then jump into a new board.",
        left_content_rect.width,
    )
    selected_note_text = "Use the sidebar search box after starting." if selected_spec.supports_search else "Plays from your local folder without a search box filter."
    description_lines = _wrap_text(menu_ui.body_font, selected_spec.description, left_content_rect.width)
    note_lines = _wrap_text(menu_ui.body_font, selected_note_text, left_content_rect.width)

    screen.set_clip(left_content_rect)

    current_y = config.MENU_INFO_Y
    for index, line in enumerate(title_lines):
        line_surf = menu_ui.title_font.render(line, True, config.TEXT_COLOR)
        screen.blit(line_surf, (config.MENU_INFO_X, current_y + (index * 62)))

    current_y += len(title_lines) * 62 + 10
    for index, line in enumerate(subtitle_lines):
        line_surf = menu_ui.subtitle_font.render(line, True, config.MENU_SUBTEXT_COLOR)
        screen.blit(line_surf, (config.MENU_INFO_X, current_y + (index * 34)))

    current_y += len(subtitle_lines) * 34 + 38
    selected_title = menu_ui.subtitle_font.render(selected_spec.label, True, config.TEXT_COLOR)
    screen.blit(selected_title, (config.MENU_INFO_X, current_y))

    current_y += 40
    for index, line in enumerate(description_lines):
        line_surf = menu_ui.body_font.render(line, True, config.MENU_SUBTEXT_COLOR)
        screen.blit(line_surf, (config.MENU_INFO_X, current_y + (index * 28)))

    note_start_y = current_y + (len(description_lines) * 28) + 4
    for index, line in enumerate(note_lines):
        line_surf = menu_ui.body_font.render(line, True, config.MENU_SUBTEXT_COLOR)
        screen.blit(line_surf, (config.MENU_INFO_X, note_start_y + (index * 28)))

    start_button_y = max(
        config.MENU_START_MIN_Y,
        note_start_y + (len(note_lines) * 28) + 24,
    )
    menu_ui.start_button.set_position(config.MENU_INFO_X, start_button_y)
    menu_ui.start_button.draw(screen)

    if state.menu_error:
        status_y = menu_ui.start_button.rect.bottom + config.MENU_STATUS_SPACING
        error_title = menu_ui.body_font.render("Could not start deck:", True, config.MENU_ERROR_COLOR)
        screen.blit(error_title, (config.MENU_INFO_X, status_y))

        error_lines = _wrap_text(menu_ui.body_font, state.menu_error, config.MENU_INFO_WIDTH)
        for index, line in enumerate(error_lines[:4]):
            line_surf = menu_ui.body_font.render(line, True, config.MENU_ERROR_COLOR)
            screen.blit(line_surf, (config.MENU_INFO_X, status_y + 32 + (index * 28)))

    screen.set_clip(None)

    if state.menu_tab == "decks":
        menu_ui.decks_tab_btn.base_color = config.MENU_CARD_SELECTED_COLOR
        menu_ui.options_tab_btn.base_color = config.MENU_CARD_COLOR
        menu_ui.tasks_tab_btn.base_color = config.MENU_CARD_COLOR
    elif state.menu_tab == "options":
        menu_ui.decks_tab_btn.base_color = config.MENU_CARD_COLOR
        menu_ui.options_tab_btn.base_color = config.MENU_CARD_SELECTED_COLOR
        menu_ui.tasks_tab_btn.base_color = config.MENU_CARD_COLOR
    elif state.menu_tab == "tasks":
        menu_ui.decks_tab_btn.base_color = config.MENU_CARD_COLOR
        menu_ui.options_tab_btn.base_color = config.MENU_CARD_COLOR
        menu_ui.tasks_tab_btn.base_color = config.MENU_CARD_SELECTED_COLOR

    menu_ui.decks_tab_btn.draw(screen)
    menu_ui.options_tab_btn.draw(screen)
    menu_ui.tasks_tab_btn.draw(screen)

    if state.menu_tab == "decks":
        deck_subheader = menu_ui.body_font.render("Choose the feed you want to puzzle from.", True, config.MENU_SUBTEXT_COLOR)
        screen.blit(deck_subheader, (config.MENU_GRID_X, config.MENU_GRID_Y - 20))
        for card in menu_ui.deck_cards:
            card.draw(screen, selected=card.key == state.selected_deck_key)
    elif state.menu_tab == "options":
        placeholder_text = menu_ui.body_font.render("Options will go here soon!", True, config.MENU_SUBTEXT_COLOR)
        screen.blit(placeholder_text, (config.MENU_GRID_X, config.MENU_GRID_Y - 20))
    elif state.menu_tab == "tasks":
        placeholder_text = menu_ui.body_font.render("Tasks will go here soon!", True, config.MENU_SUBTEXT_COLOR)
        screen.blit(placeholder_text, (config.MENU_GRID_X, config.MENU_GRID_Y - 20))
    pygame.display.flip()

def draw_loading_overlay(screen, font, status_text="Loading Next Media..."):
    """Draws an unobtrusive floating banner at the bottom of the puzzle area."""
    cache_key = (font.get_height(), status_text)
    cached_surfaces = _loading_overlay_cache.get(cache_key)

    if cached_surfaces is None:
        text_surf = font.render(status_text , True, config.TEXT_COLOR)
        padding_x = 40
        padding_y = 20
        box_width = text_surf.get_width() + padding_x
        box_height = text_surf.get_height() + padding_y

        box_surf = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, (30, 32, 37, 220), box_surf.get_rect(), border_radius=15)
        pygame.draw.rect(box_surf, config.MENU_PANEL_BORDER, box_surf.get_rect(), 2, border_radius=15)
        _loading_overlay_cache[cache_key] = (box_surf, text_surf)
        cached_surfaces = (box_surf, text_surf)

    box_surf, text_surf = cached_surfaces

    # centered at bottom of puzzle area
    center_x = config.PUZZLE_PANEL_X + (config.PUZZLE_PANEL_WIDTH // 2)
    center_y = config.PUZZLE_PANEL_Y + 34
    
    box_rect = box_surf.get_rect(center=(center_x, center_y))
    text_rect = text_surf.get_rect(center=box_rect.center)
    
    screen.blit(box_surf, box_rect)
    screen.blit(text_surf, text_rect)
