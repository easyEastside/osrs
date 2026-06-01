from pynput import mouse
from pynput.keyboard import Controller, Key
import time
import random

keyboard = Controller()

def on_click(x, y, button, pressed):
    try:
        if pressed and button == mouse.Button.right:
            time.sleep(random.uniform(0.07, 0.12))

            keyboard.press(Key.f12)
            time.sleep(random.uniform(0.07, 0.12))
            keyboard.release(Key.f12)

            time.sleep(random.uniform(0.05, 0.15))

            keyboard.press(Key.enter)
            time.sleep(random.uniform(0.07, 0.12))
            keyboard.release(Key.enter)
    except Exception as e:
        print(f"Fehler: {e}")

print("Rechtsklick -> F12 + Enter")
with mouse.Listener(on_click=on_click) as listener:
    listener.join()
