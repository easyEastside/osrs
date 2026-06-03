"""
Gemeinsame Fenster- und Screenshot-Logik für RuneLite (Windows/Linux).
Wird von osrs_color, osrs_image und osrs_ocr genutzt.
"""
import platform
import shutil
import time
import random
import subprocess
import re

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

if IS_WINDOWS:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import cv2
import numpy as np
from PIL import ImageGrab
if IS_WINDOWS:
    import win32gui
    import win32con
    import pygetwindow as gw

_linux_tool_cache = {}


def _linux_has(tool):
    if tool not in _linux_tool_cache:
        _linux_tool_cache[tool] = shutil.which(tool) is not None
    return _linux_tool_cache[tool]


class WindowClient:
    """
    Findet das Spiel-Fenster, fokussiert es und erfasst den Client-Bereich.
    """

    def __init__(self, window_title="RuneLite"):
        self.window_title = window_title

    def find_window(self):
        """
        Finds the window matching window_title (case-insensitive partial match).
        Returns HWND (Windows) or window id (Linux), or None.
        """
        if IS_WINDOWS:
            windows = gw.getWindowsWithTitle(self.window_title)
            if not windows:
                all_wins = gw.getAllWindows()
                windows = [
                    w for w in all_wins if self.window_title.lower() in w.title.lower()
                ]
            if windows:
                return windows[0]._hWnd
            return None

        if IS_LINUX:
            if _linux_has("xdotool"):
                try:
                    out = subprocess.check_output(
                        ["xdotool", "search", "--onlyvisible", "--name", self.window_title],
                        stderr=subprocess.DEVNULL,
                    ).decode().strip()
                    ids = out.split()
                    if ids:
                        return ids[0]
                except (subprocess.CalledProcessError, OSError):
                    pass

            if _linux_has("wmctrl"):
                try:
                    out = subprocess.check_output(
                        ["wmctrl", "-l"], stderr=subprocess.DEVNULL
                    ).decode()
                    for line in out.splitlines():
                        if self.window_title.lower() in line.lower():
                            parts = line.split(None, 3)
                            if parts:
                                return parts[0]
                except (subprocess.CalledProcessError, OSError) as e:
                    print(f"[!] wmctrl fehlgeschlagen: {e}")
            elif not _linux_has("xdotool"):
                print("[!] Linux: weder xdotool noch wmctrl gefunden. Bitte installieren: sudo apt install wmctrl")
            return None

        print(f"[!] Unsupported operating system: {platform.system()}")
        return None

    def focus_window(self):
        """Brings the client window to the foreground."""
        hwnd = self.find_window()
        if not hwnd:
            print(f"[!] Window containing '{self.window_title}' not found.")
            return False

        if IS_WINDOWS:
            try:
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                else:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

                import win32com.client

                shell = win32com.client.Dispatch("WScript.Shell")
                shell.SendKeys("%")

                win32gui.SetForegroundWindow(hwnd)
                time.sleep(random.uniform(0.5, 0.8))
                return True
            except Exception as e:
                print(f"[!] Error focusing window: {e}")
                try:
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(random.uniform(0.5, 0.8))
                    return True
                except Exception as e2:
                    print(f"[!] Fallback focus also failed: {e2}")
                    return False

        if IS_LINUX:
            if _linux_has("xdotool"):
                try:
                    subprocess.check_call(
                        ["xdotool", "windowactivate", hwnd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(random.uniform(0.5, 0.8))
                    return True
                except (subprocess.CalledProcessError, OSError):
                    pass

            if _linux_has("wmctrl"):
                try:
                    subprocess.check_call(
                        ["wmctrl", "-i", "-a", hwnd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(random.uniform(0.5, 0.8))
                    return True
                except Exception as e:
                    print(f"[!] wmctrl focus fehlgeschlagen: {e}")
                    return False

            print("[!] Fenster fokussieren auf Linux nicht möglich (wmctrl/xdotool fehlt).")
            return False

        return False

    def get_client_rect(self):
        """Client area in screen coordinates: (left, top, right, bottom)."""
        hwnd = self.find_window()
        if not hwnd:
            return None

        if IS_WINDOWS:
            try:
                left, top = win32gui.ClientToScreen(hwnd, (0, 0))
                _, _, width, height = win32gui.GetClientRect(hwnd)
                return (left, top, left + width, top + height)
            except Exception as e:
                print(f"[!] Error getting client rect: {e}")
                return None

        if IS_LINUX:
            if _linux_has("xdotool"):
                try:
                    out = subprocess.check_output(
                        ["xdotool", "getwindowgeometry", hwnd], stderr=subprocess.DEVNULL
                    ).decode()
                    pos_match = re.search(r"Position:\s*(\d+),(\d+)", out)
                    geom_match = re.search(r"Geometry:\s*(\d+)x(\d+)", out)
                    if pos_match and geom_match:
                        left, top = int(pos_match.group(1)), int(pos_match.group(2))
                        width, height = int(geom_match.group(1)), int(geom_match.group(2))
                        return (left, top, left + width, top + height)
                except (subprocess.CalledProcessError, OSError):
                    pass

            if _linux_has("xwininfo"):
                try:
                    out = subprocess.check_output(
                        ["xwininfo", "-id", hwnd], stderr=subprocess.DEVNULL
                    ).decode()
                    x_match = re.search(r"Absolute upper-left X:\s*(\d+)", out)
                    y_match = re.search(r"Absolute upper-left Y:\s*(\d+)", out)
                    w_match = re.search(r"Width:\s*(\d+)", out)
                    h_match = re.search(r"Height:\s*(\d+)", out)
                    if x_match and y_match and w_match and h_match:
                        left = int(x_match.group(1))
                        top = int(y_match.group(1))
                        width = int(w_match.group(1))
                        height = int(h_match.group(1))
                        return (left, top, left + width, top + height)
                except Exception as e:
                    print(f"[!] xwininfo fehlgeschlagen: {e}")
            elif not _linux_has("xdotool"):
                print("[!] Linux: xwininfo nicht gefunden. Bitte installieren: sudo apt install x11-utils")

            return None

        return None

    def capture_client_area(self):
        """
        Captures the client area.
        Returns: (BGR image, (left, top) screen offset) or (None, (0, 0)).
        """
        rect = self.get_client_rect()
        if not rect:
            return None, (0, 0)

        left, top, right, bottom = rect
        width = right - left
        height = bottom - top

        if width <= 0 or height <= 0:
            return None, (0, 0)

        try:
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            return img, (left, top)
        except Exception as e:
            print(f"[!] Screenshot fehlgeschlagen: {e}")
            return None, (0, 0)
