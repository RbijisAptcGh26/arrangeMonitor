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
        self.is_on = False
        self.busy = False

        self.sites = arrage.load_sites()
        self.rows = []
        self._next_row_id = 0
        self.show_address_var = tk.BooleanVar(value=False)
        self._defaults = set(arrage.DisplayOnscreen2Vertically)

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

        self.monitor_canvas = tk.Canvas(
            button_row,
            width=140,
            height=90,
            bg="#f3f4f6",
            highlightthickness=1,
            highlightbackground="#d1d5db",
        )
        self.monitor_canvas.pack(side="left", padx=(0, 12))
        self._draw_monitor_layout()
        self.target_display.trace_add("write", lambda *_: self._draw_monitor_layout())

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

        toggle_bar = ttk.Frame(list_frame)
        toggle_bar.pack(side="top", fill="x", pady=(0, 6))
        self.show_address_cb = ttk.Checkbutton(
            toggle_bar,
            text="Modify address",
            variable=self.show_address_var,
            command=self._apply_address_visibility,
        )
        self.show_address_cb.pack(side="left")

        self.save_btn = ttk.Button(
            toggle_bar,
            text="Save",
            command=self.save_sites,
        )

        footer = ttk.Frame(list_frame)
        footer.pack(side="bottom", fill="x", pady=(6, 0))
        self.add_btn = ttk.Button(
            footer,
            text="+",
            width=3,
            command=self.on_add_row,
        )
        self.add_btn.pack(side="left")

        self.canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        inner = self.inner

        inner.bind(
            "<Configure>",
            lambda *_: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        inner_window = self.canvas.create_window((0, 0), window=inner, anchor="nw")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(inner_window, width=e.width),
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", expand=True, fill="both")

        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"),
        )

        inner.columnconfigure(0, weight=0)
        inner.columnconfigure(1, weight=0)
        inner.columnconfigure(2, weight=0)
        inner.columnconfigure(3, weight=0)
        inner.columnconfigure(4, weight=1)
        inner.columnconfigure(5, weight=0)

        header_check = ttk.Label(inner, text="", font=("Segoe UI", 9, "bold"))
        header_check.grid(row=0, column=0, padx=(0, 6), pady=(0, 4))
        header_name = ttk.Label(inner, text="Site", font=("Segoe UI", 9, "bold"))
        header_name.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 4))
        header_disp = ttk.Label(inner, text="Display", font=("Segoe UI", 9, "bold"))
        header_disp.grid(row=0, column=2, sticky="w", padx=(0, 12), pady=(0, 4))
        header_target = ttk.Label(inner, text="Open on", font=("Segoe UI", 9, "bold"))
        header_target.grid(row=0, column=3, sticky="w", padx=(0, 12), pady=(0, 4))
        self.header_addr = ttk.Label(inner, text="Address", font=("Segoe UI", 9, "bold"))
        self.header_addr.grid(row=0, column=4, sticky="w", padx=(0, 12), pady=(0, 4))
        self.header_del = ttk.Label(inner, text="", font=("Segoe UI", 9, "bold"))
        self.header_del.grid(row=0, column=5, sticky="w", pady=(0, 4))

        for name, url in self.sites:
            self._make_row(name, url)

        self._reflow_grid()
        self._apply_address_visibility()
        self._update_sites_label()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _make_row(self, name, url):
        row_id = self._next_row_id
        self._next_row_id += 1

        check_var = tk.BooleanVar(value=url in self._defaults)
        name_var = tk.StringVar(value=name)
        url_var = tk.StringVar(value=url)
        target_var = tk.IntVar(value=-1)

        cb = ttk.Checkbutton(
            self.inner,
            variable=check_var,
            command=lambda rid=row_id: self.on_site_toggle(rid),
        )
        name_entry = ttk.Entry(self.inner, textvariable=name_var, width=22, state="readonly")
        display_lbl = ttk.Label(self.inner, text="—", foreground="#888", width=12)

        radio_cell = ttk.Frame(self.inner)
        for j in range(3):
            rb = ttk.Radiobutton(
                radio_cell,
                text=f"D{j + 1}",
                variable=target_var,
                value=j,
                command=lambda rid=row_id: self.on_target_changed(rid),
            )
            rb.pack(side="left", padx=2)
            if j >= self.monitor_count:
                rb.state(["disabled"])

        addr_entry = ttk.Entry(self.inner, textvariable=url_var)
        del_btn = ttk.Button(
            self.inner,
            text="✕",
            width=3,
            command=lambda rid=row_id: self.on_delete(rid),
        )

        row = {
            "row_id": row_id,
            "name_var": name_var,
            "url_var": url_var,
            "check_var": check_var,
            "target_var": target_var,
            "display_lbl": display_lbl,
            "addr_entry": addr_entry,
            "name_entry": name_entry,
            "cb": cb,
            "radio_cell": radio_cell,
            "del_btn": del_btn,
        }
        self.rows.append(row)
        return row

    def _reflow_grid(self):
        for i, row in enumerate(self.rows):
            grid_row = i + 1
            row["cb"].grid(row=grid_row, column=0, padx=(0, 6), pady=2)
            row["name_entry"].grid(row=grid_row, column=1, sticky="ew", padx=(0, 12), pady=2)
            row["display_lbl"].grid(row=grid_row, column=2, sticky="w", padx=(0, 12), pady=2)
            row["radio_cell"].grid(row=grid_row, column=3, sticky="w", padx=(0, 12), pady=2)
            row["addr_entry"].grid(row=grid_row, column=4, sticky="ew", padx=(0, 12), pady=2)
            row["del_btn"].grid(row=grid_row, column=5, sticky="w", pady=2)

    def _row(self, row_id):
        for r in self.rows:
            if r["row_id"] == row_id:
                return r
        return None

    def _draw_monitor_layout(self):
        canvas = self.monitor_canvas
        canvas.delete("all")
        try:
            monitors = get_monitors()
        except Exception:
            monitors = []
        if not monitors:
            canvas.create_text(
                70, 45, text="No monitors", fill="#888", font=("Segoe UI", 9)
            )
            return

        cw = int(canvas["width"])
        ch = int(canvas["height"])
        pad = 6
        min_x = min(m.x for m in monitors)
        min_y = min(m.y for m in monitors)
        max_x = max(m.x + m.width for m in monitors)
        max_y = max(m.y + m.height for m in monitors)
        span_w = max_x - min_x or 1
        span_h = max_y - min_y or 1
        scale = min((cw - 2 * pad) / span_w, (ch - 2 * pad) / span_h)
        draw_w = span_w * scale
        draw_h = span_h * scale
        off_x = (cw - draw_w) / 2 - min_x * scale
        off_y = (ch - draw_h) / 2 - min_y * scale

        selected = self.target_display.get()
        for i, m in enumerate(monitors):
            x0 = off_x + m.x * scale
            y0 = off_y + m.y * scale
            x1 = x0 + m.width * scale
            y1 = y0 + m.height * scale
            is_selected = i == selected
            fill = "#16a34a" if is_selected else "#e5e7eb"
            outline = "#15803d" if is_selected else "#9ca3af"
            text_fill = "white" if is_selected else "#374151"
            canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=1)
            canvas.create_text(
                (x0 + x1) / 2,
                (y0 + y1) / 2,
                text=str(i + 1),
                fill=text_fill,
                font=("Segoe UI", 10, "bold"),
            )

    def set_busy(self, busy):
        self.busy = busy
        self.toggle_btn.config(state="disabled" if busy else "normal")
        self._update_refresh_state()

    def _update_refresh_state(self):
        enabled = self.is_on and not self.busy and bool(self.hwnds)
        self.refresh_btn.config(state="normal" if enabled else "disabled")

    def _apply_address_visibility(self):
        show = self.show_address_var.get()
        widgets = [
            self.header_addr,
            self.header_del,
            *(r["addr_entry"] for r in self.rows),
            *(r["del_btn"] for r in self.rows),
        ]
        for w in widgets:
            if show:
                w.grid()
            else:
                w.grid_remove()
        name_state = "normal" if show else "readonly"
        for row in self.rows:
            row["name_entry"].config(state=name_state)
        if show:
            self.save_btn.pack(side="right")
        else:
            self.save_btn.pack_forget()

    def _update_sites_label(self):
        total = len(self.rows)
        displayed = len(self.hwnds)
        parts = [f"{total} sites", f"{displayed} displayed"]
        if displayed > 0:
            displays_used = sorted(set(self.site_monitor.values()))
            if len(displays_used) == 1:
                parts.append(f"Display {displays_used[0] + 1}")
            else:
                parts.append("Displays " + ", ".join(str(d + 1) for d in displays_used))
        self.list_frame.config(text=" | ".join(parts))

    def toggle(self):
        if self.busy:
            return
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on()

    def _selected_row_ids(self):
        return [r["row_id"] for r in self.rows if r["check_var"].get()]

    def _url_of(self, row_id):
        row = self._row(row_id)
        if row is None:
            return ""
        return row["url_var"].get().strip()

    def _set_display_label(self, row_id, monitor_index):
        row = self._row(row_id)
        if row is None:
            return
        lbl = row["display_lbl"]
        if monitor_index is None:
            lbl.config(text="—", foreground="#888")
        else:
            lbl.config(text=f"Display {monitor_index + 1}", foreground="#16a34a")

    def _set_target_radio(self, row_id, monitor_index):
        row = self._row(row_id)
        if row is None:
            return
        row["target_var"].set(-1 if monitor_index is None else monitor_index)

    def _resolve_target(self, row_id):
        row = self._row(row_id)
        if row is None:
            return self.target_display.get()
        per_row = row["target_var"].get()
        if 0 <= per_row < self.monitor_count:
            return per_row
        return self.target_display.get()

    def turn_on(self):
        row_ids = self._selected_row_ids()
        if not row_ids:
            messagebox.showwarning("No sites selected", "Please check at least one site.")
            return
        self.set_busy(True)
        self.status.config(text="...", foreground="#d97706")

        site_targets = [
            (rid, self._url_of(rid), self._resolve_target(rid)) for rid in row_ids
        ]

        def work():
            try:
                opened = {}
                for rid, url, mon_idx in site_targets:
                    if not url:
                        continue
                    hwnd = arrage.open_chrome_window(url)
                    if hwnd is not None:
                        opened[rid] = (hwnd, mon_idx)
                by_monitor = {}
                for rid, (hwnd, mon_idx) in opened.items():
                    by_monitor.setdefault(mon_idx, []).append(hwnd)
                for mon_idx, hwnds in by_monitor.items():
                    try:
                        mon = arrage.pick_monitor_at(mon_idx)
                        arrage.tile_hwnds(mon, hwnds)
                    except Exception as e:
                        print(f"Tile failed for display {mon_idx + 1}: {e}")
                self.root.after(0, self._on_opened, opened, None)
            except Exception as e:
                self.root.after(0, self._on_opened, {}, e)

        threading.Thread(target=work, daemon=True).start()

    def _on_opened(self, opened, err):
        self.set_busy(False)
        if err:
            self.status.config(text="Off", foreground="#dc2626")
            messagebox.showerror("Error", str(err))
            return
        self.hwnds = {rid: hwnd for rid, (hwnd, _) in opened.items()}
        self.site_monitor = {rid: mon_idx for rid, (_, mon_idx) in opened.items()}
        self.is_on = True
        self.toggle_btn.config(text="Off", bg="#16a34a", activebackground="#15803d")
        self.status.config(text="On", foreground="#16a34a")
        for rid, mon_idx in self.site_monitor.items():
            self._set_display_label(rid, mon_idx)
            self._set_target_radio(rid, mon_idx)
        for row in self.rows:
            if row["check_var"].get() and row["row_id"] not in self.hwnds:
                row["check_var"].set(False)
        self._update_refresh_state()
        self._update_sites_label()

    def turn_off(self):
        arrage.close_windows(list(self.hwnds.values()))
        for row in self.rows:
            row["check_var"].set(False)
            self._set_display_label(row["row_id"], None)
            self._set_target_radio(row["row_id"], None)
        self.hwnds = {}
        self.site_monitor = {}
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

    def on_target_changed(self, row_id):
        if not self.is_on or self.busy:
            return
        if row_id not in self.hwnds:
            return
        row = self._row(row_id)
        if row is None:
            return
        new_idx = row["target_var"].get()
        if new_idx < 0 or new_idx == self.site_monitor.get(row_id):
            return
        old_idx = self.site_monitor[row_id]
        self.site_monitor[row_id] = new_idx
        self._set_display_label(row_id, new_idx)
        self._retile_displays({old_idx, new_idx})
        self._update_sites_label()

    def on_site_toggle(self, row_id):
        if not self.is_on or self.busy:
            return
        row = self._row(row_id)
        if row is None:
            return
        if row["check_var"].get():
            if row_id in self.hwnds:
                return
            url = self._url_of(row_id)
            if not url:
                row["check_var"].set(False)
                return
            target = self._resolve_target(row_id)
            self.set_busy(True)
            self.status.config(text="...", foreground="#d97706")

            def work():
                try:
                    hwnd = arrage.open_chrome_window(url)
                    self.root.after(0, self._on_site_added, row_id, hwnd, target, None)
                except Exception as e:
                    self.root.after(0, self._on_site_added, row_id, None, target, e)

            threading.Thread(target=work, daemon=True).start()
        else:
            if row_id not in self.hwnds:
                return
            hwnd = self.hwnds.pop(row_id)
            old_idx = self.site_monitor.pop(row_id, None)
            arrage.close_windows([hwnd])
            self._set_display_label(row_id, None)
            self._set_target_radio(row_id, None)
            if old_idx is not None:
                self._retile_displays({old_idx})
            self.status.config(text="On", foreground="#16a34a")
            self._update_refresh_state()
            self._update_sites_label()

    def _on_site_added(self, row_id, hwnd, monitor_index, err):
        self.set_busy(False)
        row = self._row(row_id)
        if err or hwnd is None:
            if row is not None:
                row["check_var"].set(False)
            self.status.config(text="On", foreground="#16a34a")
            if err:
                messagebox.showerror("Error", str(err))
            else:
                messagebox.showwarning(
                    "Open failed", f"Could not locate Chrome window for {self._url_of(row_id)}"
                )
            return
        if row is None:
            arrage.close_windows([hwnd])
            return
        self.hwnds[row_id] = hwnd
        self.site_monitor[row_id] = monitor_index
        self._set_display_label(row_id, monitor_index)
        self._set_target_radio(row_id, monitor_index)
        self._retile_displays({monitor_index})
        self.status.config(text="On", foreground="#16a34a")
        self._update_refresh_state()
        self._update_sites_label()

    def on_add_row(self):
        row = self._make_row("", "")
        self._reflow_grid()
        self._apply_address_visibility()
        self._update_sites_label()
        self.root.after(50, self._scroll_to_bottom)
        if self.show_address_var.get():
            row["name_entry"].focus_set()

    def _scroll_to_bottom(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def on_delete(self, row_id):
        row = self._row(row_id)
        if row is None:
            return
        if row_id in self.hwnds:
            hwnd = self.hwnds.pop(row_id)
            old_idx = self.site_monitor.pop(row_id, None)
            arrage.close_windows([hwnd])
            if old_idx is not None:
                self._retile_displays({old_idx})
        for key in ("cb", "name_entry", "display_lbl", "radio_cell", "addr_entry", "del_btn"):
            try:
                row[key].destroy()
            except Exception:
                pass
        self.rows.remove(row)
        self._reflow_grid()
        self._update_refresh_state()
        self._update_sites_label()

    def _hwnds_by_monitor(self):
        groups = {}
        for rid, hwnd in self.hwnds.items():
            mon_idx = self.site_monitor.get(rid)
            if mon_idx is None:
                continue
            groups.setdefault(mon_idx, []).append(hwnd)
        return groups

    def _retile_displays(self, indices):
        groups = self._hwnds_by_monitor()
        for mon_idx in indices:
            hwnds = groups.get(mon_idx, [])
            try:
                mon = arrage.pick_monitor_at(mon_idx)
            except Exception as e:
                print(f"Retile failed for display {mon_idx + 1}: {e}")
                continue
            arrage.tile_hwnds(mon, hwnds)

    def _retile(self):
        if not self.hwnds:
            return
        self._retile_displays(set(self.site_monitor.values()))

    def save_sites(self):
        edited = []
        for row in self.rows:
            name = row["name_var"].get().strip()
            url = row["url_var"].get().strip()
            if not name and not url:
                continue
            edited.append((name, url))
        try:
            arrage.save_sites(edited)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return
        self.sites = edited
        self._update_sites_label()
        self.status.config(
            text="Saved" if not self.is_on else "On",
            foreground="#16a34a",
        )

    def on_close(self):
        if self.is_on:
            arrage.close_windows(list(self.hwnds.values()))
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ToggleApp().run()
