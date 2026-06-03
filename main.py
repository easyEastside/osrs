import sys
import time
import random
import cv2
from modules.osrs_color import ContourManager

def print_menu():
    print("\n" + "=" * 60)
    print("          OSRS RUNE-LITE KONTUREN AUTOMATISIERUNG")
    print("=" * 60)
    print(" 1. Fenster fokussieren & Alle Konturen zählen")
    print(" 2. Eine Konturenfarbe anklicken (Menschliches Klicken)")
    print(" 3. Auf das Erscheinen einer Kontur warten")
    print(" 4. Warten bis eine Kontur verschwindet")
    print(" 5. Aktuelle Maus-Farbe testen (Validierungstest)")
    print(" 6. Alle Konturen einer Farbe anklicken")
    print(" 7. Beenden")
    print("=" * 60)

def choose_color():
    seen = set()
    color_names = []
    for name, bgr in ContourManager.COLOR_MAP.items():
        if tuple(bgr) not in seen:
            seen.add(tuple(bgr))
            color_names.append(name)

    print("\nVerfügbare Farben:")
    for name in color_names:
        print(f"  - {name}")
    while True:
        color = input("Farbe eingeben (oder 'zurück'): ").strip().lower()
        if color == 'zurück':
            return None
        if color in ContourManager.COLOR_MAP:
            return color
        print(f"[!] Ungültige Farbe. Bitte wähle aus: {', '.join(color_names)}")

def main():
    # Initialisiere den ContourManager. Standard-Fenstername ist "RuneLite"
    manager = ContourManager(window_title="RuneLite")
    
    print("[*] RuneLite Konturen-Automatisierung geladen.")
    print("[*] Falsch-Sicherheits-Funktion (Failsafe) aktiv: Bewege die Maus in eine Ecke des Bildschirms, um das Programm sofort abzubrechen.")
    
    # Erste Überprüfung, ob das Fenster läuft
    hwnd = manager.find_window()
    if not hwnd:
        print("[WARNING] RuneLite-Fenster wurde nicht gefunden. Bitte stelle sicher, dass RuneLite geöffnet ist.")
    else:
        print("[+] RuneLite-Fenster gefunden und bereit.")

    while True:
        print_menu()
        choice = input("Option auswählen (1-7): ").strip()
        
        if choice == '1':
            print("\n[*] Fokussiere RuneLite-Fenster...")
            if manager.focus_window():
                print("[*] Suche nach Konturen...")
                img, _ = manager.capture_client_area()
                if img is not None:
                    for color in ["blue", "green", "magenta", "yellow", "red"]:
                        contours = manager.find_contours(img, color)
                        if len(contours) > 0:
                            print(f"  -> {color.upper()}: {len(contours)} Konturen gefunden")
                            for idx, cnt in enumerate(contours):
                                area = int(cv2.contourArea(cnt))
                                print(f"     - Kontur {idx+1}: Fläche = {area} px")
                        else:
                            print(f"  -> {color.upper()}: Keine Konturen gefunden")
                else:
                    print("[!] Client-Bereich konnte nicht erfasst werden.")
            else:
                print("[!] Fenster konnte nicht fokussiert werden.")
                
        elif choice == '2':
            color = choose_color()
            if not color:
                continue
                
            print("\n[*] Fokussiere RuneLite-Fenster...")
            if manager.focus_window():
                contours, offset = manager.get_contours_on_screen(color)
                if len(contours) == 0:
                    print(f"[-] Keine Konturen der Farbe '{color}' auf dem Bildschirm gefunden.")
                    continue
                
                # Wähle eine zufällige Kontur aus der Liste
                selected_contour = random.choice(contours)
                print(f"[+] {len(contours)} Konturen gefunden. Wähle eine zufällige Kontur aus...")
                
                # Führe den Klick aus (inkl. WindMouse-Bewegung und Farbprüfung an der Maus)
                success = manager.click_contour(selected_contour, color, offset)
                if success:
                    print("[+] Erfolgreich geklickt!")
                else:
                    print("[-] Klick fehlgeschlagen (Farbprüfung war ungültig).")
            else:
                print("[!] Fenster konnte nicht fokussiert werden.")
                
        elif choice == '3':
            color = choose_color()
            if not color:
                continue
                
            try:
                timeout = float(input("Timeout in Sekunden (Standard 30): ").strip() or "30")
            except ValueError:
                timeout = 30.0
                
            print(f"\n[*] Bitte wechsle zu RuneLite. Warter auf '{color}' für max {timeout}s...")
            # Warte auf das Erscheinen der Kontur
            contours, offset = manager.wait_for_contour(color, timeout=timeout)
            if len(contours) > 0:
                print(f"[+] Gefunden! Es gibt {len(contours)} Konturen.")
            else:
                print("[-] Timeout abgelaufen.")
                
        elif choice == '4':
            color = choose_color()
            if not color:
                continue
                
            try:
                timeout = float(input("Timeout in Sekunden (Standard 30): ").strip() or "30")
            except ValueError:
                timeout = 30.0
                
            print(f"\n[*] Warte bis '{color}' verschwindet...")
            success = manager.wait_for_contour_to_disappear(color, timeout=timeout)
            if success:
                print("[+] Die Kontur ist verschwunden.")
            else:
                print("[-] Timeout abgelaufen, Kontur ist noch da.")
                
        elif choice == '5':
            print("\n[*] Du hast 3 Sekunden Zeit, um deine Maus über eine farbige Kontur zu bewegen...")
            for i in range(3, 0, -1):
                print(f"  {i}...")
                time.sleep(1)
                
            print("[*] Überprüfe Farbe um die Maus herum...")
            found_any = False
            for name, bgr in manager.COLOR_MAP.items():
                if manager.verify_color_at_mouse(bgr, neighborhood_size=9, tolerance=5):
                    print(f"[+] JA! Die Farbe '{name}' wurde im Bereich deiner Maus gefunden.")
                    found_any = True
            
            if not found_any:
                # Hole den genauen Farbwert unter der Maus
                import pyautogui
                from PIL import ImageGrab
                x, y = pyautogui.position()
                img = ImageGrab.grab(bbox=(x, y, x+1, y+1))
                pixel_rgb = list(img.getpixel((0, 0)))
                print(f"[-] Keine vordefinierte Farbe gefunden. RGB an der Maus: {pixel_rgb} (Hex: #{pixel_rgb[0]:02x}{pixel_rgb[1]:02x}{pixel_rgb[2]:02x})")
                
        elif choice == '6':
            color = choose_color()
            if not color:
                continue
            
            print("\n[*] Fokussiere RuneLite-Fenster...")
            if manager.focus_window():
                clicked = manager.click_all_contours(color)
                print(f"[+] Fertig: {clicked} Konturen der Farbe '{color}' wurden angeklickt.")
            else:
                print("[!] Fenster konnte nicht fokussiert werden.")
                
        elif choice == '7':
            print("\n[*] Beende Programm. Auf Wiedersehen!")
            sys.exit(0)
            
        else:
            print("[!] Ungültige Option. Wähle eine Zahl zwischen 1 und 7.")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Durch Benutzer abgebrochen (Strg+C).")
    except Exception as e:
        print(f"\n[!] Unerwarteter Fehler: {e}")
