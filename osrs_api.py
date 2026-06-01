import platform
import sys
import ctypes

# 1. Set Windows DPI awareness IMMEDIATELY before importing GUI/graphics libraries.
# This prevents cached scaled coordinates by PyAutoGUI and Pillow.
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

if IS_WINDOWS:
    try:
        # Set process as DPI aware so that Windows returns true physical coordinates
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# 2. Import standard and external libraries
import time
import random
import cv2
import numpy as np
from PIL import ImageGrab
import pyautogui
import human_mouse
import subprocess
import re

if IS_WINDOWS:
    import win32gui
    import win32con
    import win32process
    import pygetwindow as gw

# ==============================================================================
# 3. ADVANCED CLASS INTERFACE: ContourManager
# ==============================================================================
class ContourManager:
    """
    Manages OSRS RuneLite client interaction by focusing the window,
    detecting solid colored contours, and clicking them using human-like movements.
    Cross-platform support for Windows and Linux.
    """
    
    # Predefined colors in BGR format
    COLOR_MAP = {
        "blue": [255, 0, 0],
        "green": [0, 255, 0],
        "magenta": [255, 0, 255],
        "pink": [255, 0, 255],
        "yellow": [0, 255, 255],
        "red": [0, 0, 255]
    }
    
    def __init__(self, window_title="RuneLite"):
        self.window_title = window_title
        
    def find_window(self):
        """
        Finds the window matching window_title (case-insensitive partial match).
        Returns:
            On Windows: HWND (int) or None
            On Linux: Window ID (str) or None
        """
        if IS_WINDOWS:
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows:
                # Fallback to case-insensitive match
                all_wins = gw.getAllWindows()
                windows = [w for w in all_wins if self.window_title.lower() in w.title.lower()]
                
            if windows:
                return windows[0]._hWnd
            return None
            
        elif IS_LINUX:
            # Try using xdotool search
            try:
                out = subprocess.check_output(
                    ["xdotool", "search", "--onlyvisible", "--name", self.window_title],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                ids = out.split()
                if ids:
                    return ids[0]
            except Exception:
                pass
            
            # Fallback to wmctrl
            try:
                out = subprocess.check_output(["wmctrl", "-l"], stderr=subprocess.DEVNULL).decode()
                for line in out.splitlines():
                    if self.window_title.lower() in line.lower():
                        parts = line.split(None, 3)
                        if parts:
                            return parts[0]  # Hex window ID
            except Exception:
                pass
            return None
            
        else:
            print(f"[!] Unsupported operating system: {platform.system()}")
            return None
        
    def focus_window(self):
        """
        Brings the RuneLite window to the foreground and focuses it.
        """
        hwnd = self.find_window()
        if not hwnd:
            print(f"[!] Window containing '{self.window_title}' not found.")
            return False
            
        if IS_WINDOWS:
            try:
                # If minimized, restore it
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                    
                # Bring to foreground (with bypass for SetForegroundWindow locks)
                # We simulate an ALT key press which resets the foreground lock
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys('%')  # Send ALT
                
                win32gui.SetForegroundWindow(hwnd)
                # Wait for window repaint
                time.sleep(random.uniform(0.5, 0.8))
                return True
            except Exception as e:
                print(f"[!] Error focusing window: {e}")
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(random.uniform(0.5, 0.8))
                    return True
                except Exception as e2:
                    print(f"[!] Fallback focus also failed: {e2}")
                    return False
                    
        elif IS_LINUX:
            try:
                # Try with xdotool
                subprocess.check_call(["xdotool", "windowactivate", hwnd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(random.uniform(0.5, 0.8))
                return True
            except Exception:
                pass
            try:
                # Fallback to wmctrl
                subprocess.check_call(["wmctrl", "-i", "-a", hwnd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(random.uniform(0.5, 0.8))
                return True
            except Exception as e:
                print(f"[!] Error focusing window on Linux: {e}")
                return False
        return False
                
    def get_client_rect(self):
        """
        Returns the client area rectangle in screen coordinates: (left, top, right, bottom)
        """
        hwnd = self.find_window()
        if not hwnd:
            return None
            
        if IS_WINDOWS:
            try:
                left, top = win32gui.ClientToScreen(hwnd, (0, 0))
                _, _, width, height = win32gui.GetClientRect(hwnd)
                return (left, top, left + width, top + height)
            except Exception as e:
                print(f"[!] Error getting client rect: {e}")
                return None
                
        elif IS_LINUX:
            # Try to get window geometry from xdotool
            try:
                out = subprocess.check_output(["xdotool", "getwindowgeometry", hwnd], stderr=subprocess.DEVNULL).decode()
                pos_match = re.search(r"Position:\s*(\d+),(\d+)", out)
                geom_match = re.search(r"Geometry:\s*(\d+)x(\d+)", out)
                if pos_match and geom_match:
                    left, top = int(pos_match.group(1)), int(pos_match.group(2))
                    width, height = int(geom_match.group(1)), int(geom_match.group(2))
                    return (left, top, left + width, top + height)
            except Exception:
                pass
                
            # Fallback to xwininfo
            try:
                out = subprocess.check_output(["xwininfo", "-id", hwnd], stderr=subprocess.DEVNULL).decode()
                x_match = re.search(r"Absolute upper-left X:\s*(\d+)", out)
                y_match = re.search(r"Absolute upper-left Y:\s*(\d+)", out)
                w_match = re.search(r"Width:\s*(\d+)", out)
                h_match = re.search(r"Height:\s*(\d+)", out)
                if x_match and y_match and w_match and h_match:
                    left = int(x_match.group(1))
                    top = int(y_match.group(1))
                    width = int(w_match.group(1))
                    height = int(h_match.group(1))
                    return (left, top, left + width, top + height)
            except Exception as e:
                print(f"[!] Error getting window geometry on Linux: {e}")
                
            return None
        return None
            
    def capture_client_area(self):
        """
        Captures the client area of the window.
        Returns:
            img: OpenCV BGR image of the client area
            offset: (left, top) screen coordinate offset of the client area
        """
        rect = self.get_client_rect()
        if not rect:
            return None, (0, 0)
            
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        
        if width <= 0 or height <= 0:
            return None, (0, 0)
            
        # Take screen capture using Pillow
        screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
        
        # Convert RGB (Pillow) to BGR (OpenCV)
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return img, (left, top)
        
    def _get_color_bgr(self, color_name_or_bgr):
        """
        Helper to convert color name (string) or BGR list to BGR list.
        """
        if isinstance(color_name_or_bgr, str):
            name = color_name_or_bgr.lower()
            if name in self.COLOR_MAP:
                return self.COLOR_MAP[name]
            else:
                raise ValueError(f"Unknown color name: '{color_name_or_bgr}'. Use one of {list(self.COLOR_MAP.keys())} or pass BGR [B, G, R]")
        return list(color_name_or_bgr)
        
    def find_contours(self, img, color, min_area=15, tolerance=25, min_fill_ratio=0.75):
        """
        Finds contours of a specific color inside the captured image.
        Uses absolute difference with tolerance to handle compression/lighting.
        Enforces that the shape must be a closed, filled area (using min_fill_ratio).
        """
        bgr = self._get_color_bgr(color)
        
        # Use cv2.absdiff for high performance tolerance mask
        diff = cv2.absdiff(img, np.array(bgr, dtype=np.uint8))
        mask = (diff[:, :, 0] <= tolerance) & (diff[:, :, 1] <= tolerance) & (diff[:, :, 2] <= tolerance)
        binary_mask = mask.astype(np.uint8) * 255
        
        # Find contours
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by minimum area and fill ratio (solid closed areas)
        filtered_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_area:
                # Create a temporary binary mask for just this contour filled in
                contour_mask = np.zeros(binary_mask.shape, dtype=np.uint8)
                cv2.drawContours(contour_mask, [cnt], -1, 255, thickness=-1)
                
                # Count matching target pixels inside this contour
                matching_pixels = np.sum((binary_mask == 255) & (contour_mask == 255))
                filled_pixels = np.sum(contour_mask == 255)
                
                # Calculate what fraction of the enclosed area is actually the target color
                fill_ratio = matching_pixels / filled_pixels if filled_pixels > 0 else 0
                
                if fill_ratio >= min_fill_ratio:
                    filtered_contours.append(cnt)
                
        return filtered_contours
        
    def get_random_point_in_contour(self, contour, border_margin=3):
        """
        Finds a random point (x, y) inside the contour, enforcing a safety margin from the boundary.
        Uses cv2.pointPolygonTest (with measureDist=True) to check distance to the edge.
        """
        x, y, w, h = cv2.boundingRect(contour)
        
        # Try to find a point that is well inside the contour
        for _ in range(150):
            rx = random.randint(x + border_margin, x + w - 1 - border_margin)
            ry = random.randint(y + border_margin, y + h - 1 - border_margin)
            
            # Measure distance from point to the closest contour edge
            # Positive value means inside the contour
            dist = cv2.pointPolygonTest(contour, (rx, ry), True)
            if dist >= border_margin:
                return rx, ry
                
        # Fallback to centroid if no point matches the margin
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            # Validate if centroid is inside
            if cv2.pointPolygonTest(contour, (cx, cy), False) >= 0:
                return cx, cy
            
        # Hard fallback to center of bounding box
        return x + w // 2, y + h // 2
        
    def verify_color_at_mouse(self, target_color, neighborhood_size=9, tolerance=30):
        """
        Verifies that the target color is present near the mouse position on screen.
        Takes a small screenshot of the neighborhood around the cursor.
        """
        x, y = pyautogui.position()
        half = neighborhood_size // 2
        
        # Grab neighborhood
        bbox = (x - half, y - half, x + half + 1, y + half + 1)
        try:
            img = ImageGrab.grab(bbox=bbox)
            img_np = np.array(img)  # RGB
            
            # Convert target BGR to RGB
            bgr = self._get_color_bgr(target_color)
            target_rgb = np.array([bgr[2], bgr[1], bgr[0]])
            
            # Check if any pixel in the neighborhood matches the target color
            for row in img_np:
                for pixel in row:
                    dist = np.linalg.norm(pixel - target_rgb)
                    if dist <= tolerance:
                        return True
            return False
        except Exception as e:
            print(f"[!] Error verifying color at mouse: {e}")
            return False
            
    def click_contour(self, contour, color, client_offset, max_retries=5):
        """
        Clicks a random point inside the contour.
        Moves mouse, verifies color, and clicks.
        Supports dynamic tracking: If validation fails, it recaptures the screen to find the target's new position.
        Returns True if clicked successfully, False otherwise.
        """
        bgr = self._get_color_bgr(color)
        left_offset, top_offset = client_offset
        current_contour = contour
        
        for attempt in range(max_retries):
            # 1. Get a random point inside the contour, enforcing a 3-pixel safety margin from the boundary
            rx, ry = self.get_random_point_in_contour(current_contour, border_margin=3)
            
            # 2. Convert to absolute screen coordinates
            screen_x = rx + left_offset
            screen_y = ry + top_offset
            
            # 3. Move mouse to screen coordinates
            human_mouse.move_to(screen_x, screen_y)
            
            # 4. Wait a fraction of a second to let the cursor settle
            time.sleep(random.uniform(0.08, 0.15))
            
            # 5. Snap cursor to target position if OS scaling/acceleration caused a 1-2px drift
            cur_x, cur_y = pyautogui.position()
            if cur_x != screen_x or cur_y != screen_y:
                pyautogui.moveTo(screen_x, screen_y)
                time.sleep(0.02)
            
            # 6. Verify the target color is still under/around the mouse
            if self.verify_color_at_mouse(bgr):
                # Click
                human_mouse.click()
                return True
            else:
                print(f"[!] Color mismatch at ({screen_x}, {screen_y}) on attempt {attempt+1}/{max_retries}.")
                if attempt < max_retries - 1:
                    print("[*] Target may have moved. Recapturing screen to track target...")
                    img, new_offset = self.capture_client_area()
                    if img is not None:
                        left_offset, top_offset = new_offset
                        new_contours = self.find_contours(img, color)
                        if new_contours:
                            # Convert current mouse coordinate to client offset
                            m_cx = screen_x - left_offset
                            m_cy = screen_y - top_offset
                            
                            # Find the contour that is closest to our cursor's target point
                            closest_dist = float('inf')
                            closest_contour = new_contours[0]
                            for c in new_contours:
                                M = cv2.moments(c)
                                if M["m00"] != 0:
                                    cx = int(M["m10"] / M["m00"])
                                    cy = int(M["m01"] / M["m00"])
                                else:
                                    bx, by, bw, bh = cv2.boundingRect(c)
                                    cx, cy = bx + bw//2, by + bh//2
                                    
                                dist = np.hypot(cx - m_cx, cy - m_cy)
                                if dist < closest_dist:
                                    closest_dist = dist
                                    closest_contour = c
                                    
                            current_contour = closest_contour
                            print(f"[+] Found updated target position. Dist to cursor: {closest_dist:.1f}px. Adjusting...")
                            continue
                    print("[-] Target lost. Could not find color on screen.")
                    break
                
        print("[!] Failed to click contour after max retries.")
        return False
        
    def count_contours(self, color, min_area=15):
        """
        Captures screen and counts the number of contours of the specified color.
        """
        img, _ = self.capture_client_area()
        if img is None:
            return 0
        contours = self.find_contours(img, color, min_area)
        return len(contours)
        
    def click_all_contours(self, color, min_area=15, delay_between_clicks=0.3):
        """
        Klickt alle aktuell sichtbaren Konturen einer Farbe nacheinander an.
        Nach jedem Klick wird der Bildschirm neu erfasst, um Änderungen zu erkennen.
        Gibt die Anzahl der erfolgreich geklickten Konturen zurück.
        """
        contours, offset = self.get_contours_on_screen(color, min_area)
        if not contours:
            print(f"[-] Keine Konturen der Farbe '{color}' gefunden.")
            return 0
        
        total = len(contours)
        print(f"[+] {total} Konturen der Farbe '{color}' gefunden. Klicke alle an...")
        
        clicked = 0
        for i, contour in enumerate(contours):
            print(f"[*] Klicke Kontur {i+1}/{total}...")
            success = self.click_contour(contour, color, offset)
            if success:
                clicked += 1
                print(f"[+] Kontur {i+1} erfolgreich geklickt.")
            else:
                print(f"[-] Kontur {i+1} fehlgeschlagen.")
            
            if delay_between_clicks > 0 and i < total - 1:
                self.sleep(delay_between_clicks)
        
        return clicked
        
    def get_contours_on_screen(self, color, min_area=15):
        """
        Returns a list of contours and the client offset.
        """
        img, offset = self.capture_client_area()
        if img is None:
            return [], (0, 0)
        contours = self.find_contours(img, color, min_area)
        return contours, offset
        
    def simulate_idle(self):
        """
        Simulates natural human idle behavior.
        Only runs if the mouse cursor is currently inside the RuneLite client window.
        - 2% chance to move the mouse to a random neutral spot inside the window.
        - 6% chance to perform a subtle micro-jitter (trembling/breathing).
        """
        rect = self.get_client_rect()
        if not rect:
            return
            
        left, top, right, bottom = rect
        x, y = pyautogui.position()
        
        # Only simulate idle if the mouse is currently inside the game window
        if not (left <= x <= right and top <= y <= bottom):
            return
            
        roll = random.random()
        
        if roll < 0.02:  # 2% chance per check to move to a neutral zone
            width = right - left
            height = bottom - top
            
            # Inner safe region to avoid hitting window borders or the minimap
            margin_w = int(width * 0.15)
            margin_h = int(height * 0.15)
            
            nx = random.randint(left + margin_w, right - margin_w)
            ny = random.randint(top + margin_h, bottom - margin_h)
            
            print(f"[*] Simuliere menschliche Untätigkeit: Maus wird in neutrale Zone bewegt...")
            human_mouse.move_to(nx, ny)
            
        elif roll < 0.08:  # 6% chance to perform subtle hand trembling
            jx = x + random.choice([-2, -1, 1, 2])
            jy = y + random.choice([-2, -1, 1, 2])
            
            # Keep cursor within window bounds
            if left <= jx <= right and top <= jy <= bottom:
                pyautogui.moveTo(jx, jy)

    def sleep(self, duration):
        """
        Custom sleep function that blocks for the given duration,
        but dynamically runs human idle behavior (jitter, neutral movements)
        instead of keeping the mouse completely frozen.
        """
        start_time = time.time()
        while time.time() - start_time < duration:
            self.simulate_idle()
            time.sleep(0.1)

    def wait_for_contour(self, color, min_area=15, timeout=30.0, check_interval=0.2):
        """
        Blocks and waits until at least one contour of the specified color appears.
        Simulates natural human idle behavior while waiting.
        Returns the list of contours and the client offset when found, or ([], (0,0)) on timeout.
        """
        start_time = time.time()
        print(f"[*] Waiting for '{color}' contour to appear...")
        while time.time() - start_time < timeout:
            contours, offset = self.get_contours_on_screen(color, min_area)
            if len(contours) > 0:
                print(f"[+] Found {len(contours)} contours of '{color}' after {time.time() - start_time:.2f}s.")
                return contours, offset
            
            # Run human idle simulation
            self.simulate_idle()
            time.sleep(check_interval)
            
        print(f"[-] Timeout: No '{color}' contour appeared within {timeout}s.")
        return [], (0, 0)
        
    def wait_for_contour_to_disappear(self, color, min_area=15, timeout=30.0, check_interval=0.2):
        """
        Blocks and waits until all contours of the specified color disappear.
        Simulates natural human idle behavior while waiting.
        Returns True if they disappeared, False on timeout.
        """
        start_time = time.time()
        print(f"[*] Waiting for all '{color}' contours to disappear...")
        while time.time() - start_time < timeout:
            contours, _ = self.get_contours_on_screen(color, min_area)
            if len(contours) == 0:
                print(f"[+] All '{color}' contours disappeared after {time.time() - start_time:.2f}s.")
                return True
                
            # Run human idle simulation
            self.simulate_idle()
            time.sleep(check_interval)
            
        print(f"[-] Timeout: '{color}' contours did not disappear within {timeout}s.")
        return False


# ==============================================================================
# 4. BEGINNER-FRIENDLY GLOBAL FUNCTIONS
# ==============================================================================
_manager = None

def start(window_title="RuneLite"):
    """
    Sucht das RuneLite-Fenster, bringt es in den Vordergrund und initialisiert die API.
    Muss einmal am Anfang aufgerufen werden.
    Gibt True zurück, wenn das Fenster gefunden und fokussiert wurde.
    """
    global _manager
    _manager = ContourManager(window_title=window_title)
    success = _manager.focus_window()
    if success:
        print(f"[+] OSRS-API erfolgreich gestartet für Fenster: '{window_title}'")
    else:
        print(f"[!] OSRS-API Warnung: Fenster '{window_title}' konnte nicht fokussiert werden.")
    return success

def click(color, index=0):
    """
    Sucht nach allen Konturen der angegebenen Farbe und klickt auf die Kontur
    am gewünschten Index (Standard: 0 = die erste gefundene Kontur).
    Gibt True zurück bei erfolgreichem Klick, andernfalls False.
    """
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    contours, offset = _manager.get_contours_on_screen(color)
    if contours and len(contours) > index:
        return _manager.click_contour(contours[index], color, offset)
    return False

def click_random(color):
    """
    Sucht nach allen Konturen der angegebenen Farbe und klickt auf eine zufällig ausgewählte Kontur.
    Gibt True zurück bei erfolgreichem Klick, andernfalls False.
    """
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    contours, offset = _manager.get_contours_on_screen(color)
    if contours:
        cnt = random.choice(contours)
        return _manager.click_contour(cnt, color, offset)
    return False

def click_all(color, delay_between_clicks=0.3):
    """
    Klickt alle aktuell sichtbaren Konturen einer Farbe nacheinander an.
    Gibt die Anzahl der erfolgreich geklickten Konturen zurück.
    """
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return 0
    return _manager.click_all_contours(color, delay_between_clicks=delay_between_clicks)

def count(color):
    """
    Gibt die Anzahl der aktuell auf dem Bildschirm sichtbaren Konturen dieser Farbe zurück.
    """
    if _manager is None:
        return 0
    return _manager.count_contours(color)

def wait_for(color, timeout=30.0):
    """
    Wartet, bis mindestens eine Kontur dieser Farbe auf dem Bildschirm erscheint.
    Simuliert während des Wartens natürliches Mausverhalten.
    Gibt True zurück, wenn sie erschienen ist, andernfalls False bei Timeout.
    """
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    contours, _ = _manager.wait_for_contour(color, timeout=timeout)
    return len(contours) > 0

def wait_for_disappear(color, timeout=30.0):
    """
    Wartet, bis alle Konturen dieser Farbe vom Bildschirm verschwinden.
    Simuliert während des Wartens natürliches Mausverhalten.
    Gibt True zurück, wenn alle verschwunden sind, andernfalls False bei Timeout.
    """
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    return _manager.wait_for_contour_to_disappear(color, timeout=timeout)

def sleep(duration):
    """
    Pausiert das Skript für die angegebene Dauer (in Sekunden).
    Simuliert während des Wartens natürliche menschliche Mikro-Mausbewegungen (Zittern, Atmen),
    anstatt den Cursor komplett einzufrieren.
    """
    if _manager is not None:
        _manager.sleep(duration)
    else:
        time.sleep(duration)
