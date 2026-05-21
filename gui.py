import threading
import tkinter as tk
from tkinter import messagebox, ttk

from screeninfo import get_monitors

import arrage


class ToggleApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Arrange Monitor")

        dpi = self.root.winfo_fpixels("1i")
        w, h = int(8 * dpi), int(5 * dpi)
        self.root.geometry(f"{w}x{h}")
        self.root.minsize(w // 2, h // 2)

        self.hwnds = []
        self.is_on = False
        self.busy = False

        self.sites = arrage.load_sites()
        self.site_vars = []

        try:
            monitor_count = len(get_monitors())
        except Exception:
            monitor_count = 0

        if monitor_count == 0:
            display_text = "No display detected"
        elif monitor_count == 1:
            display_text = "1 display detected — tiling on primary"
        else:
            display_text = f"{monitor_count} displays detected — tiling on secondary"

        container = ttk.Frame(self.root, padding=20)
        container.pack(expand=True, fill="both")

        self.display_info = ttk.Label(
            container,
            text=display_text,
            font=("Segoe UI", 11, "bold"),
            foreground="#374151",
        )
        self.display_info.pack(pady=(0, 10))

        self.toggle_btn = tk.Button(
            container,
            text="On",
            font=("Segoe UI", 28, "bold"),
            width=10,
            height=2,
            bg="#bbbbbb",
            fg="white",
            relief="flat",
            activebackground="#999999",
            command=self.toggle,
            cursor="hand2",
        )
        self.toggle_btn.pack(pady=(10, 10))

        self.status = ttk.Label(
            container,
            text="Off",
            font=("Segoe UI", 18, "bold"),
            foreground="#888",
        )
        self.status.pack(pady=(5, 10))

        list_frame = ttk.LabelFrame(container, text="Sites", padding=10)
        list_frame.pack(expand=True, fill="both", pady=(5, 0))

        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda *_: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", expand=True, fill="both")
        scrollbar.pack(side="right", fill="y")

        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        defaults = set(arrage.DisplayOnscreen2Vertically)
        for name, url in self.sites:
            var = tk.BooleanVar(value=url in defaults)
            cb = ttk.Checkbutton(inner, text=name, variable=var)
            cb.pack(anchor="w", pady=2)
            self.site_vars.append((var, url))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_busy(self, busy):
        self.busy = busy
        self.toggle_btn.config(state="disabled" if busy else "normal")

    def toggle(self):
        if self.busy:
            return
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on()

    def selected_urls(self):
        return [url for var, url in self.site_vars if var.get()]

    def turn_on(self):
        urls = self.selected_urls()
        if not urls:
            messagebox.showwarning("No sites selected", "Please check at least one site.")
            return
        self.set_busy(True)
        self.status.config(text="...", foreground="#d97706")

        def work():
            try:
                hwnds = arrage.open_sites(urls)
                self.root.after(0, self._on_opened, hwnds, None)
            except Exception as e:
                self.root.after(0, self._on_opened, [], e)

        threading.Thread(target=work, daemon=True).start()

    def _on_opened(self, hwnds, err):
        self.set_busy(False)
        if err:
            self.status.config(text="Off", foreground="#dc2626")
            messagebox.showerror("Error", str(err))
            return
        self.hwnds = hwnds
        self.is_on = True
        self.toggle_btn.config(text="Off", bg="#16a34a", activebackground="#15803d")
        self.status.config(text="On", foreground="#16a34a")

    def turn_off(self):
        arrage.close_windows(self.hwnds)
        self.hwnds = []
        self.is_on = False
        self.toggle_btn.config(text="On", bg="#bbbbbb", activebackground="#999999")
        self.status.config(text="Off", foreground="#888")

    def on_close(self):
        if self.is_on:
            arrage.close_windows(self.hwnds)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ToggleApp().run()
