import random
import modules.osrs_color as api
import time

def run_sequence():
    if not api.start(window_title="RuneLite - Freund"):
        return

    print("[*] Starte Woodcutting-Sequenz...")

    while True:
        if api.count("pink") == 28:
            clicked = api.click_all("pink")
            if clicked == 0:
                print("[!] click_all('pink') hat nichts geklickt.")
            time.sleep(random.uniform(0.2, 0.5))
            continue
        
        if not api.click("yellow"):
            print("[!] Klick auf 'yellow' fehlgeschlagen.")
            time.sleep(random.uniform(0.3, 0.7))
            continue

        time.sleep(random.uniform(0.2, 0.5))

        initial_pink = api.count("pink")
        timeout = random.uniform(17, 25)
        print(f"[*] Warte auf Änderung der pinken Konturen (Start: {initial_pink}, max. {timeout:.1f}s)...")
        start = time.time()
        changed = False

        while time.time() - start < timeout:
            current_pink = api.count("pink")
            if current_pink != initial_pink:
                print(f"[+] Pinke Konturen geändert: {initial_pink} -> {current_pink}")
                changed = True
                break
            time.sleep(random.uniform(0.5, 1.5))

        if changed:
            break

        print(f"[!] Timeout nach {timeout:.1f}s ohne Änderung. Starte von vorne...")

    print("[+] Sequenz erfolgreich beendet!")

if __name__ == "__main__":
    while True:
        try:
            run_sequence()
            print("\n[*] Starte nächsten Durchlauf\n")
        except KeyboardInterrupt:
            print("\n[!] Durch Benutzer abgebrochen.")
            break
