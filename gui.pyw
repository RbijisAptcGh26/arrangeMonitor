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

        self.hwnds = {}
        self.is_on = False
        self.busy = False
        self.active_monitor_index = None

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
        self.display_info.pack(pady=(0, 5))

        default_index = 1 if monitor_count >= 2 else 0
        self.target_display = tk.IntVar(value=default_index)

        radio_frame = ttk.Frame(container)
        radio_frame.pack(pady=(0, 10))

        for i in range(3):
            rb = ttk.Radiobutton(
                radio_frame,
                text=f"Display {i + 1}",
                variable=self.target_display,
                value=i,
            )
            rb.pack(side="left", padx=8)
            if i >= monitor_count:
                rb.state(["disabled"])

        button_row = ttk.Frame(container)
        button_row.pack(pady=(10, 10))

        self.toggle_btn = tk.Button(
            button_row,
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
        self.toggle_btn.pack(side="left", padx=(0, 10))

        self.refresh_btn = tk.Button(
            button_row,
            text="Refresh",
            font=("Segoe UI", 12, "bold"),
            width=10,
            height=2,
            bg="#e5e7eb",
            fg="#374151",
            relief="flat",
            activebackground="#d1d5db",
            command=self.refresh,
            cursor="hand2",
            state="disabled",
        )
        self.refresh_btn.pack(side="left")

        self.status = ttk.Label(
            container,
            text="Off",
            font=("Segoe UI", 18, "bold"),
            foreground="#888",
        )
        self.status.pack(pady=(5, 10))

        self.list_frame = ttk.LabelFrame(container, text="", padding=10)
        self.list_frame.pack(expand=True, fill="both", pady=(5, 0))
        list_frame = self.list_frame

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

        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=0)

        header_name = ttk.Label(inner, text="Site", font=("Segoe UI", 9, "bold"))
        header_name.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 4))
        header_disp = ttk.Label(inner, text="Display", font=("Segoe UI", 9, "bold"))
        header_disp.grid(row=0, column=1, sticky="w", pady=(0, 4))

        self.site_display_labels = {}
        defaults = set(arrage.DisplayOnscreen2Vertically)
        for i, (name, url) in enumerate(self.sites, start=1):
            var = tk.BooleanVar(value=url in defaults)
            cb = ttk.Checkbutton(
                inner,
                text=name,
                variable=var,
                command=lambda u=url: self.on_site_toggle(u),
            )
            cb.grid(row=i, column=0, sticky="w", padx=(0, 12), pady=2)
            lbl = ttk.Label(inner, text="—", foreground="#888", width=12)
            lbl.grid(row=i, column=1, sticky="w", pady=2)
            self.site_vars.append((var, url))
            self.site_display_labels[url] = lbl

        self._update_sites_label()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def set_busy(self, busy):
        self.busy = busy
        self.toggle_btn.config(state="disabled" if busy else "normal")
        self._update_refresh_state()

    def _update_refresh_state(self):
        enabled = self.is_on and not self.busy and bool(self.hwnds)
        self.refresh_btn.config(state="normal" if enabled else "disabled")

    def _update_sites_label(self):
        total = len(self.sites)
        displayed = len(self.hwnds)
        parts = [f"{total} sites", f"{displayed} displayed"]
        if self.active_monitor_index is not None and displayed > 0:
            parts.append(f"Display {self.active_monitor_index + 1}")
        self.list_frame.config(text=" | ".join(parts))

    def toggle(self):
        if self.busy:
            return
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on()

    def selected_urls(self):
        return [url for var, url in self.site_vars if var.get()]

    def _var_for(self, url):
        return next(v for v, u in self.site_vars if u == url)

    def _set_display_label(self, url, monitor_index):
        lbl = self.site_display_labels.get(url)
        if lbl is None:
            return
        if monitor_index is None:
            lbl.config(text="—", foreground="#888")
        else:
            lbl.config(text=f"Display {monitor_index + 1}", foreground="#16a34a")

    def turn_on(self):
        urls = self.selected_urls()
        if not urls:
            messagebox.showwarning("No sites selected", "Please check at least one site.")
            return
        self.set_busy(True)
        self.status.config(text="...", foreground="#d97706")

        monitor_index = self.target_display.get()

        def work():
            try:
                opened = arrage.open_sites(urls, monitor_index=monitor_index)
                self.root.after(0, self._on_opened, opened, monitor_index, None)
            except Exception as e:
                self.root.after(0, self._on_opened, {}, monitor_index, e)

        threading.Thread(target=work, daemon=True).start()

    def _on_opened(self, opened, monitor_index, err):
        self.set_busy(False)
        if err:
            self.status.config(text="Off", foreground="#dc2626")
            messagebox.showerror("Error", str(err))
            return
        self.hwnds = dict(opened)
        self.active_monitor_index = monitor_index
        self.is_on = True
        self.toggle_btn.config(text="Off", bg="#16a34a", activebackground="#15803d")
        self.status.config(text="On", foreground="#16a34a")
        for url in self.hwnds:
            self._set_display_label(url, monitor_index)
        for var, url in self.site_vars:
            if var.get() and url not in self.hwnds:
                var.set(False)
        self._update_refresh_state()
        self._update_sites_label()

    def turn_off(self):
        arrage.close_windows(list(self.hwnds.values()))
        for url in list(self.hwnds.keys()):
            self._set_display_label(url, None)
        self.hwnds = {}
        self.active_monitor_index = None
        self.is_on = False
        self.toggle_btn.config(text="On", bg="#bbbbbb", activebackground="#999999")
        self.status.config(text="Off", foreground="#888")
        self._update_refresh_state()
        self._update_sites_label()

    def refresh(self):
        if not self.is_on or self.busy or not self.hwnds:
            return
        self._retile()
        self.status.config(text="On", foreground="#16a34a")

    def on_site_toggle(self, url):
        if not self.is_on or self.busy:
            return
        var = self._var_for(url)
        if var.get():
            if url in self.hwnds:
                return
            self.set_busy(True)
            self.status.config(text="...", foreground="#d97706")

            def work():
                try:
                    hwnd = arrage.open_chrome_window(url)
                    self.root.after(0, self._on_site_added, url, hwnd, None)
                except Exception as e:
                    self.root.after(0, self._on_site_added, url, None, e)

            threading.Thread(target=work, daemon=True).start()
        else:
            if url not in self.hwnds:
                return
            hwnd = self.hwnds.pop(url)
            arrage.close_windows([hwnd])
            self._set_display_label(url, None)
            self._retile()
            self.status.config(text="On", foreground="#16a34a")
            self._update_refresh_state()
            self._update_sites_label()

    def _on_site_added(self, url, hwnd, err):
        self.set_busy(False)
        if err or hwnd is None:
            self._var_for(url).set(False)
            self.status.config(text="On", foreground="#16a34a")
            if err:
                messagebox.showerror("Error", str(err))
            else:
                messagebox.showwarning(
                    "Open failed", f"Could not locate Chrome window for {url}"
                )
            return
        self.hwnds[url] = hwnd
        self._set_display_label(url, self.active_monitor_index)
        self._retile()
        self.status.config(text="On", foreground="#16a34a")
        self._update_sites_label()

    def _retile(self):
        if self.active_monitor_index is None or not self.hwnds:
            return
        try:
            monitor = arrage.pick_monitor_at(self.active_monitor_index)
        except Exception as e:
            messagebox.showerror("Retile failed", str(e))
            return
        arrage.tile_hwnds(monitor, list(self.hwnds.values()))

    def on_close(self):
        if self.is_on:
            arrage.close_windows(list(self.hwnds.values()))
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ToggleApp().run()
