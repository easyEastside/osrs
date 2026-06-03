"""
OCR-Textsuche im RuneLite-Client (Tesseract).
Nutzt ContourManager für Fensterfokus, Screenshot und Idle-Simulation.

Tesseract muss installiert sein:
  Windows: https://github.com/UB-Mannheim/tesseract/wiki
  Optional: Umgebungsvariable TESSERACT_CMD auf tesseract.exe setzen.
"""
import os
import platform
import time
import random
import cv2
import numpy as np
from PIL import ImageGrab
import pyautogui

from . import human_mouse
from .osrs_api import ContourManager

try:
    import pytesseract
    from pytesseract import Output as TesseractOutput
except ImportError:
    pytesseract = None
    TesseractOutput = None

IS_WINDOWS = platform.system() == "Windows"


class OcrManager:
    """
    Erkennt Text im Client-Bereich und klickt Treffer mit menschlicher Mausbewegung an.
    """

    def __init__(self, client=None, window_title="RuneLite", tesseract_cmd=None):
        self._client = client or ContourManager(window_title=window_title)
        self._scale = 2
        self._tesseract_config = "--psm 6"
        self._configure_tesseract(tesseract_cmd)

    def _configure_tesseract(self, tesseract_cmd=None):
        if pytesseract is None:
            raise ImportError(
                "pytesseract ist nicht installiert. Bitte ausführen: pip install pytesseract"
            )
        cmd = tesseract_cmd or os.environ.get("TESSERACT_CMD")
        if cmd and os.path.isfile(cmd):
            pytesseract.pytesseract.tesseract_cmd = cmd
            return
        if IS_WINDOWS:
            candidates = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for path in candidates:
                if os.path.isfile(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    return

    def focus_window(self):
        return self._client.focus_window()

    @staticmethod
    def _text_matches(detected, query, partial=True, case_sensitive=False):
        if not case_sensitive:
            detected, query = detected.lower(), query.lower()
        if partial:
            return query in detected
        return detected == query

    def _prepare_for_ocr(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        scale = self._scale
        if scale != 1:
            gray = cv2.resize(
                gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
            )
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return binary, scale

    def _ocr_entries(self, img, region=None, min_conf=60):
        if img is None:
            return []

        offset_x, offset_y = 0, 0
        work = img
        if region is not None:
            rx, ry, rw, rh = region
            work = img[ry : ry + rh, rx : rx + rw]
            offset_x, offset_y = rx, ry

        prepared, scale = self._prepare_for_ocr(work)
        try:
            data = pytesseract.image_to_data(
                prepared,
                output_type=TesseractOutput.DICT,
                config=self._tesseract_config,
            )
        except pytesseract.TesseractNotFoundError:
            raise RuntimeError(
                "Tesseract wurde nicht gefunden. Installiere Tesseract OCR oder setze "
                "TESSERACT_CMD auf den Pfad zu tesseract.exe."
            ) from None

        entries = []
        n = len(data["text"])
        for i in range(n):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1.0
            if conf < min_conf:
                continue

            x = int(data["left"][i] / scale) + offset_x
            y = int(data["top"][i] / scale) + offset_y
            w = max(1, int(data["width"][i] / scale))
            h = max(1, int(data["height"][i] / scale))
            entries.append(
                {
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "text": text,
                    "conf": conf,
                }
            )
        return entries

    def find_text(
        self,
        img,
        query,
        min_conf=60,
        partial=True,
        case_sensitive=False,
        region=None,
    ):
        """
        Findet Text-Vorkommen in img.
        Returns: Liste von {x, y, w, h, text, conf}.
        """
        entries = self._ocr_entries(img, region=region, min_conf=min_conf)
        matches = [
            e
            for e in entries
            if self._text_matches(e["text"], query, partial, case_sensitive)
        ]
        matches.sort(key=lambda m: m["conf"], reverse=True)
        return matches

    def get_text_on_screen(
        self,
        query,
        min_conf=60,
        partial=True,
        case_sensitive=False,
        region=None,
    ):
        img, offset = self._client.capture_client_area()
        if img is None:
            return [], (0, 0)
        return (
            self.find_text(
                img,
                query,
                min_conf=min_conf,
                partial=partial,
                case_sensitive=case_sensitive,
                region=region,
            ),
            offset,
        )

    def read_screen(self, min_conf=60, region=None):
        """Liest allen erkannten Text im Client (oder in region)."""
        img, _ = self._client.capture_client_area()
        if img is None:
            return []
        entries = self._ocr_entries(img, region=region, min_conf=min_conf)
        return [e["text"] for e in entries]

    def get_random_point_in_match(self, match, border_margin=2):
        x, y, w, h = match["x"], match["y"], match["w"], match["h"]
        margin = min(border_margin, max(0, w // 2 - 1), max(0, h // 2 - 1))
        if w > 2 * margin and h > 2 * margin:
            rx = random.randint(x + margin, x + w - 1 - margin)
            ry = random.randint(y + margin, y + h - 1 - margin)
            return rx, ry
        return x + w // 2, y + h // 2

    def verify_text_at_mouse(
        self,
        query,
        min_conf=55,
        partial=True,
        case_sensitive=False,
        neighborhood_scale=2.5,
    ):
        x, y = pyautogui.position()
        pad = 40
        bbox = (x - pad, y - pad, x + pad, y + pad)
        try:
            shot = ImageGrab.grab(bbox=bbox)
            region = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
            matches = self.find_text(
                region,
                query,
                min_conf=min_conf,
                partial=partial,
                case_sensitive=case_sensitive,
            )
            return len(matches) > 0
        except Exception as e:
            print(f"[!] Error verifying text at mouse: {e}")
            return False

    def click_text(
        self,
        match,
        query,
        client_offset,
        max_retries=5,
        fast_mode=False,
        min_conf=60,
        partial=True,
        case_sensitive=False,
        region=None,
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

            if self.verify_text_at_mouse(
                query,
                min_conf=min_conf - 5,
                partial=partial,
                case_sensitive=case_sensitive,
            ):
                human_mouse.click()
                return True

            print(
                f"[!] Text '{query}' nicht unter Maus ({screen_x}, {screen_y}) "
                f"– Versuch {attempt+1}/{max_retries}."
            )
            if attempt < max_retries - 1:
                print("[*] Ziel evtl. verschoben. Neuer Screenshot...")
                img, new_offset = self._client.capture_client_area()
                if img is not None:
                    left_offset, top_offset = new_offset
                    new_matches = self.find_text(
                        img,
                        query,
                        min_conf=min_conf,
                        partial=partial,
                        case_sensitive=case_sensitive,
                        region=region,
                    )
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
                        print("[+] Text-Position aktualisiert.")
                        continue
                print("[-] Text nicht mehr gefunden.")
                break

        if not fast_mode:
            print(f"[!] Klick auf Text '{query}' nach max. Versuchen fehlgeschlagen.")
        return False

    def count_text(
        self,
        query,
        min_conf=60,
        partial=True,
        case_sensitive=False,
        region=None,
    ):
        img, _ = self._client.capture_client_area()
        if img is None:
            return 0
        return len(
            self.find_text(
                img,
                query,
                min_conf=min_conf,
                partial=partial,
                case_sensitive=case_sensitive,
                region=region,
            )
        )

    def click_all_text(
        self,
        query,
        min_conf=60,
        partial=True,
        case_sensitive=False,
        region=None,
        delay_between_clicks=0.0,
    ):
        matches, offset = self.get_text_on_screen(
            query,
            min_conf=min_conf,
            partial=partial,
            case_sensitive=case_sensitive,
            region=region,
        )
        if not matches:
            print(f"[-] Text '{query}' nicht gefunden.")
            return 0

        total = len(matches)
        print(f"[+] {total} Text-Treffer für '{query}'. Klicke alle an...")

        clicked = 0
        for i, match in enumerate(matches):
            print(f"[*] Klicke Treffer {i+1}/{total} ('{match['text']}')...")
            if self.click_text(
                match,
                query,
                offset,
                fast_mode=True,
                min_conf=min_conf,
                partial=partial,
                case_sensitive=case_sensitive,
                region=region,
            ):
                clicked += 1
            else:
                print(f"[-] Treffer {i+1} fehlgeschlagen.")
            if delay_between_clicks > 0 and i < total - 1:
                time.sleep(delay_between_clicks)

        print(f"[+] {clicked}/{total} Text-Treffer geklickt.")
        return clicked

    def wait_for_text(
        self,
        query,
        min_conf=60,
        partial=True,
        case_sensitive=False,
        region=None,
        timeout=30.0,
        check_interval=0.5,
    ):
        start_time = time.time()
        print(f"[*] Warte auf Text '{query}'...")
        while time.time() - start_time < timeout:
            matches, offset = self.get_text_on_screen(
                query,
                min_conf=min_conf,
                partial=partial,
                case_sensitive=case_sensitive,
                region=region,
            )
            if matches:
                print(
                    f"[+] {len(matches)} Treffer für '{query}' nach "
                    f"{time.time() - start_time:.2f}s."
                )
                return matches, offset
            self._client.simulate_idle()
            time.sleep(check_interval)

        print(f"[-] Timeout: Text '{query}' nicht innerhalb von {timeout}s erschienen.")
        return [], (0, 0)

    def wait_for_text_to_disappear(
        self,
        query,
        min_conf=60,
        partial=True,
        case_sensitive=False,
        region=None,
        timeout=30.0,
        check_interval=0.5,
    ):
        start_time = time.time()
        print(f"[*] Warte bis Text '{query}' verschwindet...")
        while time.time() - start_time < timeout:
            matches, _ = self.get_text_on_screen(
                query,
                min_conf=min_conf,
                partial=partial,
                case_sensitive=case_sensitive,
                region=region,
            )
            if not matches:
                print(
                    f"[+] Text '{query}' weg nach {time.time() - start_time:.2f}s."
                )
                return True
            self._client.simulate_idle()
            time.sleep(check_interval)

        print(f"[-] Timeout: Text '{query}' noch nach {timeout}s sichtbar.")
        return False


# ==============================================================================
# Beginner-friendly global functions
# ==============================================================================
_manager = None


def start(window_title="RuneLite", tesseract_cmd=None):
    """Initialisiert Fensterfokus für OCR. Einmal am Anfang aufrufen."""
    global _manager
    if _manager is not None:
        print("[*] OCR-API läuft bereits. Überspringe Initialisierung.")
        return _manager.focus_window()
    _manager = OcrManager(window_title=window_title, tesseract_cmd=tesseract_cmd)
    success = _manager.focus_window()
    if success:
        print(f"[+] OCR-API gestartet für Fenster: '{window_title}'")
    else:
        print(f"[!] OCR-API Warnung: Fenster '{window_title}' konnte nicht fokussiert werden.")
    return success


def click(
    text,
    index=0,
    min_conf=60,
    partial=True,
    case_sensitive=False,
    region=None,
):
    """Klickt den Text-Treffer am Index (0 = bester Treffer)."""
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    matches, offset = _manager.get_text_on_screen(
        text,
        min_conf=min_conf,
        partial=partial,
        case_sensitive=case_sensitive,
        region=region,
    )
    if matches and len(matches) > index:
        return _manager.click_text(
            matches[index],
            text,
            offset,
            min_conf=min_conf,
            partial=partial,
            case_sensitive=case_sensitive,
            region=region,
        )
    return False


def click_random(
    text,
    min_conf=60,
    partial=True,
    case_sensitive=False,
    region=None,
):
    """Klickt einen zufälligen Text-Treffer."""
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    matches, offset = _manager.get_text_on_screen(
        text,
        min_conf=min_conf,
        partial=partial,
        case_sensitive=case_sensitive,
        region=region,
    )
    if matches:
        m = random.choice(matches)
        return _manager.click_text(
            m,
            text,
            offset,
            min_conf=min_conf,
            partial=partial,
            case_sensitive=case_sensitive,
            region=region,
        )
    return False


def click_all(
    text,
    delay_between_clicks=0.0,
    min_conf=60,
    partial=True,
    case_sensitive=False,
    region=None,
):
    """Klickt alle sichtbaren Text-Treffer (Fast-Mode)."""
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return 0
    return _manager.click_all_text(
        text,
        min_conf=min_conf,
        partial=partial,
        case_sensitive=case_sensitive,
        region=region,
        delay_between_clicks=delay_between_clicks,
    )


def count(
    text,
    min_conf=60,
    partial=True,
    case_sensitive=False,
    region=None,
):
    """Anzahl sichtbarer Text-Treffer."""
    if _manager is None:
        return 0
    return _manager.count_text(
        text,
        min_conf=min_conf,
        partial=partial,
        case_sensitive=case_sensitive,
        region=region,
    )


def wait_for(
    text,
    timeout=30.0,
    min_conf=60,
    partial=True,
    case_sensitive=False,
    region=None,
):
    """Wartet bis mindestens ein Treffer erscheint."""
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    matches, _ = _manager.wait_for_text(
        text,
        min_conf=min_conf,
        partial=partial,
        case_sensitive=case_sensitive,
        region=region,
        timeout=timeout,
    )
    return len(matches) > 0


def wait_for_disappear(
    text,
    timeout=30.0,
    min_conf=60,
    partial=True,
    case_sensitive=False,
    region=None,
):
    """Wartet bis alle Treffer verschwunden sind."""
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return False
    return _manager.wait_for_text_to_disappear(
        text,
        min_conf=min_conf,
        partial=partial,
        case_sensitive=case_sensitive,
        region=region,
        timeout=timeout,
    )


def wait_till_gone(
    text,
    timeout=30.0,
    min_conf=60,
    partial=True,
    case_sensitive=False,
    region=None,
):
    """Alias für wait_for_disappear."""
    return wait_for_disappear(
        text,
        timeout=timeout,
        min_conf=min_conf,
        partial=partial,
        case_sensitive=case_sensitive,
        region=region,
    )


def read(min_conf=60, region=None):
    """Liest allen erkannten Text im Client (Liste von Strings)."""
    if _manager is None:
        print("[!] Fehler: Bitte rufe zuerst 'start()' auf.")
        return []
    return _manager.read_screen(min_conf=min_conf, region=region)
