import random
import pyautogui
import osrs_api as api
import time

def run_sequence():
    if not api.start(window_title="RuneLite - Freund"):
        return
        
    print("[*] Starte vereinfachte Sequenz...")

    if api.count("pink") == 28:
        api.click_all("pink")
    
    api.click("red")

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
