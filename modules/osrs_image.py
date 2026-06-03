"""
Template-Bilderkennung für den RuneLite-Client.
"""
import os
import time
import random
import cv2
import numpy as np
from PIL import ImageGrab
import pyautogui

from . import human_mouse
from .window_client import WindowClient


class ImageManager:
    """
    Findet Template-Bilder im Client-Bereich und klickt sie mit menschlicher Mausbewegung an.
    """

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def __init__(self, client=None, window_title="RuneLite"):
        self._client = client or WindowClient(window_title=window_title)
        self._template_cache = {}

    def focus_window(self):
        return self._client.focus_window()

    def _resolve_template_path(self, template_path):
        if os.path.isabs(template_path) and os.path.isfile(template_path):
            return os.path.abspath(template_path)

        module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            template_path,
            os.path.join(os.getcwd(), template_path),
            os.path.join(module_root, template_path),
            os.path.join(module_root, "images", template_path),
            os.path.join(module_root, "images", os.path.basename(template_path)),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return os.path.abspath(path)
        raise FileNotFoundError(
            f"Template image not found: '{template_path}'. "
            f"Tried: {', '.join(candidates)}"
        )

    def _load_template(self, template_path):
        path = self._resolve_template_path(template_path)
        if path not in self._template_cache:
            tpl = cv2.imread(path, cv2.IMREAD_COLOR)
            if tpl is None:
                raise ValueError(f"Could not load template image: {path}")
            self._template_cache[path] = tpl
        return self._template_cache[path]

    def find_images(self, img, template_path, threshold=0.8):
        """
        Findet alle Vorkommen von template_path in img.
        Returns: Liste von {x, y, w, h, score} (Client-Koordinaten).
        """
        template = self._load_template(template_path)
        th, tw = template.shape[:2]
        if img is None or img.shape[0] < th or img.shape[1] < tw:
            return []

        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        matches = []
        work = result.copy()

        while True:
            _, max_val, _, max_loc = cv2.minMaxLoc(work)
            if max_val < threshold:
                break
            x, y = max_loc
            matches.append({"x": x, "y": y, "w": tw, "h": th, "score": float(max_val)})
            x1 = max(0, x - tw // 2)
            y1 = max(0, y - th // 2)
            x2 = min(work.shape[1], x + tw // 2 + 1)
            y2 = min(work.shape[0], y + th // 2 + 1)
            work[y1:y2, x1:x2] = 0

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    def get_images_on_screen(self, template_path, threshold=0.8):
        img, offset = self._client.capture_client_area()
        if img is None:
            return [], (0, 0)
        return self.find_images(img, template_path, threshold), offset

    def get_random_point_in_match(self, match, border_margin=2):
        x, y, w, h = match["x"], match["y"], match["w"], match["h"]
        margin = min(border_margin, max(0, w // 2 - 1), max(0, h // 2 - 1))
        if w > 2 * margin and h > 2 * margin:
            rx = random.randint(x + margin, x + w - 1 - margin)
            ry = random.randint(y + margin, y + h - 1 - margin)
            return rx, ry
        return x + w // 2, y + h // 2

    def verify_image_at_mouse(self, template_path, threshold=0.75, neighborhood_scale=1.5):
        template = self._load_template(template_path)
        th, tw = template.shape[:2]
        x, y = pyautogui.position()
        pad_x = int(tw * neighborhood_scale)
        pad_y = int(th * neighborhood_scale)
        bbox = (x - pad_x, y - pad_y, x + pad_x, y + pad_y)
        try:
            shot = ImageGrab.grab(bbox=bbox)
            region = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
            if region.shape[0] < th or region.shape[1] < tw:
                return False
            result = cv2.matchTemplate(region, template, cv2.TM_CCOEFF_NORMED)
            return bool(np.max(result) >= threshold)
        except Exception as e:
            print(f"[!] Error verifying image at mouse: {e}")
            return False

    def click_image(
        self, match, template_path, client_offset, max_retries=5, fast_mode=False, threshold=0.8
    ):
        left_offset, top_offset = client_offset
        current_match = match

        for attempt in range(max_retries if not fast_mode else 1):
            rx, ry = self.get_random_point_in_match(current_match)
            screen_x = rx + left_offset
            screen_y = ry + top_offset

            if fast_mode:
                human_mouse.fast_move_to(screen_x, screen_y)
                human_mouse.fast_click()
                return True

            human_mouse.move_to(screen_x, screen_y)
            time.sleep(random.uniform(0.08, 0.15))

            cur_x, cur_y = pyautogui.position()
            if cur_x != screen_x or cur_y != screen_y:
                pyautogui.moveTo(screen_x, screen_y)
                time.sleep(0.02)

            if self.verify_image_at_mouse(template_path, threshold=threshold * 0.95):
                human_mouse.click()
                return True

            print(
                f"[!] Image mismatch at ({screen_x}, {screen_y}) "
                f"on attempt {attempt+1}/{max_retries}."
            )
            if attempt < max_retries - 1:
                print("[*] Target may have moved. Recapturing screen to track target...")
                img, new_offset = self._client.capture_client_area()
                if img is not None:
                    left_offset, top_offset = new_offset
                    new_matches = self.find_images(img, template_path, threshold)
                    if new_matches:
                        m_x = screen_x - left_offset
                        m_y = screen_y - top_offset
                        current_match = min(
                            new_matches,
                            key=lambda m: np.hypot(
                                m["x"] + m["w"] // 2 - m_x,
                                m["y"] + m["h"] // 2 - m_y,
                            ),
                        )
                        print("[+] Found updated template position. Adjusting...")
                        continue
                print("[-] Target lost. Could not find template on screen.")
                break

        if not fast_mode:
            print("[!] Failed to click image after max retries.")
        return False

    def count_images(self, template_path, threshold=0.8):
        img, _ = self._client.capture_client_area()
        if img is None:
            return 0
        return len(self.find_images(img, template_path, threshold))

    def click_all_images(self, template_path, threshold=0.8, delay_between_clicks=0.0):
        matches, offset = self.get_images_on_screen(template_path, threshold)
        if not matches:
            print(f"[-] Kein Bild '{template_path}' gefunden.")
            return 0

        total = len(matches)
        print(f"[+] {total} Vorkommen von '{template_path}' gefunden. Klicke alle an...")

        clicked = 0
        for i, match in enumerate(matches):
            print(f"[*] Klicke Bild {i+1}/{total}...")
            if self.click_image(match, template_path, offset, fast_mode=True, threshold=threshold):
                clicked += 1
            else:
                print(f"[-] Bild {i+1} fehlgeschlagen.")
            if delay_between_clicks > 0 and i < total - 1:
                time.sleep(delay_between_clicks)

        print(f"[+] {clicked}/{total} Bilder erfolgreich geklickt.")
        return clicked

    def wait_for_image(self, template_path, threshold=0.8, timeout=30.0, check_interval=0.2):
        start_time = time.time()
        print(f"[*] Waiting for image '{template_path}' to appear...")
        while time.time() - start_time < timeout:
            matches, offset = self.get_images_on_screen(template_path, threshold)
            if matches:
                print(
                    f"[+] Found {len(matches)} match(es) for '{template_path}' "
                    f"after {time.time() - start_time:.2f}s."
                )
                return matches, offset
            time.sleep(check_interval)

        print(f"[-] Timeout: '{template_path}' did not appear within {timeout}s.")
        return [], (0, 0)

    def wait_for_image_to_disappear(
        self, template_path, threshold=0.8, timeout=30.0, check_interval=0.2
    ):
        start_time = time.time()
        print(f"[*] Waiting for all '{template_path}' images to disappear...")
        while time.time() - start_time < timeout:
            matches, _ = self.get_images_on_screen(template_path, threshold)
            if not matches:
                print(
                    f"[+] All '{template_path}' images disappeared "
                    f"after {time.time() - start_time:.2f}s."
                )
                return True
            time.sleep(check_interval)

        print(f"[-] Timeout: '{template_path}' did not disappear within {timeout}s.")
        return False


# ==============================================================================
# Beginner-friendly global functions
# ==============================================================================
_manager = None


def _get_manager():
    global _manager
    from . import osrs_session
    from .api_helpers import require_manager

    _manager = require_manager(osrs_session.get_image_manager)
    return _manager


def start(window_title="RuneLite", tesseract_cmd=None):
    """Startet die gemeinsame Session und bindet die Bild-API."""
    global _manager
    from . import osrs_session

    success = osrs_session.start(window_title, tesseract_cmd=tesseract_cmd)
    _manager = _get_manager()
    return success


def click(template, index=0, threshold=0.8):
    """Klickt das Template am Index (Standard: 0 = bestes Match)."""
    mgr = _get_manager()
    if mgr is None:
        return False
    matches, offset = mgr.get_images_on_screen(template, threshold)
    if matches and len(matches) > index:
        return mgr.click_image(matches[index], template, offset, threshold=threshold)
    return False


def click_random(template, threshold=0.8):
    """Klickt ein zufällig gewähltes Template-Vorkommen."""
    mgr = _get_manager()
    if mgr is None:
        return False
    matches, offset = mgr.get_images_on_screen(template, threshold)
    if matches:
        m = random.choice(matches)
        return mgr.click_image(m, template, offset, threshold=threshold)
    return False


def click_all(template, delay_between_clicks=0.0, threshold=0.8):
    """Klickt alle sichtbaren Vorkommen (Fast-Mode). Gibt Anzahl Klicks zurück."""
    mgr = _get_manager()
    if mgr is None:
        return 0
    return mgr.click_all_images(
        template, threshold=threshold, delay_between_clicks=delay_between_clicks
    )


def count(template, threshold=0.8):
    """Anzahl sichtbarer Template-Vorkommen."""
    mgr = _get_manager()
    if mgr is None:
        return 0
    return mgr.count_images(template, threshold)


def wait_for(template, timeout=30.0, threshold=0.8):
    """Wartet bis mindestens ein Vorkommen erscheint. True bei Erfolg."""
    mgr = _get_manager()
    if mgr is None:
        return False
    matches, _ = mgr.wait_for_image(template, threshold=threshold, timeout=timeout)
    return len(matches) > 0


def wait_for_disappear(template, timeout=30.0, threshold=0.8):
    """Wartet bis alle Vorkommen verschwunden sind."""
    mgr = _get_manager()
    if mgr is None:
        return False
    return mgr.wait_for_image_to_disappear(template, threshold=threshold, timeout=timeout)


def wait_till_gone(template, timeout=30.0, threshold=0.8):
    """Alias für wait_for_disappear."""
    return wait_for_disappear(template, timeout=timeout, threshold=threshold)
