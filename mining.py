import random
import modules.osrs_color as api
import time

def run_sequence():
    if not api.start(window_title="RuneLite - Trader Mirco"):
        return

    print("[*] Starte Mining-Sequenz...")

    if api.count("pink") == 28:
        clicked = api.click_all("pink")
        if clicked == 0:
            print("[!] click_all('pink') hat nichts geklickt.")
        time.sleep(random.uniform(0.2, 0.5))

    if not api.click_random("yellow"):
        print("[!] Klick auf 'yellow' fehlgeschlagen.")
        return

    initial_pink = api.count("pink")
    target_pink = initial_pink + 1
    timeout = random.uniform(10, 15)
    print(
        f"[*] Warte auf +1 pinke Kontur ({initial_pink} -> {target_pink}, "
        f"max. {timeout:.1f}s)..."
    )
    start = time.time()

    while time.time() - start < timeout:
        current_count = api.count("pink")
        print(f"[*] Pinke Konturen: {current_count} (Ziel: {target_pink})")
        if current_count >= target_pink:
            print(f"[+] Pinke Konturen: {initial_pink} -> {current_count}")
            print("[+] Sequenz erfolgreich beendet!")
            return
        time.sleep(random.uniform(0.5, 1.5))

    print(f"[!] Timeout nach {timeout:.1f}s ohne +1. Starte von vorne...")

if __name__ == "__main__":
    while True:
        try:
            run_sequence()
            print("\n[*] Starte nächsten Durchlauf\n")
        except KeyboardInterrupt:
            print("\n[!] Durch Benutzer abgebrochen.")
            break
