import customtkinter as ctk
import threading
import time
from tkinter import messagebox
from ..constants import C, FONT_TITLE, FONT_SMALL, FONT_HEADER, FONT_MONO
from ..widgets.card import Card
from ..widgets.ip_entry import IPEntry
from ..widgets.action_button import ActionButton
from ..widgets.danger_button import DangerButton
from ..utils import is_admin, run_cmd
from ..core import get_adapter_info, ping_host

class DiagnosticsPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._running = False
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Diagnostics", font=FONT_TITLE,
                     text_color=C["text_bright"]).pack(anchor="w", pady=(0, 16))

        # Ping card
        ping_card = Card(self)
        ping_card.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(ping_card, text="Ping Test", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=18, pady=(14, 6))

        row = ctk.CTkFrame(ping_card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 14))

        self.ping_entry = IPEntry(row, placeholder="hostname or IP  e.g. 8.8.8.8")
        self.ping_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.ping_count = ctk.CTkOptionMenu(
            row, values=["1", "2", "4", "8", "16"],
            fg_color=C["input_bg"], button_color=C["accent"],
            button_hover_color=C["accent_hover"],
            text_color=C["text"], font=FONT_SMALL,
            width=70, height=36, corner_radius=6
        )
        self.ping_count.set("4")
        self.ping_count.pack(side="left", padx=(0, 10))

        self.ping_btn = ActionButton(row, "Ping", width=80,
                                     command=self._run_ping)
        self.ping_btn.pack(side="left")

        # Quick targets
        q_row = ctk.CTkFrame(ping_card, fg_color="transparent")
        q_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkLabel(q_row, text="Quick:", font=FONT_SMALL,
                     text_color=C["text_muted"]).pack(side="left", padx=(0, 8))
        for target in ["8.8.8.8", "1.1.1.1", "gateway", "google.com"]:
            ctk.CTkButton(
                q_row, text=target, width=90, height=26,
                fg_color=C["bg_light"], hover_color=C["accent_dim"],
                text_color=C["text"], font=FONT_SMALL, corner_radius=6,
                command=lambda t=target: self._quick_ping(t)
            ).pack(side="left", padx=(0, 6))

        # Output
        out_card = Card(self)
        out_card.pack(fill="both", expand=True, pady=(0, 12))
        hdr = ctk.CTkFrame(out_card, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(hdr, text="Output", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(side="left")
        ctk.CTkButton(
            hdr, text="Clear", width=60, height=26,
            fg_color=C["bg_light"], hover_color=C["red_dim"],
            text_color=C["text"], font=FONT_SMALL, corner_radius=6,
            command=self._clear
        ).pack(side="right")

        self.output = ctk.CTkTextbox(
            out_card, fg_color=C["input_bg"],
            text_color=C["green"], font=FONT_MONO,
            border_width=0, corner_radius=6, state="disabled"
        )
        self.output.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Network info row
        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.pack(fill="x")
        info_row.columnconfigure((0, 1), weight=1)

        flush_card = Card(info_row)
        flush_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(flush_card, text="DNS Cache", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(flush_card,
                     text="Flush the local DNS resolver cache to resolve\nstale or incorrect DNS entries.",
                     font=FONT_SMALL, text_color=C["text_muted"],
                     justify="left").pack(anchor="w", padx=14, pady=(0, 8))
        DangerButton(flush_card, "Flush DNS Cache",
                     command=self._flush_dns).pack(anchor="w", padx=14, pady=(0, 12))

        release_card = Card(info_row)
        release_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(release_card, text="DHCP Lease", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(release_card,
                     text="Release and renew DHCP lease to get a fresh\nIP address from your router.",
                     font=FONT_SMALL, text_color=C["text_muted"],
                     justify="left").pack(anchor="w", padx=14, pady=(0, 8))
        ActionButton(release_card, "Release & Renew",
                     command=self._renew_dhcp).pack(anchor="w", padx=14, pady=(0, 12))

    def _append(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def _quick_ping(self, target: str):
        if target == "gateway":
            adapter = self.app.selected_adapter.get()
            info = get_adapter_info(adapter)
            target = info["gateway"] or "192.168.1.1"
        self.ping_entry.delete(0, "end")
        self.ping_entry.insert(0, target)
        self._run_ping()

    def _run_ping(self):
        if self._running:
            return
        host = self.ping_entry.get().strip()
        if not host:
            return
        count = int(self.ping_count.get())
        self._running = True
        self.ping_btn.configure(text="…", state="disabled")
        self._append(f"\n── Pinging {host} ({count} packets) ──\n")

        def worker():
            result = ping_host(host, count)
            self.after(0, lambda: self._ping_done(result))

        threading.Thread(target=worker, daemon=True).start()

    def _ping_done(self, result: str):
        self._append(result + "\n")
        self._running = False
        self.ping_btn.configure(text="Ping", state="normal")

    def _flush_dns(self):
        if not is_admin():
            messagebox.showerror("Permissions", "Run as Administrator.")
            return
        self._append("\n── Flushing DNS cache… ──\n")

        def worker():
            out, err, code = run_cmd("ipconfig /flushdns")
            self.after(0, lambda: self._append((out or err) + "\n"))

        threading.Thread(target=worker, daemon=True).start()

    def _renew_dhcp(self):
        if not is_admin():
            messagebox.showerror("Permissions", "Run as Administrator.")
            return
        adapter = self.app.selected_adapter.get()
        self._append(f"\n── Releasing DHCP for '{adapter}'… ──\n")

        def worker():
            out1, _, _ = run_cmd(f'ipconfig /release "{adapter}"')
            time.sleep(1)
            out2, _, _ = run_cmd(f'ipconfig /renew "{adapter}"')
            self.after(0, lambda: self._append(out1 + out2 + "\n"))

        threading.Thread(target=worker, daemon=True).start()

    def on_show(self):
        pass
