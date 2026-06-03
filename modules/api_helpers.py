"""Gemeinsame Hilfen für osrs_color, osrs_image und osrs_ocr."""


def require_manager(getter, not_started_message="[!] Fehler: Bitte rufe zuerst 'start()' auf."):
    """
    Holt den Modul-Manager über osrs_session.
    Gibt None zurück, wenn die Session nicht läuft.
    """
    from . import osrs_session

    if not osrs_session.is_started():
        print(not_started_message)
        return None
    try:
        return getter()
    except RuntimeError as e:
        print(f"[!] {e}")
        return None
