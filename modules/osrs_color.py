import time
import random
import cv2
import numpy as np
from PIL import ImageGrab
import pyautogui

from . import human_mouse
from .window_client import WindowClient

# ==============================================================================
# ContourManager
# ==============================================================================
class ContourManager:
    """
    Erkennt farbige Konturen im RuneLite-Client und klickt sie menschlich an.
    """

    # BGR – 7 Farben: je Kanal nur 0 oder 255, insgesamt 1–3 Kanäle mit 255
    COLOR_MAP = {
        "red": [0, 0, 255],
        "green": [0, 255, 0],
        "blue": [255, 0, 0],
        "yellow": [0, 255, 255],
        "cyan": [255, 255, 0],
        "pink": [255, 0, 255],
        "white": [255, 255, 255],
    }

    def __init__(self, client=None, window_title="RuneLite"):
        self._client = client or WindowClient(window_title=window_title)

    def focus_window(self):
        return self._client.focus_window()

    def find_window(self):
        return self._client.find_window()

    def get_client_rect(self):
        return self._client.get_client_rect()

    def capture_client_area(self):
        return self._client.capture_client_area()

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
            diffs = np.linalg.norm(img_np - target_rgb, axis=2)
            return bool(np.any(diffs <= tolerance))
        except Exception as e:
            print(f"[!] Error verifying color at mouse: {e}")
            return False
            
    def click_contour(self, contour, color, client_offset, max_retries=5, fast_mode=False):
        """
        Clicks a random point inside the contour.
        Moves mouse, verifies color, and clicks.
        Supports dynamic tracking: If validation fails, it recaptures the screen to find the target's new position.
        If fast_mode=True, uses minimal delays and skips verification for rapid clicking.
        Returns True if clicked successfully, False otherwise.
        """
        bgr = self._get_color_bgr(color)
        left_offset, top_offset = client_offset
        current_contour = contour
        
        for attempt in range(max_retries if not fast_mode else 1):
            rx, ry = self.get_random_point_in_contour(current_contour, border_margin=3)
            screen_x = rx + left_offset
            screen_y = ry + top_offset
            
            if fast_mode:
                human_mouse.fast_move_to(screen_x, screen_y)
                human_mouse.fast_click()
                return True
            else:
                human_mouse.move_to(screen_x, screen_y)
                time.sleep(random.uniform(0.08, 0.15))
                
                cur_x, cur_y = pyautogui.position()
                if cur_x != screen_x or cur_y != screen_y:
                    pyautogui.moveTo(screen_x, screen_y)
                    time.sleep(0.02)
                
                if self.verify_color_at_mouse(bgr):
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
                                m_cx = screen_x - left_offset
                                m_cy = screen_y - top_offset
                                
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
                    
        if not fast_mode:
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
        
    def click_all_contours(self, color, min_area=15, delay_between_clicks=0.0):
        """
        Klickt alle beim Start sichtbaren Konturen nacheinander an (eine Erkennung, dann Fast-Mode).
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
            if self.click_contour(contour, color, offset, fast_mode=True):
                clicked += 1
            else:
                print(f"[-] Kontur {i+1} fehlgeschlagen.")
            if delay_between_clicks > 0 and i < total - 1:
                time.sleep(delay_between_clicks)

        print(f"[+] {clicked}/{total} Konturen erfolgreich geklickt.")
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

    def wait_for_contour(self, color, min_area=15, timeout=30.0, check_interval=0.2):
        """
        Blocks and waits until at least one contour of the specified color appears.
        Returns the list of contours and the client offset when found, or ([], (0,0)) on timeout.
        """
        start_time = time.time()
        print(f"[*] Waiting for '{color}' contour to appear...")
        while time.time() - start_time < timeout:
            contours, offset = self.get_contours_on_screen(color, min_area)
            if len(contours) > 0:
                print(f"[+] Found {len(contours)} contours of '{color}' after {time.time() - start_time:.2f}s.")
                return contours, offset

            time.sleep(check_interval)
            
        print(f"[-] Timeout: No '{color}' contour appeared within {timeout}s.")
        return [], (0, 0)
        
    def wait_for_contour_to_disappear(self, color, min_area=15, timeout=30.0, check_interval=0.2):
        """
        Blocks and waits until all contours of the specified color disappear.
        Returns True if they disappeared, False on timeout.
        """
        start_time = time.time()
        print(f"[*] Waiting for all '{color}' contours to disappear...")
        while time.time() - start_time < timeout:
            contours, _ = self.get_contours_on_screen(color, min_area)
            if len(contours) == 0:
                print(f"[+] All '{color}' contours disappeared after {time.time() - start_time:.2f}s.")
                return True

            time.sleep(check_interval)
            
        print(f"[-] Timeout: '{color}' contours did not disappear within {timeout}s.")
        return False


# ==============================================================================
# 4. BEGINNER-FRIENDLY GLOBAL FUNCTIONS
# ==============================================================================
_manager = None


def _get_manager():
    global _manager
    from . import osrs_session
    from .api_helpers import require_manager

    _manager = require_manager(osrs_session.get_contour_manager)
    return _manager


def start(window_title="RuneLite", tesseract_cmd=None):
    """
    Startet die gemeinsame OSRS-Session (Fenster) und bindet die Kontur-API.
    tesseract_cmd wird für spätere OCR-Nutzung in derselben Session gespeichert.
    """
    global _manager
    from . import osrs_session

    success = osrs_session.start(window_title, tesseract_cmd=tesseract_cmd)
    _manager = _get_manager()
    return success

def click(color, index=0):
    """
    Sucht nach allen Konturen der angegebenen Farbe und klickt auf die Kontur
    am gewünschten Index (Standard: 0 = die erste gefundene Kontur).
    Gibt True zurück bei erfolgreichem Klick, andernfalls False.
    """
    mgr = _get_manager()
    if mgr is None:
        return False
    contours, offset = mgr.get_contours_on_screen(color)
    if contours and len(contours) > index:
        return mgr.click_contour(contours[index], color, offset)
    return False

def click_random(color):
    """
    Sucht nach allen Konturen der angegebenen Farbe und klickt auf eine zufällig ausgewählte Kontur.
    Gibt True zurück bei erfolgreichem Klick, andernfalls False.
    """
    mgr = _get_manager()
    if mgr is None:
        return False
    contours, offset = mgr.get_contours_on_screen(color)
    if contours:
        cnt = random.choice(contours)
        return mgr.click_contour(cnt, color, offset)
    return False

def click_all(color, delay_between_clicks=0.0):
    """
    Klickt alle aktuell sichtbaren Konturen einer Farbe nacheinander an.
    Verwendet Fast-Mode für ~3-4 Klicks pro Sekunde.
    Gibt die Anzahl der erfolgreich geklickten Konturen zurück.
    """
    mgr = _get_manager()
    if mgr is None:
        return 0
    return mgr.click_all_contours(color, delay_between_clicks=delay_between_clicks)

def count(color):
    """
    Gibt die Anzahl der aktuell auf dem Bildschirm sichtbaren Konturen dieser Farbe zurück.
    """
    mgr = _get_manager()
    if mgr is None:
        return 0
    return mgr.count_contours(color)

def wait_for(color, timeout=30.0):
    """
    Wartet, bis mindestens eine Kontur dieser Farbe auf dem Bildschirm erscheint.
    Gibt True zurück, wenn sie erschienen ist, andernfalls False bei Timeout.
    """
    mgr = _get_manager()
    if mgr is None:
        return False
    contours, _ = mgr.wait_for_contour(color, timeout=timeout)
    return len(contours) > 0

def wait_for_disappear(color, timeout=30.0):
    """
    Wartet, bis alle Konturen dieser Farbe vom Bildschirm verschwinden.
    Gibt True zurück, wenn alle verschwunden sind, andernfalls False bei Timeout.
    """
    mgr = _get_manager()
    if mgr is None:
        return False
    return mgr.wait_for_contour_to_disappear(color, timeout=timeout)


