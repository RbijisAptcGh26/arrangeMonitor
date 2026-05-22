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
        self.site_monitor = {}
        self.display_layouts = {}
        self.is_on = False
        self.busy = False

        self.sites = arrage.load_sites()
        self.site_vars = []
        self.site_target_vars = {}

        try:
            self.monitor_count = len(get_monitors())
        except Exception:
            self.monitor_count = 0
        monitor_count = self.monitor_count

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
        inner.columnconfigure(2, weight=0)

        header_name = ttk.Label(inner, text="Site", font=("Segoe UI", 9, "bold"))
        header_name.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 4))
        header_disp = ttk.Label(inner, text="Display", font=("Segoe UI", 9, "bold"))
        header_disp.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 4))
        header_target = ttk.Label(inner, text="Open on", font=("Segoe UI", 9, "bold"))
        header_target.grid(row=0, column=2, sticky="w", pady=(0, 4))

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
            lbl.grid(row=i, column=1, sticky="w", padx=(0, 12), pady=2)

            target_var = tk.IntVar(value=-1)
            self.site_target_vars[url] = target_var
            radio_cell = ttk.Frame(inner)
            radio_cell.grid(row=i, column=2, sticky="w", pady=2)
            for j in range(3):
                rb = ttk.Radiobutton(
                    radio_cell,
                    text=f"D{j + 1}",
                    variable=target_var,
                    value=j,
                    command=lambda u=url: self.on_target_changed(u),
                )
                rb.pack(side="left", padx=2)
                if j >= monitor_count:
                    rb.state(["disabled"])

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

    def _describe_display(self, idx, short=False):
        layout = self.display_layouts.get(idx)
        prefix = f"D{idx + 1}" if short else f"Display {idx + 1}"
        return f"{prefix} ({layout})" if layout else prefix

    def _update_sites_label(self):
        total = len(self.sites)
        displayed = len(self.hwnds)
        parts = [f"{total} sites", f"{displayed} displayed"]
        if displayed > 0:
            displays_used = sorted(set(self.site_monitor.values()))
            if len(displays_used) == 1:
                parts.append(self._describe_display(displays_used[0]))
            else:
                parts.append(
                    "Displays "
                    + ", ".join(self._describe_display(d, short=True) for d in displays_used)
                )
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

    def _set_target_radio(self, url, monitor_index):
        var = self.site_target_vars.get(url)
        if var is None:
            return
        var.set(-1 if monitor_index is None else monitor_index)

    def _resolve_target(self, url):
        per_row = self.site_target_vars[url].get()
        if 0 <= per_row < self.monitor_count:
            return per_row
        return self.target_display.get()

    def turn_on(self):
        urls = self.selected_urls()
        if not urls:
            messagebox.showwarning("No sites selected", "Please check at least one site.")
            return
        self.set_busy(True)
        self.status.config(text="...", foreground="#d97706")

        site_targets = [(url, self._resolve_target(url)) for url in urls]

        def work():
            try:
                opened = {}
                for url, idx in site_targets:
                    hwnd = arrage.open_chrome_window(url)
                    if hwnd is not None:
                        opened[url] = (hwnd, idx)
                by_monitor = {}
                for url, (hwnd, idx) in opened.items():
                    by_monitor.setdefault(idx, []).append(hwnd)
                layouts = {}
                for idx, hwnds in by_monitor.items():
                    try:
                        mon = arrage.pick_monitor_at(idx)
                        layouts[idx] = arrage.tile_hwnds(mon, hwnds)
                    except Exception as e:
                        print(f"Tile failed for display {idx + 1}: {e}")
                self.root.after(0, self._on_opened, opened, layouts, None)
            except Exception as e:
                self.root.after(0, self._on_opened, {}, {}, e)

        threading.Thread(target=work, daemon=True).start()

    def _on_opened(self, opened, layouts, err):
        self.set_busy(False)
        if err:
            self.status.config(text="Off", foreground="#dc2626")
            messagebox.showerror("Error", str(err))
            return
        self.hwnds = {url: hwnd for url, (hwnd, _) in opened.items()}
        self.site_monitor = {url: idx for url, (_, idx) in opened.items()}
        self.display_layouts = dict(layouts)
        self.is_on = True
        self.toggle_btn.config(text="Off", bg="#16a34a", activebackground="#15803d")
        self.status.config(text="On", foreground="#16a34a")
        for url, idx in self.site_monitor.items():
            self._set_display_label(url, idx)
            self._set_target_radio(url, idx)
        for var, url in self.site_vars:
            if var.get() and url not in self.hwnds:
                var.set(False)
        self._update_refresh_state()
        self._update_sites_label()

    def turn_off(self):
        arrage.close_windows(list(self.hwnds.values()))
        for url in list(self.hwnds.keys()):
            self._set_display_label(url, None)
            self._set_target_radio(url, None)
        self.hwnds = {}
        self.site_monitor = {}
        self.display_layouts = {}
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

    def on_target_changed(self, url):
        if not self.is_on or self.busy:
            return
        if url not in self.hwnds:
            return
        new_idx = self.site_target_vars[url].get()
        if new_idx < 0 or new_idx == self.site_monitor.get(url):
            return
        old_idx = self.site_monitor[url]
        self.site_monitor[url] = new_idx
        self._set_display_label(url, new_idx)
        self._retile_displays({old_idx, new_idx})
        self._update_sites_label()

    def on_site_toggle(self, url):
        if not self.is_on or self.busy:
            return
        var = self._var_for(url)
        if var.get():
            if url in self.hwnds:
                return
            target = self._resolve_target(url)
            self.set_busy(True)
            self.status.config(text="...", foreground="#d97706")

            def work():
                try:
                    hwnd = arrage.open_chrome_window(url)
                    self.root.after(0, self._on_site_added, url, hwnd, target, None)
                except Exception as e:
                    self.root.after(0, self._on_site_added, url, None, target, e)

            threading.Thread(target=work, daemon=True).start()
        else:
            if url not in self.hwnds:
                return
            hwnd = self.hwnds.pop(url)
            old_idx = self.site_monitor.pop(url, None)
            arrage.close_windows([hwnd])
            self._set_display_label(url, None)
            self._set_target_radio(url, None)
            if old_idx is not None:
                self._retile_displays({old_idx})
            self.status.config(text="On", foreground="#16a34a")
            self._update_refresh_state()
            self._update_sites_label()

    def _on_site_added(self, url, hwnd, monitor_index, err):
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
        self.site_monitor[url] = monitor_index
        self._set_display_label(url, monitor_index)
        self._set_target_radio(url, monitor_index)
        self._retile_displays({monitor_index})
        self.status.config(text="On", foreground="#16a34a")
        self._update_refresh_state()
        self._update_sites_label()

    def _hwnds_by_monitor(self):
        groups = {}
        for url, hwnd in self.hwnds.items():
            idx = self.site_monitor.get(url)
            if idx is None:
                continue
            groups.setdefault(idx, []).append(hwnd)
        return groups

    def _retile_displays(self, indices):
        groups = self._hwnds_by_monitor()
        for idx in indices:
            hwnds = groups.get(idx, [])
            if not hwnds:
                self.display_layouts.pop(idx, None)
                continue
            try:
                mon = arrage.pick_monitor_at(idx)
            except Exception as e:
                print(f"Retile failed for display {idx + 1}: {e}")
                continue
            self.display_layouts[idx] = arrage.tile_hwnds(mon, hwnds)

    def _retile(self):
        if not self.hwnds:
            return
        self._retile_displays(set(self.site_monitor.values()))

    def on_close(self):
        if self.is_on:
            arrage.close_windows(list(self.hwnds.values()))
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ToggleApp().run()
