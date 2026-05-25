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


def save_sites(sites, path=SITES_FILE):
    with open(path, "w", encoding="utf-8") as f:
        for name, url in sites:
            f.write(f"{name} | {url}\n")

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_chrome():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Chrome not found in standard install locations")


BROWSER_CANDIDATES = [
    {
        "name": "Chrome",
        "short": "Chr",
        "paths": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ],
        "win_class": "Chrome_WidgetWin_1",
        "app_mode": True,
    },
    {
        "name": "Edge",
        "short": "Edg",
        "paths": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ],
        "win_class": "Chrome_WidgetWin_1",
        "app_mode": True,
    },
    {
        "name": "Brave",
        "short": "Brv",
        "paths": [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        ],
        "win_class": "Chrome_WidgetWin_1",
        "app_mode": True,
    },
    {
        "name": "Opera",
        "short": "Opr",
        "paths": [
            r"C:\Program Files\Opera\opera.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\opera.exe"),
        ],
        "win_class": "Chrome_WidgetWin_1",
        "app_mode": True,
    },
    {
        "name": "Firefox",
        "short": "Fir",
        "paths": [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ],
        "win_class": "MozillaWindowClass",
        "app_mode": False,
    },
]


def detect_browsers():
    found = []
    for spec in BROWSER_CANDIDATES:
        for p in spec["paths"]:
            if p and os.path.exists(p):
                found.append({**spec, "path": p})
                break
    return found


def list_browser_windows(win_class):
    handles = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if win32gui.GetClassName(hwnd) == win_class:
            handles.append(hwnd)

    win32gui.EnumWindows(cb, None)
    return set(handles)


def open_browser_window(browser, url):
    before = list_browser_windows(browser["win_class"])
    if browser.get("app_mode"):
        subprocess.Popen([browser["path"], f"--app={url}"])
    else:
        subprocess.Popen([browser["path"], url])
    for _ in range(40):
        time.sleep(0.2)
        diff = list_browser_windows(browser["win_class"]) - before
        if diff:
            return next(iter(diff))
    return None


def pick_target_monitor():
    monitors = get_monitors()
    if not monitors:
        raise RuntimeError("No monitors detected")
    if len(monitors) == 1:
        return monitors[0]
    for m in monitors:
        if not getattr(m, "is_primary", False):
            return m
    return monitors[1]


def pick_monitor_at(index):
    monitors = get_monitors()
    if not monitors:
        raise RuntimeError("No monitors detected")
    if index < 0 or index >= len(monitors):
        raise RuntimeError(
            f"Display {index + 1} not available; only {len(monitors)} detected"
        )
    return monitors[index]


pick_second_monitor = pick_target_monitor


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


def open_chrome_window(url):
    chrome = find_chrome()
    before = list_chrome_windows()
    subprocess.Popen([chrome, f"--app={url}"])
    for _ in range(40):
        time.sleep(0.2)
        diff = list_chrome_windows() - before
        if diff:
            return next(iter(diff))
    return None


def tile_hwnds(monitor, hwnds):
    n = len(hwnds)
    if n == 0:
        return
    tile_w = monitor.width
    tile_h = monitor.height // n
    for i, hwnd in enumerate(hwnds):
        y = monitor.y + i * tile_h
        move_window(hwnd, monitor.x, y, tile_w, tile_h)


def tile_vertically(monitor, urls):
    opened = []
    for url in urls:
        hwnd = open_chrome_window(url)
        if hwnd is None:
            print(f"Warning: could not locate new Chrome window for {url}")
            continue
        opened.append(hwnd)
    tile_hwnds(monitor, opened)
    return opened


def open_sites(urls=None, monitor_index=None):
    if monitor_index is None:
        monitor = pick_target_monitor()
    else:
        monitor = pick_monitor_at(monitor_index)
    urls = list(urls or DisplayOnscreen2Vertically)
    opened = {}
    for url in urls:
        hwnd = open_chrome_window(url)
        if hwnd is None:
            print(f"Warning: could not locate new Chrome window for {url}")
            continue
        opened[url] = hwnd
    tile_hwnds(monitor, list(opened.values()))
    return opened


def close_windows(hwnds):
    for hwnd in hwnds:
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        except Exception as e:
            print(f"Failed to close hwnd {hwnd}: {e}")


if __name__ == "__main__":
    open_sites()
