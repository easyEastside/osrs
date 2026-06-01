import pyautogui
import tkinter as tk

root = tk.Tk()
root.title("")
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", "black")
root.config(bg="black")

label = tk.Label(root, text="", fg="lime", bg="black", font=("Consolas", 12))
label.pack()

def update():
    x, y = pyautogui.position()
    label.config(text=f"X={x}  Y={y}")
    root.geometry(f"+{x+15}+{y+15}")
    root.after(10, update)

root.after(10, update)
root.mainloop()