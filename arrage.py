import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes

import win32con
import win32gui
from screeninfo import get_monitors

DWMWA_EXTENDED_FRAME_BOUNDS = 9

SITES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sites.txt")
APPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps.txt")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

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


def load_settings(path=SETTINGS_FILE):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(data, path=SETTINGS_FILE):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


DEFAULT_APPS = [
    ("Outlook", r"C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE"),
    ("Teams", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe")),
    ("Word", r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"),
    ("Excel", r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"),
    ("PowerPoint", r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"),
    ("OneNote", r"C:\Program Files\Microsoft Office\root\Office16\ONENOTE.EXE"),
]


def load_apps(path=APPS_FILE):
    apps = []
    if not os.path.exists(path):
        save_apps(DEFAULT_APPS, path)
        return list(DEFAULT_APPS)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            name, exe = line.split("|", 1)
            apps.append((name.strip(), exe.strip()))
    return apps


def save_apps(apps, path=APPS_FILE):
    with open(path, "w", encoding="utf-8") as f:
        for name, exe in apps:
            f.write(f"{name} | {exe}\n")


def _list_top_windows():
    handles = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        if not win32gui.GetWindowText(hwnd):
            return
        handles.append(hwnd)

    win32gui.EnumWindows(cb, None)
    return set(handles)


def open_app_window(exe_path):
    if not exe_path or not os.path.exists(exe_path):
        raise FileNotFoundError(f"App not found: {exe_path}")
    before = _list_top_windows()
    subprocess.Popen([exe_path])
    for _ in range(60):
        time.sleep(0.25)
        diff = _list_top_windows() - before
        for hwnd in diff:
            try:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
            except Exception:
                continue
            if w > 200 and h > 150:
                return hwnd
    return None

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


def _get_frame_padding(hwnd):
    try:
        visible = wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd),
            DWMWA_EXTENDED_FRAME_BOUNDS,
            ctypes.byref(visible),
            ctypes.sizeof(visible),
        )
        geom = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(geom))
        return (
            visible.left - geom.left,
            visible.top - geom.top,
            geom.right - visible.right,
            geom.bottom - visible.bottom,
        )
    except Exception:
        return (0, 0, 0, 0)


def move_window(hwnd, x, y, w, h):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x, y, w, h, win32con.SWP_SHOWWINDOW)
    left, top, right, bottom = _get_frame_padding(hwnd)
    if left or top or right or bottom:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            x - left,
            y - top,
            w + left + right,
            h + top + bottom,
            win32con.SWP_SHOWWINDOW,
        )


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
