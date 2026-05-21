import os
import subprocess
import time

import win32con
import win32gui
from screeninfo import get_monitors

SITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sites.txt")

DisplayOnscreen2Vertically = [
    "https://reliance.allegromicro.com/Prod/rel/#/app/auth/login",
    "https://reliance-dev.allegromicro.com/Dev/rel/#/app/auth/login",
    "https://reliance-qa.allegromicro.com/Test/rel/#/app/auth/login",
]


def load_sites(path=SITES_FILE):
    sites = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            name, url = line.split("|", 1)
            sites.append((name.strip(), url.strip()))
    return sites

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Chrome not found in standard install locations")


def pick_second_monitor():
    monitors = get_monitors()
    if len(monitors) < 2:
        raise RuntimeError(f"Only {len(monitors)} monitor(s) detected; need at least 2")
    for m in monitors:
        if not getattr(m, "is_primary", False):
            return m
    return monitors[1]


def list_chrome_windows():
    handles = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1":
            handles.append(hwnd)

    win32gui.EnumWindows(cb, None)
    return set(handles)


def move_window(hwnd, x, y, w, h):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_SHOWWINDOW)


def tile_vertically(monitor, urls):
    chrome = find_chrome()
    n = len(urls)
    tile_w = monitor.width
    tile_h = monitor.height // n
    opened = []

    for i, url in enumerate(urls):
        before = list_chrome_windows()
        subprocess.Popen([chrome, f"--app={url}"])

        new_hwnd = None
        for _ in range(40):
            time.sleep(0.2)
            diff = list_chrome_windows() - before
            if diff:
                new_hwnd = next(iter(diff))
                break

        if new_hwnd is None:
            print(f"Warning: could not locate new Chrome window for {url}")
            continue

        y = monitor.y + i * tile_h
        move_window(new_hwnd, monitor.x, y, tile_w, tile_h)
        opened.append(new_hwnd)

    return opened


def open_sites(urls=None):
    monitor = pick_second_monitor()
    return tile_vertically(monitor, urls or DisplayOnscreen2Vertically)


def close_windows(hwnds):
    for hwnd in hwnds:
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception as e:
            print(f"Failed to close hwnd {hwnd}: {e}")


if __name__ == "__main__":
    open_sites()
