"""
Gemeinsame Session: ein Fenster, ein start() für Konturen, Bilder und OCR.
"""
from .window_client import WindowClient

_window = None
_ready = False
_tesseract_cmd = None
_contour_manager = None
_image_manager = None
_ocr_manager = None


def is_started():
    """True nur wenn start() das Fenster gefunden hat."""
    return _window is not None and _ready


def get_window():
    return _window


def start(window_title="RuneLite", tesseract_cmd=None, focus=True):
    """
    Initialisiert das Spiel-Fenster (einmalig) und fokussiert es.
    Kontur-, Bild- und OCR-Module teilen sich dieselbe WindowClient-Instanz.

    Gibt True zurück, wenn das Fenster gefunden (und ggf. fokussiert) wurde.
    """
    global _window, _ready, _tesseract_cmd
    global _contour_manager, _image_manager, _ocr_manager

    if tesseract_cmd is not None:
        if tesseract_cmd != _tesseract_cmd:
            _ocr_manager = None
            from . import osrs_ocr

            osrs_ocr._manager = None
        _tesseract_cmd = tesseract_cmd

    was_started = is_started()
    title_changed = _window is not None and _window.window_title != window_title

    if _window is None:
        _window = WindowClient(window_title)
    elif title_changed:
        _window.window_title = window_title
        _contour_manager = None
        _image_manager = None
        _ocr_manager = None

    if _window.find_window() is None:
        success = False
        _ready = False
        if not was_started:
            _window = None
    elif focus:
        success = _window.focus_window()
        _ready = success
    else:
        success = True
        _ready = True

    if success and (not was_started or title_changed):
        print(f"[+] OSRS-Session aktiv: '{window_title}'")
    elif not success:
        print(f"[!] OSRS-Session Warnung: Fenster '{window_title}' nicht gefunden/fokussiert.")

    return success


def reset():
    """Setzt die Session zurück (z. B. für Tests oder Fensterwechsel)."""
    global _window, _ready, _tesseract_cmd
    global _contour_manager, _image_manager, _ocr_manager
    _window = None
    _ready = False
    _tesseract_cmd = None
    _contour_manager = None
    _image_manager = None
    _ocr_manager = None
    _clear_module_managers()


def _clear_module_managers():
    """Modul-globale _manager-Caches leeren (nach reset)."""
    from . import osrs_color, osrs_image, osrs_ocr

    osrs_color._manager = None
    osrs_image._manager = None
    osrs_ocr._manager = None


def get_contour_manager():
    global _contour_manager
    if _window is None or not _ready:
        raise RuntimeError("Session nicht bereit. Bitte zuerst start() aufrufen.")
    if _contour_manager is None:
        from .osrs_color import ContourManager

        _contour_manager = ContourManager(client=_window)
    return _contour_manager


def get_image_manager():
    global _image_manager
    if _window is None or not _ready:
        raise RuntimeError("Session nicht bereit. Bitte zuerst start() aufrufen.")
    if _image_manager is None:
        from .osrs_image import ImageManager

        _image_manager = ImageManager(client=_window)
    return _image_manager


def get_ocr_manager():
    global _ocr_manager
    if _window is None or not _ready:
        raise RuntimeError("Session nicht bereit. Bitte zuerst start() aufrufen.")
    if _ocr_manager is None:
        from .osrs_ocr import OcrManager

        _ocr_manager = OcrManager(client=_window, tesseract_cmd=_tesseract_cmd)
    return _ocr_manager
