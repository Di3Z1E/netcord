import customtkinter as ctk
import threading
from ..constants import C, FONT_TITLE, FONT_SMALL, FONT_HEADER, FONT_MONO
from ..widgets.card import Card
from ..core import get_adapter_info, get_public_ip

class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(hdr, text="Dashboard", font=FONT_TITLE,
                     text_color=C["text_bright"]).pack(side="left")
        self.refresh_btn = ctk.CTkButton(
            hdr, text="⟳  Refresh", width=110, height=32,
            fg_color=C["bg_light"], hover_color=C["bg_dark"],
            text_color=C["text"], font=FONT_SMALL,
            command=self._refresh, corner_radius=6
        )
        self.refresh_btn.pack(side="right")

        # Stats row
        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 16))
        stats_row.columnconfigure((0, 1, 2, 3), weight=1, uniform="s")

        self.stat_cards = {}
        stats = [
            ("Local IP",    "—",  "🖥"),
            ("Gateway",     "—",  "🔀"),
            ("DNS",         "—",  "🔍"),
            ("Public IP",   "—",  "🌐"),
        ]
        for col, (label, val, icon) in enumerate(stats):
            card = Card(stats_row)
            card.grid_propagate(False)
            ctk.CTkLabel(card, text=f"{icon}  {label}", font=FONT_SMALL,
                         text_color=C["text_muted"]).pack(anchor="w", padx=14, pady=(12, 2))
            val_lbl = ctk.CTkLabel(card, text=val, font=("Consolas", 14, "bold"),
                                   text_color=C["text_bright"])
            val_lbl.pack(anchor="w", padx=14, pady=(0, 12))
            card.grid(row=0, column=col, padx=(0, 10) if col < 3 else 0, sticky="nsew")
            stats_row.grid_rowconfigure(0, weight=1)
            self.stat_cards[label] = val_lbl

        # Adapter info card
        self.info_card = Card(self)
        self.info_card.pack(fill="both", expand=True)

        ctk.CTkLabel(self.info_card, text="Adapter Details", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=18, pady=(14, 6))

        self.info_text = ctk.CTkTextbox(
            self.info_card, fg_color=C["input_bg"],
            text_color=C["text"], font=FONT_MONO,
            border_width=0, corner_radius=6, state="disabled"
        )
        self.info_text.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _refresh(self):
        adapter = self.app.selected_adapter.get()
        if not adapter:
            return
        self.refresh_btn.configure(text="⟳  Loading…", state="disabled")

        def worker():
            info = get_adapter_info(adapter)
            pub = get_public_ip()
            self.after(0, lambda: self._update(info, pub))

        threading.Thread(target=worker, daemon=True).start()

    def _update(self, info: dict, pub: str):
        self.stat_cards["Local IP"].configure(text=info["ip"] or "N/A")
        self.stat_cards["Gateway"].configure(text=info["gateway"] or "N/A")
        self.stat_cards["DNS"].configure(text=info["dns1"] or "N/A")
        self.stat_cards["Public IP"].configure(text=pub)

        mode = "DHCP (Auto)" if info["dhcp"] else "Static"
        lines = [
            f"  Adapter          {self.app.selected_adapter.get()}",
            f"  Description      {info['desc']}",
            f"  MAC Address      {info['mac']}",
            f"  Link Speed       {info['speed']}",
            f"  Status           {info['status']}",
            "",
            f"  Mode             {mode}",
            f"  IP Address       {info['ip']}",
            f"  Subnet Mask      {info['mask']}  (/{info['prefix']})",
            f"  Default Gateway  {info['gateway']}",
            f"  Primary DNS      {info['dns1']}",
            f"  Secondary DNS    {info['dns2']}",
        ]
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.configure(state="disabled")
        self.refresh_btn.configure(text="⟳  Refresh", state="normal")

    def on_show(self):
        self._refresh()
