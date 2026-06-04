import random
import modules.osrs_color as api
import time

def run_sequence():
    if not api.start(window_title="RuneLite - Trader Mirco"):
        return

    print("[*] Starte Woodcutting-Sequenz...")

    if api.count("pink") == 28:
        clicked = api.click_all("pink")
        if clicked == 0:
            print("[!] click_all('pink') hat nichts geklickt.")
        time.sleep(random.uniform(0.2, 0.5))

    if not api.click_random("yellow"):
        print("[!] Klick auf 'yellow' fehlgeschlagen.")
        return

    last_count = api.count("pink")
    last_change = time.time()
    timeout = random.uniform(15, 22)
    while last_count < 28:
        current_count = api.count("pink")
        print(f"[*] Pinke Konturen: {current_count}/28")
        if current_count != last_count:
            last_count = current_count
            last_change = time.time()
        elif time.time() - last_change > timeout:
            print(f"[!] Timeout: {timeout:.1f}s keine Änderung.")
            break
        time.sleep(random.uniform(0.5, 1.5))

    print("[+] Sequenz erfolgreich beendet!")

if __name__ == "__main__":
    while True:
        try:
            run_sequence()
            print("\n[*] Starte nächsten Durchlauf\n")
        except KeyboardInterrupt:
            print("\n[!] Durch Benutzer abgebrochen.")
            break
