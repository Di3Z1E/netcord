import customtkinter as ctk
import threading
from tkinter import messagebox, StringVar
from ..constants import C, FONT_TITLE, FONT_SMALL, FONT_HEADER, FONT_BODY
from ..widgets.card import Card
from ..widgets.ip_entry import IPEntry
from ..widgets.action_button import ActionButton
from ..widgets.danger_button import DangerButton
from ..widgets.toast import ToastNotification
from ..utils import is_admin, validate_ip, validate_prefix, prefix_to_mask, mask_to_prefix
from ..core import get_adapter_info, apply_static, apply_dhcp, apply_extra_ips, get_extra_ips

class ConfigurePage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        # Scrollable container so buttons are never cut off
        S = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        S.pack(fill="both", expand=True)
        self._S = S  # keep reference

        ctk.CTkLabel(S, text="Configure Interface", font=FONT_TITLE,
                     text_color=C["text_bright"]).pack(anchor="w", pady=(0, 16))

        # Mode toggle
        mode_card = Card(S)
        mode_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(mode_card, text="Address Mode", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=18, pady=(14, 6))

        self.mode_var = StringVar(value="dhcp")
        toggle_row = ctk.CTkFrame(mode_card, fg_color="transparent")
        toggle_row.pack(fill="x", padx=14, pady=(0, 14))

        self.dhcp_radio = ctk.CTkRadioButton(
            toggle_row, text="DHCP  (Automatic)", variable=self.mode_var,
            value="dhcp", command=self._toggle_mode,
            text_color=C["text"], fg_color=C["accent"],
            hover_color=C["accent_hover"], font=FONT_BODY
        )
        self.dhcp_radio.pack(side="left", padx=(0, 24))

        self.static_radio = ctk.CTkRadioButton(
            toggle_row, text="Static  (Manual)", variable=self.mode_var,
            value="static", command=self._toggle_mode,
            text_color=C["text"], fg_color=C["accent"],
            hover_color=C["accent_hover"], font=FONT_BODY
        )
        self.static_radio.pack(side="left")

        # Fields card
        self.fields_card = Card(S)
        self.fields_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(self.fields_card, text="Network Settings", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=18, pady=(14, 6))

        grid = ctk.CTkFrame(self.fields_card, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(0, 14))
        grid.columnconfigure((1, 3), weight=1)

        fields = [
            ("IP Address",       "ip",      "192.168.1.100", 0, 0),
            ("Prefix Length",    "prefix",  "24",            0, 2),
            ("Subnet Mask",      "mask",    "255.255.255.0", 1, 0),
            ("Default Gateway",  "gateway", "192.168.1.1",   1, 2),
            ("Primary DNS",      "dns1",    "8.8.8.8",       2, 0),
            ("Secondary DNS",    "dns2",    "8.8.4.4",       2, 2),
        ]
        self.entries: dict[str, IPEntry] = {}
        for label, key, ph, row, col in fields:
            ctk.CTkLabel(grid, text=label, font=FONT_SMALL,
                         text_color=C["text_muted"]).grid(
                row=row * 2, column=col, columnspan=2, sticky="w",
                padx=(0, 16), pady=(6, 2)
            )
            e = IPEntry(grid, placeholder=ph)
            e.grid(row=row * 2 + 1, column=col, columnspan=2, sticky="ew",
                   padx=(0, 20 if col == 0 else 0), pady=(0, 4))
            self.entries[key] = e

        # Prefix ↔ Mask sync
        self.entries["prefix"].bind("<FocusOut>", self._sync_mask)
        self.entries["mask"].bind("<FocusOut>", self._sync_prefix)

        # ── Additional IP Addresses card ──────────────────────────────────────
        self.extra_card = Card(S)

        extra_hdr = ctk.CTkFrame(self.extra_card, fg_color="transparent")
        extra_hdr.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(extra_hdr, text="Additional IP Addresses", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(side="left")
        ctk.CTkButton(
            extra_hdr, text="＋  Add IP", width=100, height=28,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color=C["text_bright"], font=FONT_SMALL, corner_radius=6,
            command=self._add_extra_row
        ).pack(side="right")

        ctk.CTkLabel(
            self.extra_card,
            text="These are applied as secondary IPs on the same adapter (netsh add address).",
            font=FONT_SMALL, text_color=C["text_muted"]
        ).pack(anchor="w", padx=14, pady=(0, 6))

        # Scrollable container for extra IP rows
        self.extra_rows_frame = ctk.CTkScrollableFrame(
            self.extra_card, fg_color="transparent",
            height=120, corner_radius=0
        )
        self.extra_rows_frame.pack(fill="x", padx=14, pady=(0, 12))
        self.extra_rows_frame.columnconfigure((0, 1, 2), weight=1)

        self._extra_rows: list[dict] = []  # list of {frame, ip_entry, mask_entry}

        # DNS presets
        self.dns_card = dns_card = Card(S)
        dns_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(dns_card, text="Quick DNS Presets", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=18, pady=(14, 6))

        presets_row = ctk.CTkFrame(dns_card, fg_color="transparent")
        presets_row.pack(fill="x", padx=14, pady=(0, 14))
        presets = [
            ("Google", "8.8.8.8", "8.8.4.4"),
            ("Cloudflare", "1.1.1.1", "1.0.0.1"),
            ("OpenDNS", "208.67.222.222", "208.67.220.220"),
            ("Quad9", "9.9.9.9", "149.112.112.112"),
        ]
        for name, d1, d2 in presets:
            ctk.CTkButton(
                presets_row, text=name, width=100, height=30,
                fg_color=C["bg_light"], hover_color=C["accent_dim"],
                text_color=C["text"], font=FONT_SMALL, corner_radius=6,
                command=lambda a=d1, b=d2: self._set_dns(a, b)
            ).pack(side="left", padx=(0, 8))

        # Action buttons
        btn_row = ctk.CTkFrame(S, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4, 0))

        ActionButton(btn_row, "  ✓   Apply Settings",
                     command=self._apply).pack(side="left", padx=(0, 10))
        ActionButton(btn_row, "  ↓   Load Current",
                     color=C["bg_light"], hover=C["bg_dark"],
                     command=self._load).pack(side="left", padx=(0, 10))
        DangerButton(btn_row, "  ✗   Reset to DHCP",
                     command=self._reset_dhcp).pack(side="left")

        self._toggle_mode()

    def _add_extra_row(self, ip: str = "", mask: str = ""):
        row_frame = ctk.CTkFrame(self.extra_rows_frame, fg_color=C["bg_light"],
                                  corner_radius=6)
        row_frame.pack(fill="x", pady=(0, 6))
        row_frame.columnconfigure((0, 1), weight=1)

        ip_entry = IPEntry(row_frame, placeholder="IP Address  e.g. 192.168.1.101")
        ip_entry.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=8)
        if ip:
            ip_entry.insert(0, ip)

        mask_entry = IPEntry(row_frame, placeholder="Subnet Mask  e.g. 255.255.255.0")
        mask_entry.grid(row=0, column=1, sticky="ew", padx=(4, 4), pady=8)
        if mask:
            mask_entry.insert(0, mask)

        def remove(rf=row_frame):
            rf.destroy()
            self._extra_rows = [r for r in self._extra_rows if r["frame"] != rf]

        ctk.CTkButton(
            row_frame, text="✕", width=32, height=32,
            fg_color=C["red_dim"], hover_color=C["red"],
            text_color=C["text_bright"], font=FONT_BODY,
            corner_radius=6, command=remove
        ).grid(row=0, column=2, padx=(4, 8), pady=8)

        self._extra_rows.append({"frame": row_frame, "ip": ip_entry, "mask": mask_entry})

    def _clear_extra_rows(self):
        for r in self._extra_rows:
            r["frame"].destroy()
        self._extra_rows = []

    def _get_extra_ips(self) -> list[tuple[str, str]]:
        result = []
        for r in self._extra_rows:
            ip   = r["ip"].get().strip()
            mask = r["mask"].get().strip()
            if validate_ip(ip) and validate_ip(mask):
                result.append((ip, mask))
        return result

    def _toggle_mode(self):
        state = "normal" if self.mode_var.get() == "static" else "disabled"
        for e in self.entries.values():
            e.configure(state=state)
        if self.mode_var.get() == "static":
            self.extra_card.pack(fill="x", pady=(0, 12), before=self.dns_card)
        else:
            self.extra_card.pack_forget()
            self._clear_extra_rows()

    def _sync_mask(self, _=None):
        p = self.entries["prefix"].get().strip()
        if validate_prefix(p):
            self.entries["mask"].configure(state="normal")
            self.entries["mask"].delete(0, "end")
            self.entries["mask"].insert(0, prefix_to_mask(int(p)))
            if self.mode_var.get() == "dhcp":
                self.entries["mask"].configure(state="disabled")

    def _sync_prefix(self, _=None):
        m = self.entries["mask"].get().strip()
        p = mask_to_prefix(m)
        if p is not None:
            self.entries["prefix"].configure(state="normal")
            self.entries["prefix"].delete(0, "end")
            self.entries["prefix"].insert(0, str(p))
            if self.mode_var.get() == "dhcp":
                self.entries["prefix"].configure(state="disabled")

    def _set_dns(self, d1: str, d2: str):
        if self.mode_var.get() == "static":
            for key, val in [("dns1", d1), ("dns2", d2)]:
                self.entries[key].delete(0, "end")
                self.entries[key].insert(0, val)

    def _load(self):
        adapter = self.app.selected_adapter.get()
        if not adapter:
            return
        info = get_adapter_info(adapter)
        if info["dhcp"]:
            self.mode_var.set("dhcp")
        else:
            self.mode_var.set("static")
        self._toggle_mode()

        mapping = {"ip": info["ip"], "prefix": info["prefix"],
                   "mask": info["mask"], "gateway": info["gateway"],
                   "dns1": info["dns1"], "dns2": info["dns2"]}
        was_static = self.mode_var.get() == "static"
        for key, val in mapping.items():
            e = self.entries[key]
            e.configure(state="normal")
            e.delete(0, "end")
            e.insert(0, val)
            if not was_static:
                e.configure(state="disabled")

        self._clear_extra_rows()
        if was_static:
            for eip, emask in get_extra_ips(adapter):
                self._add_extra_row(ip=eip, mask=emask)

        ToastNotification(self.app, "Current settings loaded.")

    def _apply(self):
        adapter = self.app.selected_adapter.get()
        if not adapter:
            messagebox.showerror("Error", "No adapter selected.")
            return

        if self.mode_var.get() == "dhcp":
            self._reset_dhcp()
            return

        ip      = self.entries["ip"].get().strip()
        prefix  = self.entries["prefix"].get().strip()
        gateway = self.entries["gateway"].get().strip()
        dns1    = self.entries["dns1"].get().strip()
        dns2    = self.entries["dns2"].get().strip()

        errors = []
        if not validate_ip(ip):      errors.append("Invalid IP address.")
        if not validate_prefix(prefix): errors.append("Invalid prefix (0-32).")
        if gateway and not validate_ip(gateway): errors.append("Invalid gateway.")
        if dns1 and not validate_ip(dns1): errors.append("Invalid primary DNS.")
        if dns2 and not validate_ip(dns2): errors.append("Invalid secondary DNS.")

        extra_ips = self._get_extra_ips()
        raw_extras = [(r["ip"].get().strip(), r["mask"].get().strip())
                      for r in self._extra_rows]
        for eip, emask in raw_extras:
            if eip or emask:
                if not validate_ip(eip):
                    errors.append(f"Additional IP invalid: '{eip}'")
                if not validate_ip(emask):
                    errors.append(f"Additional mask invalid: '{emask}'")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return

        if not is_admin():
            messagebox.showerror(
                "Permissions Required",
                "Please run NetCord as Administrator to modify network settings."
            )
            return

        def worker():
            ok, err = apply_static(adapter, ip, prefix, gateway, dns1, dns2)
            if ok and extra_ips:
                ok, err = apply_extra_ips(adapter, extra_ips)
            self.after(0, lambda: self._done(ok, err))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, ok: bool, err: str):
        if ok:
            ToastNotification(self.app, "Static IP applied successfully!", success=True)
        else:
            ToastNotification(self.app, f"Failed: {err[:60]}", success=False)

    def _reset_dhcp(self):
        adapter = self.app.selected_adapter.get()
        if not adapter:
            return
        if not is_admin():
            messagebox.showerror("Permissions", "Run as Administrator.")
            return

        def worker():
            ok, err = apply_dhcp(adapter)
            self.after(0, lambda: self._done(ok, err or ""))

        threading.Thread(target=worker, daemon=True).start()

    def on_show(self):
        pass
