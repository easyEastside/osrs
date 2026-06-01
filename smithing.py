import random
import pyautogui
import osrs_api as api
import cursor_overlay

def run_sequence():
    # 1. Spielfenster fokussieren und API starten
    # (Trage hier deinen genauen Fenstertitel ein, falls er abweicht, z.B. "RuneLite - Freund")
    if not api.start(window_title="RuneLite - Freund"):
        return
        
    print("[*] Starte vereinfachte Sequenz...")

    # click_first_contour(*GREEN)
    api.click("green")
    api.sleep(random.uniform(0.3, 0.7))

    # click_first_contour(*PINK)
    # ("pink" ist als Alias für "magenta" hinterlegt)
    api.click("pink")
    api.sleep(random.uniform(0.3, 0.7))

    # click_first_contour(*YELLOW)
    api.click("yellow")
    api.sleep(random.uniform(0.3, 0.7))

    # time.sleep(random.uniform(4.5, 5.5))
    print("[*] Warte ~5 Sekunden (mit natürlicher Mausaktivität)...")
    api.sleep(random.uniform(5.5, 6.5))

    # pyautogui.press('space')
    print("[*] Sende Tastendruck: LEERTASTE")
    pyautogui.press('space')

    # while count_contours(*RED) > 0:
    #     time.sleep(random.uniform(0.7, 1.2))
    print("[*] Warte, bis alle roten Konturen verschwunden sind...")
    while api.count("red") > 0:
        print(f"  -> Rote Konturen sind noch da ({api.count('red')}). Warte...")
        api.sleep(random.uniform(0.7, 1.2))
    print("[+] Alle roten Konturen sind verschwunden.")

    # click_first_contour(*BLUE)
    api.click("blue")
    
    # time.sleep(random.uniform(4.5, 5.5))
    print("[*] Warte ~5 Sekunden (mit natürlicher Mausaktivität)...")
    api.sleep(random.uniform(5.5, 6.5))
    
    print("[+] Sequenz erfolgreich beendet!")

if __name__ == "__main__":
    cursor_overlay.start()
    while True:
        try:
            run_sequence()
            # break  # Entferne das '#' am Zeilenanfang, wenn die Sequenz nur EINMAL laufen soll!
            print("\n[*] Starte nächsten Durchlauf\n")
        except KeyboardInterrupt:
            print("\n[!] Durch Benutzer abgebrochen.")
            break
