"""
Gemeinsame Fenster- und Screenshot-Logik für RuneLite (Windows/Linux).
Wird von osrs_color, osrs_image und osrs_ocr genutzt.
"""
import platform
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
            try:
                out = subprocess.check_output(
                    ["xdotool", "search", "--onlyvisible", "--name", self.window_title],
                    stderr=subprocess.DEVNULL,
                ).decode().strip()
                ids = out.split()
                if ids:
                    return ids[0]
            except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
                print(f"[!] xdotool nicht verfügbar oder fehlgeschlagen: {e}")

            try:
                out = subprocess.check_output(
                    ["wmctrl", "-l"], stderr=subprocess.DEVNULL
                ).decode()
                for line in out.splitlines():
                    if self.window_title.lower() in line.lower():
                        parts = line.split(None, 3)
                        if parts:
                            return parts[0]
            except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
                print(f"[!] wmctrl nicht verfügbar oder fehlgeschlagen: {e}")
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
            try:
                subprocess.check_call(
                    ["xdotool", "windowactivate", hwnd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(random.uniform(0.5, 0.8))
                return True
            except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
                print(f"[!] xdotool windowactivate fehlgeschlagen: {e}")
            try:
                subprocess.check_call(
                    ["wmctrl", "-i", "-a", hwnd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(random.uniform(0.5, 0.8))
                return True
            except Exception as e:
                print(f"[!] Error focusing window on Linux: {e}")
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
            except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
                print(f"[!] xdotool getwindowgeometry fehlgeschlagen: {e}")

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
                print(f"[!] Error getting window geometry on Linux: {e}")

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
