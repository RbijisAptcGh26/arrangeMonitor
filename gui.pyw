import threading
import tkinter as tk
from tkinter import messagebox, ttk

from screeninfo import get_monitors

import arrage


class ToggleApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Arrange Monitor")
        self.root.attributes("-topmost", True)

        dpi = self.root.winfo_fpixels("1i")
        w, h = int(13 * dpi), int(5 * dpi)
        self.root.geometry(f"{w}x{h}")
        self._full_minsize = (int(8 * dpi), int(3 * dpi))
        self.root.minsize(*self._full_minsize)
        self._compact_mode = False
        self._saved_geometry = None

        self.hwnds = {}
        self.site_monitor = {}
        self.is_on = False
        self.busy = False

        self.sites = arrage.load_sites()
        self.apps = arrage.load_apps()
        self.settings = arrage.load_settings()
        self._row_settings = self.settings.get("rows", {}) if isinstance(self.settings.get("rows"), dict) else {}
        self._app_row_settings = self.settings.get("apps", {}) if isinstance(self.settings.get("apps"), dict) else {}
        self.rows = []
        self.app_rows = []
        self._next_row_id = 0
        self._next_app_row_id = 0
        self.app_hwnds = {}
        self.app_monitor = {}
        self.show_address_var = tk.BooleanVar(value=bool(self.settings.get("show_address", False)))
        self.show_app_address_var = tk.BooleanVar(value=bool(self.settings.get("show_app_address", False)))
        self._defaults = set(arrage.DisplayOnscreen2Vertically)
        self._edit_snapshot = None
        self._app_edit_snapshot = None
        self.browsers = arrage.detect_browsers()
        self._default_browser = self.browsers[0]["name"] if self.browsers else ""

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

        self.top_frame = ttk.Frame(container)
        self.top_frame.pack(side="top", fill="x")
        self.top_frame.columnconfigure(0, weight=1, uniform="halves")
        self.top_frame.columnconfigure(1, weight=1, uniform="halves")

        self.bottom_buttons = ttk.Frame(container)
        self.bottom_buttons.pack(side="bottom", fill="x", pady=(10, 0))
        self.bottom_buttons.columnconfigure(0, weight=1, uniform="bot_halves")
        self.bottom_buttons.columnconfigure(1, weight=1, uniform="bot_halves")
        self.bottom_buttons_left = ttk.Frame(self.bottom_buttons)
        self.bottom_buttons_left.grid(row=0, column=0, sticky="nsew")

        self.bottom_frame = ttk.Frame(container)
        self.bottom_frame.pack(side="top", expand=True, fill="both", pady=(10, 0))

        self.controls_frame = ttk.Frame(self.top_frame)
        self.controls_frame.grid(row=0, column=0, sticky="nsew")
        self.controls_inner = ttk.Frame(self.controls_frame)
        self.controls_inner.pack(expand=True, fill="x")

        self.list_frame = ttk.LabelFrame(self.top_frame, text="", padding=10)
        self.list_frame.grid(row=0, column=1, sticky="nsew", padx=(20, 0))

        self.apps_wrapper = ttk.Frame(self.bottom_frame)
        self.apps_wrapper.pack(expand=True, fill="both")

        self.display_info = ttk.Label(
            self.controls_inner,
            text=display_text,
            font=("Segoe UI", 11, "bold"),
            foreground="#374151",
        )
        self.display_info.pack(pady=(0, 5))

        default_index = 1 if monitor_count >= 2 else 0
        saved_target = self.settings.get("target_display")
        if isinstance(saved_target, int) and 0 <= saved_target < max(monitor_count, 1):
            default_index = saved_target
        self.target_display = tk.IntVar(value=default_index)

        self.radio_frame = ttk.Frame(self.controls_inner)
        self.radio_frame.pack(pady=(0, 10))

        for i in range(3):
            rb = ttk.Radiobutton(
                self.radio_frame,
                text=f"Display {i + 1}",
                variable=self.target_display,
                value=i,
            )
            rb.pack(side="left", padx=8)
            if i >= monitor_count:
                rb.state(["disabled"])

        self.button_row = ttk.Frame(self.controls_inner)
        self.button_row.pack(pady=(10, 10))

        self.monitor_canvas = tk.Canvas(
            self.button_row,
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
            self.button_row,
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
        self.toggle_btn.pack(side="left")

        bottom_btn_center = ttk.Frame(self.bottom_buttons_left)
        bottom_btn_center.pack()

        bottom_spacer = tk.Frame(bottom_btn_center, width=140 + 12, height=1)
        bottom_spacer.pack(side="left")
        bottom_spacer.pack_propagate(False)

        self.refresh_btn = tk.Button(
            bottom_btn_center,
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
        self.refresh_btn.pack(side="left", padx=(0, 10))

        self.compact_btn = tk.Button(
            bottom_btn_center,
            text="Compact",
            font=("Segoe UI", 12, "bold"),
            width=10,
            height=2,
            bg="#e5e7eb",
            fg="#374151",
            relief="flat",
            activebackground="#d1d5db",
            command=self._toggle_compact,
            cursor="hand2",
        )
        self.compact_btn.pack(side="left")

        self.status = ttk.Label(
            self.controls_inner,
            text="Off",
            font=("Segoe UI", 18, "bold"),
            foreground="#888",
        )
        self.status.pack(pady=(5, 10))

        self.app_frame = ttk.LabelFrame(self.apps_wrapper, text="", padding=10)
        self.app_frame.pack(expand=True, fill="both")
        app_frame = self.app_frame

        app_toggle_bar = ttk.Frame(app_frame)
        app_toggle_bar.pack(side="top", fill="x", pady=(0, 6))
        self.show_app_address_cb = ttk.Checkbutton(
            app_toggle_bar,
            text="Modify path",
            variable=self.show_app_address_var,
            command=self._apply_app_address_visibility,
        )
        self.show_app_address_cb.pack(side="left")

        self.save_app_btn = ttk.Button(
            app_toggle_bar,
            text="Save",
            command=self.save_apps_file,
        )

        app_footer = ttk.Frame(app_frame)
        app_footer.pack(side="bottom", fill="x", pady=(6, 0))
        self.add_app_btn = ttk.Button(
            app_footer,
            text="+",
            width=3,
            command=self.on_add_app_row,
        )

        self.app_canvas = tk.Canvas(app_frame, highlightthickness=0)
        app_scrollbar = ttk.Scrollbar(app_frame, orient="vertical", command=self.app_canvas.yview)
        self.app_inner = ttk.Frame(self.app_canvas)
        app_inner = self.app_inner

        app_inner.bind(
            "<Configure>",
            lambda *_: self.app_canvas.configure(scrollregion=self.app_canvas.bbox("all")),
        )
        app_inner_window = self.app_canvas.create_window((0, 0), window=app_inner, anchor="nw")
        self.app_canvas.bind(
            "<Configure>",
            lambda e: self.app_canvas.itemconfigure(app_inner_window, width=e.width),
        )
        self.app_canvas.configure(yscrollcommand=app_scrollbar.set)

        app_scrollbar.pack(side="right", fill="y")
        self.app_canvas.pack(side="left", expand=True, fill="both")

        app_inner.columnconfigure(0, weight=0)
        app_inner.columnconfigure(1, weight=0)
        app_inner.columnconfigure(2, weight=0)
        app_inner.columnconfigure(3, weight=0)
        app_inner.columnconfigure(4, weight=1)
        app_inner.columnconfigure(5, weight=0)

        ttk.Label(app_inner, text="", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 4)
        )
        ttk.Label(app_inner, text="App", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 4)
        )
        ttk.Label(app_inner, text="Display", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=2, sticky="w", padx=(0, 12), pady=(0, 4)
        )
        ttk.Label(app_inner, text="Open on", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=3, sticky="w", padx=(0, 12), pady=(0, 4)
        )
        self.app_header_addr = ttk.Label(app_inner, text="Path", font=("Segoe UI", 9, "bold"))
        self.app_header_addr.grid(row=0, column=4, sticky="w", padx=(0, 12), pady=(0, 4))
        self.app_header_del = ttk.Label(app_inner, text="", font=("Segoe UI", 9, "bold"))
        self.app_header_del.grid(row=0, column=5, sticky="w", pady=(0, 4))

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


        inner.columnconfigure(0, weight=0)
        inner.columnconfigure(1, weight=0)
        inner.columnconfigure(2, weight=1)
        inner.columnconfigure(3, weight=0)

        self.header_left_panel = ttk.Frame(inner)
        self.header_left_panel.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 4))

        ttk.Label(self.header_left_panel, text="", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Label(self.header_left_panel, text="Open on", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, sticky="w", padx=(0, 12)
        )
        ttk.Label(self.header_left_panel, text="Browser", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=2, sticky="w", padx=(0, 12)
        )
        self.header_name = ttk.Label(inner, text="Site", font=("Segoe UI", 9, "bold"))
        self.header_name.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 4))
        self.header_addr = ttk.Label(inner, text="Address", font=("Segoe UI", 9, "bold"))
        self.header_addr.grid(row=0, column=2, sticky="w", padx=(0, 12), pady=(0, 4))
        self.header_del = ttk.Label(inner, text="", font=("Segoe UI", 9, "bold"))
        self.header_del.grid(row=0, column=3, sticky="w", pady=(0, 4))

        for name, url in self.sites:
            self._make_row(name, url)

        for name, path in self.apps:
            self._make_app_row(name, path)

        self._bind_wheel(self.list_frame, self.canvas)
        self._bind_wheel(self.app_frame, self.app_canvas)

        self._reflow_grid()
        self._reflow_app_grid()
        self._apply_address_visibility()
        self._apply_app_address_visibility()
        self._update_sites_label()
        self._update_apps_label()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _make_row(self, name, url, row_id=None):
        if row_id is None:
            row_id = self._next_row_id
            self._next_row_id += 1
        else:
            self._next_row_id = max(self._next_row_id, row_id + 1)

        saved = self._row_settings.get(url, {}) if url else {}
        if "checked" in saved:
            initial_checked = bool(saved.get("checked"))
        else:
            initial_checked = url in self._defaults
        saved_browsers = saved.get("browsers")
        saved_target = saved.get("target")

        check_var = tk.BooleanVar(value=initial_checked)
        name_var = tk.StringVar(value=name)
        url_var = tk.StringVar(value=url)
        target_var = tk.IntVar(
            value=saved_target if isinstance(saved_target, int) and 0 <= saved_target < self.monitor_count else -1
        )
        if isinstance(saved_browsers, list) and self.browsers:
            saved_set = set(saved_browsers)
            browser_vars = {
                b["name"]: tk.BooleanVar(value=(b["name"] in saved_set))
                for b in self.browsers
            }
        else:
            browser_vars = {
                b["name"]: tk.BooleanVar(value=(b is self.browsers[0]))
                for b in self.browsers
            }

        left_panel = ttk.Frame(self.inner)

        cb = ttk.Checkbutton(
            left_panel,
            variable=check_var,
            command=lambda rid=row_id: self.on_site_toggle(rid),
        )
        name_entry = ttk.Entry(self.inner, textvariable=name_var, width=22, state="readonly")

        browser_cell = ttk.Frame(left_panel)
        if self.browsers:
            for b in self.browsers:
                self._make_browser_icon(browser_cell, b, browser_vars[b["name"]], row_id)
        else:
            ttk.Label(browser_cell, text="—", foreground="#888").pack(side="left")

        radio_cell = ttk.Frame(left_panel)
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
            "browser_vars": browser_vars,
            "addr_entry": addr_entry,
            "name_entry": name_entry,
            "cb": cb,
            "browser_cell": browser_cell,
            "radio_cell": radio_cell,
            "del_btn": del_btn,
            "left_panel": left_panel,
        }
        self.rows.append(row)
        for w in (left_panel, name_entry, addr_entry, del_btn):
            self._bind_wheel(w, self.canvas)
        return row

    def _reflow_grid(self):
        for i, row in enumerate(self.rows):
            grid_row = i + 1
            row["left_panel"].grid(row=grid_row, column=0, sticky="w", padx=(0, 12), pady=2)
            row["cb"].grid(row=0, column=0, padx=(0, 6))
            row["radio_cell"].grid(row=0, column=1, sticky="w", padx=(0, 12))
            row["browser_cell"].grid(row=0, column=2, sticky="w", padx=(0, 12))
            row["name_entry"].grid(row=grid_row, column=1, sticky="ew", padx=(0, 12), pady=2)
            row["addr_entry"].grid(row=grid_row, column=2, sticky="ew", padx=(0, 12), pady=2)
            row["del_btn"].grid(row=grid_row, column=3, sticky="w", pady=2)

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
            tag = f"mon-{i}"
            canvas.create_rectangle(
                x0, y0, x1, y1, fill=fill, outline=outline, width=1, tags=(tag,)
            )
            canvas.create_text(
                (x0 + x1) / 2,
                (y0 + y1) / 2,
                text=str(i + 1),
                fill=text_fill,
                font=("Segoe UI", 10, "bold"),
                tags=(tag,),
            )
            canvas.tag_bind(tag, "<Button-1>", lambda *_, idx=i: self._select_monitor(idx))
            canvas.tag_bind(tag, "<Enter>", lambda *_: canvas.config(cursor="hand2"))
            canvas.tag_bind(tag, "<Leave>", lambda *_: canvas.config(cursor=""))

    def _select_monitor(self, idx):
        if 0 <= idx < self.monitor_count:
            self.target_display.set(idx)
            for row in self.rows:
                row["target_var"].set(idx)
                self.on_target_changed(row["row_id"])
            for row in self.app_rows:
                row["target_var"].set(idx)
                self.on_app_target_changed(row["row_id"])

    def _make_browser_icon(self, parent, browser, var, row_id):
        size = 22
        try:
            bg = ttk.Style().lookup("TFrame", "background") or "#f0f0f0"
        except Exception:
            bg = "#f0f0f0"
        canvas = tk.Canvas(
            parent,
            width=size,
            height=size,
            highlightthickness=0,
            bg=bg,
            cursor="hand2",
        )
        canvas.pack(side="left", padx=2)

        def draw(*_):
            canvas.delete("all")
            if var.get():
                canvas.create_rectangle(
                    0, 0, size - 1, size - 1, outline="#16a34a", width=2
                )
            self._draw_browser_glyph(canvas, browser["name"], size, bg)

        def on_click(*_):
            new_state = not var.get()
            var.set(new_state)
            self.on_browser_toggled(row_id, browser, new_state)

        canvas.bind("<Button-1>", on_click)
        var.trace_add("write", draw)
        draw()
        return canvas

    def _draw_browser_glyph(self, canvas, name, size, bg):
        cx = cy = size / 2
        if name == "Chrome":
            canvas.create_arc(3, 3, size - 3, size - 3, start=60, extent=120,
                              fill="#EA4335", outline="")
            canvas.create_arc(3, 3, size - 3, size - 3, start=180, extent=120,
                              fill="#34A853", outline="")
            canvas.create_arc(3, 3, size - 3, size - 3, start=300, extent=120,
                              fill="#FBBC04", outline="")
            canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                               fill="#4285F4", outline="white", width=1)
        elif name == "Edge":
            canvas.create_oval(3, 3, size - 3, size - 3, fill="#0078D7", outline="")
            canvas.create_arc(6, 6, size - 6, size - 6, start=20, extent=200,
                              style="arc", outline="white", width=2)
        elif name == "Firefox":
            canvas.create_oval(3, 3, size - 3, size - 3, fill="#FF7139", outline="")
            canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3,
                               fill="#0060DF", outline="")
        elif name == "Brave":
            points = [cx, 3, size - 3, 7, size - 5, size - 4,
                      cx, size - 3, 5, size - 4, 3, 7]
            canvas.create_polygon(points, fill="#FB542B", outline="")
            canvas.create_polygon(
                [cx, 8, cx + 3, 11, cx + 1, size - 7, cx, size - 6,
                 cx - 1, size - 7, cx - 3, 11],
                fill="#ffffff", outline="",
            )
        elif name == "Opera":
            canvas.create_oval(3, 3, size - 3, size - 3, fill="#FF1B2D", outline="")
            canvas.create_oval(cx - 2, 6, cx + 2, size - 6, fill=bg, outline="")
        else:
            canvas.create_oval(3, 3, size - 3, size - 3, fill="#9ca3af", outline="")
            canvas.create_text(cx, cy, text=name[:1], fill="white",
                               font=("Segoe UI", 8, "bold"))

    def set_busy(self, busy):
        self.busy = busy
        self.toggle_btn.config(state="disabled" if busy else "normal")
        self._update_refresh_state()

    def _update_refresh_state(self):
        has_windows = bool(self.hwnds) or bool(self.app_hwnds)
        enabled = not self.busy and has_windows
        self.refresh_btn.config(state="normal" if enabled else "disabled")

    def _apply_address_visibility(self):
        show = self.show_address_var.get()
        if show and self._edit_snapshot is None:
            self._take_edit_snapshot()
        elif not show and self._edit_snapshot is not None:
            self._revert_to_snapshot()
            self._edit_snapshot = None
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
            self.add_btn.pack(side="left")
        else:
            self.save_btn.pack_forget()
            self.add_btn.pack_forget()

    def _take_edit_snapshot(self):
        self._edit_snapshot = [
            (r["row_id"], r["name_var"].get(), r["url_var"].get())
            for r in self.rows
        ]

    def _revert_to_snapshot(self):
        snapshot = self._edit_snapshot or []
        snapshot_ids = {rid for rid, _, _ in snapshot}
        current_ids = {r["row_id"] for r in self.rows}

        for row in list(self.rows):
            if row["row_id"] not in snapshot_ids:
                self._destroy_row(row)

        rows_by_id = {r["row_id"]: r for r in self.rows}
        for rid, name, url in snapshot:
            if rid in rows_by_id:
                rows_by_id[rid]["name_var"].set(name)
                rows_by_id[rid]["url_var"].set(url)

        for rid, name, url in snapshot:
            if rid not in current_ids:
                self._make_row(name, url, row_id=rid)

        rows_by_id = {r["row_id"]: r for r in self.rows}
        self.rows = [rows_by_id[rid] for rid, _, _ in snapshot if rid in rows_by_id]

        self._reflow_grid()
        self._update_refresh_state()
        self._update_sites_label()

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
        return

    def _scroll_canvas(self, canvas, event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _bind_wheel(self, widget, canvas):
        widget.bind("<MouseWheel>", lambda e, c=canvas: self._scroll_canvas(c, e))
        for child in widget.winfo_children():
            self._bind_wheel(child, canvas)

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

    def _browsers_for(self, row_id):
        row = self._row(row_id)
        if row is None or not self.browsers:
            return []
        vars_map = row.get("browser_vars", {})
        return [b for b in self.browsers if vars_map.get(b["name"]) and vars_map[b["name"]].get()]

    def turn_on(self):
        row_ids = self._selected_row_ids()
        if not row_ids:
            messagebox.showwarning("No sites selected", "Please check at least one site.")
            return
        self.set_busy(True)
        self.status.config(text="...", foreground="#d97706")

        site_targets = [
            (rid, self._url_of(rid), self._resolve_target(rid), self._browsers_for(rid))
            for rid in row_ids
        ]

        def work():
            try:
                opened = {}
                for rid, url, mon_idx, browsers in site_targets:
                    if not url or not browsers:
                        continue
                    per_row = {}
                    for browser in browsers:
                        hwnd = arrage.open_browser_window(browser, url)
                        if hwnd is not None:
                            per_row[browser["name"]] = hwnd
                    if per_row:
                        opened[rid] = (per_row, mon_idx)
                by_monitor = {}
                for rid, (per_row, mon_idx) in opened.items():
                    by_monitor.setdefault(mon_idx, []).extend(per_row.values())
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
        self.hwnds = {rid: dict(per_row) for rid, (per_row, _) in opened.items()}
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
        all_hwnds = [hwnd for per_row in self.hwnds.values() for hwnd in per_row.values()]
        arrage.close_windows(all_hwnds)
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
        if self.busy or (not self.hwnds and not self.app_hwnds):
            return
        self._retile()
        if self.is_on:
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
            browsers = self._browsers_for(row_id)
            if not browsers:
                row["check_var"].set(False)
                messagebox.showwarning("No browser", "Select at least one browser for this site.")
                return
            target = self._resolve_target(row_id)
            self.set_busy(True)
            self.status.config(text="...", foreground="#d97706")

            def work():
                try:
                    per_row = {}
                    for browser in browsers:
                        hwnd = arrage.open_browser_window(browser, url)
                        if hwnd is not None:
                            per_row[browser["name"]] = hwnd
                    self.root.after(0, self._on_site_added, row_id, per_row, target, None)
                except Exception as e:
                    self.root.after(0, self._on_site_added, row_id, {}, target, e)

            threading.Thread(target=work, daemon=True).start()
        else:
            if row_id not in self.hwnds:
                return
            per_row = self.hwnds.pop(row_id)
            old_idx = self.site_monitor.pop(row_id, None)
            arrage.close_windows(list(per_row.values()))
            self._set_display_label(row_id, None)
            self._set_target_radio(row_id, None)
            if old_idx is not None:
                self._retile_displays({old_idx})
            self.status.config(text="On", foreground="#16a34a")
            self._update_refresh_state()
            self._update_sites_label()

    def _on_site_added(self, row_id, per_row, monitor_index, err):
        self.set_busy(False)
        row = self._row(row_id)
        if err or not per_row:
            if row is not None:
                row["check_var"].set(False)
            if per_row:
                arrage.close_windows(list(per_row.values()))
            self.status.config(text="On", foreground="#16a34a")
            if err:
                messagebox.showerror("Error", str(err))
            else:
                messagebox.showwarning(
                    "Open failed", f"Could not locate browser window for {self._url_of(row_id)}"
                )
            return
        if row is None:
            arrage.close_windows(list(per_row.values()))
            return
        self.hwnds[row_id] = dict(per_row)
        self.site_monitor[row_id] = monitor_index
        self._set_display_label(row_id, monitor_index)
        self._set_target_radio(row_id, monitor_index)
        self._retile_displays({monitor_index})
        self.status.config(text="On", foreground="#16a34a")
        self._update_refresh_state()
        self._update_sites_label()

    def on_browser_toggled(self, row_id, browser, enabled):
        if not self.is_on or self.busy:
            return
        if row_id not in self.hwnds:
            return
        per_row = self.hwnds[row_id]
        name = browser["name"]
        mon_idx = self.site_monitor.get(row_id)
        if enabled:
            if name in per_row:
                return
            url = self._url_of(row_id)
            if not url:
                return
            self.set_busy(True)
            self.status.config(text="...", foreground="#d97706")

            def work():
                try:
                    hwnd = arrage.open_browser_window(browser, url)
                    self.root.after(0, self._on_browser_opened, row_id, name, hwnd, mon_idx, None)
                except Exception as e:
                    self.root.after(0, self._on_browser_opened, row_id, name, None, mon_idx, e)

            threading.Thread(target=work, daemon=True).start()
        else:
            hwnd = per_row.pop(name, None)
            if hwnd is None:
                return
            arrage.close_windows([hwnd])
            if not per_row:
                self.hwnds.pop(row_id, None)
                old_idx = self.site_monitor.pop(row_id, None)
                row = self._row(row_id)
                if row is not None:
                    row["check_var"].set(False)
                self._set_display_label(row_id, None)
                self._set_target_radio(row_id, None)
                if old_idx is not None:
                    self._retile_displays({old_idx})
            elif mon_idx is not None:
                self._retile_displays({mon_idx})
            self._update_refresh_state()
            self._update_sites_label()

    def _on_browser_opened(self, row_id, browser_name, hwnd, monitor_index, err):
        self.set_busy(False)
        if err or hwnd is None:
            row = self._row(row_id)
            if row is not None:
                var = row.get("browser_vars", {}).get(browser_name)
                if var is not None:
                    var.set(False)
            self.status.config(text="On", foreground="#16a34a")
            if err:
                messagebox.showerror("Error", str(err))
            else:
                messagebox.showwarning(
                    "Open failed", f"Could not locate {browser_name} window"
                )
            return
        if row_id not in self.hwnds:
            arrage.close_windows([hwnd])
            return
        self.hwnds[row_id][browser_name] = hwnd
        if monitor_index is not None:
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

    def _destroy_row(self, row):
        row_id = row["row_id"]
        retile_idx = None
        if row_id in self.hwnds:
            per_row = self.hwnds.pop(row_id)
            retile_idx = self.site_monitor.pop(row_id, None)
            try:
                arrage.close_windows(list(per_row.values()))
            except Exception:
                pass
        for key in ("left_panel", "name_entry", "addr_entry", "del_btn"):
            try:
                row[key].destroy()
            except Exception:
                pass
        if row in self.rows:
            self.rows.remove(row)
        if retile_idx is not None:
            self._retile_displays({retile_idx})

    def on_delete(self, row_id):
        row = self._row(row_id)
        if row is None:
            return
        self._destroy_row(row)
        self._reflow_grid()
        self._update_refresh_state()
        self._update_sites_label()

    def _hwnds_by_monitor(self):
        groups = {}
        for rid, per_row in self.hwnds.items():
            mon_idx = self.site_monitor.get(rid)
            if mon_idx is None:
                continue
            groups.setdefault(mon_idx, []).extend(per_row.values())
        for rid, hwnd in self.app_hwnds.items():
            mon_idx = self.app_monitor.get(rid)
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
        indices = set(self.site_monitor.values()) | set(self.app_monitor.values())
        if not indices:
            return
        self._retile_displays(indices)

    def save_sites(self):
        for row in list(self.rows):
            name = row["name_var"].get().strip()
            url = row["url_var"].get().strip()
            if not name or not url:
                self._destroy_row(row)
        self._reflow_grid()

        edited = [
            (r["name_var"].get().strip(), r["url_var"].get().strip())
            for r in self.rows
        ]
        try:
            arrage.save_sites(edited)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return
        self.sites = edited
        if self.show_address_var.get():
            self._take_edit_snapshot()
        else:
            self._edit_snapshot = None
        self._update_refresh_state()
        self._update_sites_label()
        self.status.config(
            text="Saved" if not self.is_on else "On",
            foreground="#16a34a",
        )

    def _make_app_row(self, name, path, row_id=None):
        if row_id is None:
            row_id = self._next_app_row_id
            self._next_app_row_id += 1
        else:
            self._next_app_row_id = max(self._next_app_row_id, row_id + 1)

        saved = self._app_row_settings.get(path, {}) if path else {}
        saved_target = saved.get("target")
        initial_checked = bool(saved.get("checked", False))

        check_var = tk.BooleanVar(value=initial_checked)
        name_var = tk.StringVar(value=name)
        path_var = tk.StringVar(value=path)
        target_var = tk.IntVar(
            value=saved_target if isinstance(saved_target, int) and 0 <= saved_target < self.monitor_count else -1
        )

        cb = ttk.Checkbutton(
            self.app_inner,
            variable=check_var,
            command=lambda rid=row_id: self.on_app_toggle(rid),
        )
        name_entry = ttk.Entry(self.app_inner, textvariable=name_var, width=22, state="readonly")
        display_lbl = ttk.Label(self.app_inner, text="—", foreground="#888", width=12)

        radio_cell = ttk.Frame(self.app_inner)
        for j in range(3):
            rb = ttk.Radiobutton(
                radio_cell,
                text=f"D{j + 1}",
                variable=target_var,
                value=j,
                command=lambda rid=row_id: self.on_app_target_changed(rid),
            )
            rb.pack(side="left", padx=2)
            if j >= self.monitor_count:
                rb.state(["disabled"])

        path_entry = ttk.Entry(self.app_inner, textvariable=path_var)
        del_btn = ttk.Button(
            self.app_inner,
            text="✕",
            width=3,
            command=lambda rid=row_id: self.on_app_delete(rid),
        )

        row = {
            "row_id": row_id,
            "name_var": name_var,
            "path_var": path_var,
            "check_var": check_var,
            "target_var": target_var,
            "display_lbl": display_lbl,
            "path_entry": path_entry,
            "name_entry": name_entry,
            "cb": cb,
            "radio_cell": radio_cell,
            "del_btn": del_btn,
        }
        self.app_rows.append(row)
        for w in (cb, name_entry, display_lbl, radio_cell, path_entry, del_btn):
            self._bind_wheel(w, self.app_canvas)
        return row

    def _reflow_app_grid(self):
        for i, row in enumerate(self.app_rows):
            grid_row = i + 1
            row["cb"].grid(row=grid_row, column=0, padx=(0, 6), pady=2)
            row["name_entry"].grid(row=grid_row, column=1, sticky="ew", padx=(0, 12), pady=2)
            row["display_lbl"].grid(row=grid_row, column=2, sticky="w", padx=(0, 12), pady=2)
            row["radio_cell"].grid(row=grid_row, column=3, sticky="w", padx=(0, 12), pady=2)
            row["path_entry"].grid(row=grid_row, column=4, sticky="ew", padx=(0, 12), pady=2)
            row["del_btn"].grid(row=grid_row, column=5, sticky="w", pady=2)

    def _app_row(self, row_id):
        for r in self.app_rows:
            if r["row_id"] == row_id:
                return r
        return None

    def _apply_app_address_visibility(self):
        show = self.show_app_address_var.get()
        if show and self._app_edit_snapshot is None:
            self._take_app_edit_snapshot()
        elif not show and self._app_edit_snapshot is not None:
            self._revert_app_to_snapshot()
            self._app_edit_snapshot = None
        widgets = [
            self.app_header_addr,
            self.app_header_del,
            *(r["path_entry"] for r in self.app_rows),
            *(r["del_btn"] for r in self.app_rows),
        ]
        for w in widgets:
            if show:
                w.grid()
            else:
                w.grid_remove()
        name_state = "normal" if show else "readonly"
        for row in self.app_rows:
            row["name_entry"].config(state=name_state)
        if show:
            self.save_app_btn.pack(side="right")
            self.add_app_btn.pack(side="left")
        else:
            self.save_app_btn.pack_forget()
            self.add_app_btn.pack_forget()

    def _take_app_edit_snapshot(self):
        self._app_edit_snapshot = [
            (r["row_id"], r["name_var"].get(), r["path_var"].get())
            for r in self.app_rows
        ]

    def _revert_app_to_snapshot(self):
        snapshot = self._app_edit_snapshot or []
        snapshot_ids = {rid for rid, _, _ in snapshot}
        current_ids = {r["row_id"] for r in self.app_rows}

        for row in list(self.app_rows):
            if row["row_id"] not in snapshot_ids:
                self._destroy_app_row(row)

        rows_by_id = {r["row_id"]: r for r in self.app_rows}
        for rid, name, path in snapshot:
            if rid in rows_by_id:
                rows_by_id[rid]["name_var"].set(name)
                rows_by_id[rid]["path_var"].set(path)

        for rid, name, path in snapshot:
            if rid not in current_ids:
                self._make_app_row(name, path, row_id=rid)

        rows_by_id = {r["row_id"]: r for r in self.app_rows}
        self.app_rows = [rows_by_id[rid] for rid, _, _ in snapshot if rid in rows_by_id]
        self._reflow_app_grid()
        self._update_apps_label()

    def _update_apps_label(self):
        total = len(self.app_rows)
        displayed = len(self.app_hwnds)
        parts = [f"{total} apps", f"{displayed} displayed"]
        self.app_frame.config(text=" | ".join(parts))

    def _path_of(self, row_id):
        row = self._app_row(row_id)
        if row is None:
            return ""
        return row["path_var"].get().strip()

    def _set_app_display_label(self, row_id, monitor_index):
        row = self._app_row(row_id)
        if row is None:
            return
        lbl = row["display_lbl"]
        if monitor_index is None:
            lbl.config(text="—", foreground="#888")
        else:
            lbl.config(text=f"Display {monitor_index + 1}", foreground="#16a34a")

    def _set_app_target_radio(self, row_id, monitor_index):
        row = self._app_row(row_id)
        if row is None:
            return
        row["target_var"].set(-1 if monitor_index is None else monitor_index)

    def _resolve_app_target(self, row_id):
        row = self._app_row(row_id)
        if row is None:
            return self.target_display.get()
        per_row = row["target_var"].get()
        if 0 <= per_row < self.monitor_count:
            return per_row
        return self.target_display.get()

    def on_app_toggle(self, row_id):
        if self.busy:
            return
        row = self._app_row(row_id)
        if row is None:
            return
        if row["check_var"].get():
            if row_id in self.app_hwnds:
                return
            path = self._path_of(row_id)
            if not path:
                row["check_var"].set(False)
                return
            target = self._resolve_app_target(row_id)
            self.set_busy(True)
            self.status.config(text="...", foreground="#d97706")

            def work():
                try:
                    hwnd = arrage.open_app_window(path)
                    self.root.after(0, self._on_app_added, row_id, hwnd, target, None)
                except Exception as e:
                    self.root.after(0, self._on_app_added, row_id, None, target, e)

            threading.Thread(target=work, daemon=True).start()
        else:
            if row_id not in self.app_hwnds:
                return
            hwnd = self.app_hwnds.pop(row_id)
            old_idx = self.app_monitor.pop(row_id, None)
            arrage.close_windows([hwnd])
            self._set_app_display_label(row_id, None)
            self._set_app_target_radio(row_id, None)
            if old_idx is not None:
                self._retile_displays({old_idx})
            self.status.config(text="On" if self.is_on else "Off",
                               foreground="#16a34a" if self.is_on else "#888")
            self._update_refresh_state()
            self._update_apps_label()

    def _on_app_added(self, row_id, hwnd, monitor_index, err):
        self.set_busy(False)
        row = self._app_row(row_id)
        if err or hwnd is None:
            if row is not None:
                row["check_var"].set(False)
            self.status.config(text="On" if self.is_on else "Off",
                               foreground="#16a34a" if self.is_on else "#888")
            if err:
                messagebox.showerror("Error", str(err))
            else:
                messagebox.showwarning(
                    "Launch failed", f"Could not locate window for {self._path_of(row_id)}"
                )
            return
        if row is None:
            arrage.close_windows([hwnd])
            return
        self.app_hwnds[row_id] = hwnd
        self.app_monitor[row_id] = monitor_index
        self._set_app_display_label(row_id, monitor_index)
        self._set_app_target_radio(row_id, monitor_index)
        self._retile_displays({monitor_index})
        self.status.config(text="On" if self.is_on else "Off",
                           foreground="#16a34a" if self.is_on else "#888")
        self._update_refresh_state()
        self._update_apps_label()

    def on_app_target_changed(self, row_id):
        if self.busy or row_id not in self.app_hwnds:
            return
        row = self._app_row(row_id)
        if row is None:
            return
        new_idx = row["target_var"].get()
        if new_idx < 0 or new_idx == self.app_monitor.get(row_id):
            return
        old_idx = self.app_monitor[row_id]
        self.app_monitor[row_id] = new_idx
        self._set_app_display_label(row_id, new_idx)
        self._retile_displays({old_idx, new_idx})
        self._update_apps_label()

    def on_add_app_row(self):
        row = self._make_app_row("", "")
        self._reflow_app_grid()
        self._apply_app_address_visibility()
        self._update_apps_label()
        self.root.after(50, self._scroll_app_to_bottom)
        if self.show_app_address_var.get():
            row["name_entry"].focus_set()

    def _scroll_app_to_bottom(self):
        self.app_canvas.update_idletasks()
        self.app_canvas.yview_moveto(1.0)

    def _destroy_app_row(self, row):
        row_id = row["row_id"]
        retile_idx = None
        if row_id in self.app_hwnds:
            hwnd = self.app_hwnds.pop(row_id)
            retile_idx = self.app_monitor.pop(row_id, None)
            try:
                arrage.close_windows([hwnd])
            except Exception:
                pass
        for key in ("cb", "name_entry", "display_lbl", "radio_cell", "path_entry", "del_btn"):
            try:
                row[key].destroy()
            except Exception:
                pass
        if row in self.app_rows:
            self.app_rows.remove(row)
        if retile_idx is not None:
            self._retile_displays({retile_idx})

    def on_app_delete(self, row_id):
        row = self._app_row(row_id)
        if row is None:
            return
        self._destroy_app_row(row)
        self._reflow_app_grid()
        self._update_refresh_state()
        self._update_apps_label()

    def save_apps_file(self):
        for row in list(self.app_rows):
            name = row["name_var"].get().strip()
            path = row["path_var"].get().strip()
            if not name or not path:
                self._destroy_app_row(row)
        self._reflow_app_grid()

        edited = [
            (r["name_var"].get().strip(), r["path_var"].get().strip())
            for r in self.app_rows
        ]
        try:
            arrage.save_apps(edited)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
            return
        self.apps = edited
        if self.show_app_address_var.get():
            self._take_app_edit_snapshot()
        else:
            self._app_edit_snapshot = None
        self._update_refresh_state()
        self._update_apps_label()
        self.status.config(
            text="Saved" if not self.is_on else "On",
            foreground="#16a34a",
        )

    def _collect_settings(self):
        rows = {}
        for r in self.rows:
            url = r["url_var"].get().strip()
            if not url:
                continue
            target = r["target_var"].get()
            rows[url] = {
                "checked": bool(r["check_var"].get()),
                "browsers": [name for name, var in r.get("browser_vars", {}).items() if var.get()],
                "target": target if 0 <= target < self.monitor_count else -1,
            }
        apps = {}
        for r in self.app_rows:
            path = r["path_var"].get().strip()
            if not path:
                continue
            target = r["target_var"].get()
            apps[path] = {
                "checked": bool(r["check_var"].get()),
                "target": target if 0 <= target < self.monitor_count else -1,
            }
        return {
            "target_display": int(self.target_display.get()),
            "show_address": bool(self.show_address_var.get()),
            "show_app_address": bool(self.show_app_address_var.get()),
            "rows": rows,
            "apps": apps,
        }

    def _toggle_compact(self):
        if self._compact_mode:
            self._exit_compact()
        else:
            self._enter_compact()

    def _enter_compact(self):
        self.root.update_idletasks()
        self._saved_geometry = self.root.geometry()

        self.display_info.pack_forget()
        self.radio_frame.pack_forget()
        self.list_frame.grid_remove()
        self.bottom_frame.pack_forget()
        self.controls_frame.grid_configure(columnspan=2)

        self.compact_btn.config(
            text="Expand",
            bg="#fde68a",
            fg="#78350f",
            activebackground="#fcd34d",
        )
        self._compact_mode = True

        self.root.update_idletasks()
        req_w = max(self.button_row.winfo_reqwidth() + 60, 600)
        req_h = (
            self.button_row.winfo_reqheight()
            + self.status.winfo_reqheight()
            + self.bottom_buttons.winfo_reqheight()
            + 60
        )
        self.root.minsize(req_w, req_h)
        self.root.geometry(f"{req_w}x{req_h}")

    def _exit_compact(self):
        self._compact_mode = False
        self.compact_btn.config(
            text="Compact",
            bg="#e5e7eb",
            fg="#374151",
            activebackground="#d1d5db",
        )

        self.controls_frame.grid_configure(columnspan=1)
        self.list_frame.grid()
        self.bottom_frame.pack(side="top", expand=True, fill="both", pady=(10, 0))
        self.display_info.pack(in_=self.controls_inner, before=self.button_row, pady=(0, 5))
        self.radio_frame.pack(in_=self.controls_inner, before=self.button_row, pady=(0, 10))

        self.root.minsize(*self._full_minsize)
        if self._saved_geometry:
            self.root.geometry(self._saved_geometry)

    def on_close(self):
        try:
            arrage.save_settings(self._collect_settings())
        except Exception as e:
            print(f"Failed to save settings: {e}")
        all_hwnds = [hwnd for per_row in self.hwnds.values() for hwnd in per_row.values()]
        all_hwnds.extend(self.app_hwnds.values())
        if all_hwnds:
            arrage.close_windows(all_hwnds)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ToggleApp().run()
