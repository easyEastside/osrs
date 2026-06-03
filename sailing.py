import random
import pyautogui
import modules.osrs_color as api
import time

def run_sequence():
    if not api.start(window_title="RuneLite - Freund"):
        return
        
    print("[*] Starte vereinfachte Sequenz...")

    if api.count("pink") == 28:
        clicked = api.click_all("pink")
        if clicked == 0:
            print("[!] click_all('pink') hat nichts geklickt.")
    
    time.sleep(random.uniform(0.2, 0.5))
    
    if not api.click("red"):
        print("[!] Klick auf 'red' fehlgeschlagen.")
        return

    last_count = api.count("pink")
    last_change = time.time()
    while last_count < 28:
        current_count = api.count("pink")
        print(f"[*] Pinke Konturen: {current_count}/28")
        if current_count != last_count:
            last_count = current_count
            last_change = time.time()
        elif time.time() - last_change > 30:
            print("[!] Timeout: 30 Sekunden keine Änderung.")
            break
        time.sleep(random.uniform(1, 5))

    print("[+] Sequenz erfolgreich beendet!")

if __name__ == "__main__":
    while True:
        try:
            run_sequence()
            # break  # Entferne das '#' am Zeilenanfang, wenn die Sequenz nur EINMAL laufen soll!
            print("\n[*] Starte nächsten Durchlauf\n")
        except KeyboardInterrupt:
            print("\n[!] Durch Benutzer abgebrochen.")
            break
