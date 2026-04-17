import customtkinter as ctk
import os
import json
from tkinter import messagebox
from ..constants import C, FONT_TITLE, FONT_SMALL, FONT_HEADER, FONT_BODY
from ..widgets.card import Card
from ..widgets.action_button import ActionButton
from ..widgets.toast import ToastNotification
from ..core import get_adapter_info, get_extra_ips

class ProfilesPage(ctk.CTkFrame):
    """Save and load network configuration profiles."""
    PROFILES_FILE = os.path.join(os.path.expanduser("~"), ".netcord_profiles.json")

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.profiles: dict = {}
        self._load_profiles()
        self._build()

    def _load_profiles(self):
        if os.path.exists(self.PROFILES_FILE):
            try:
                with open(self.PROFILES_FILE) as f:
                    self.profiles = json.load(f)
                for name, cfg in self.profiles.items():
                    if not isinstance(cfg.get("dhcp"), bool):
                        cfg["dhcp"] = not bool(cfg.get("ip", ""))
            except Exception:
                self.profiles = {}

    def _save_profiles(self):
        with open(self.PROFILES_FILE, "w") as f:
            json.dump(self.profiles, f, indent=2)

    def _build(self):
        ctk.CTkLabel(self, text="Network Profiles", font=FONT_TITLE,
                     text_color=C["text_bright"]).pack(anchor="w", pady=(0, 16))

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 12))
        top.columnconfigure((0, 1), weight=1)

        # Save card
        save_card = Card(top)
        save_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(save_card, text="Save Current Config", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=14, pady=(14, 6))
        ctk.CTkLabel(save_card,
                     text="Give the profile a name and save\nthe current adapter configuration.",
                     font=FONT_SMALL, text_color=C["text_muted"],
                     justify="left").pack(anchor="w", padx=14)

        self.profile_name = ctk.CTkEntry(
            save_card, placeholder_text="Profile name…",
            fg_color=C["input_bg"], border_color=C["bg_light"],
            text_color=C["text"], placeholder_text_color=C["text_muted"],
            font=FONT_BODY, height=36, corner_radius=6
        )
        self.profile_name.pack(fill="x", padx=14, pady=(10, 8))
        ActionButton(save_card, "Save Profile",
                     command=self._save_current).pack(anchor="w", padx=14, pady=(0, 14))

        # Info
        info_card = Card(top)
        info_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(info_card, text="How Profiles Work", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=14, pady=(14, 6))
        tips = (
            "• Profiles store IP, mask, gateway & DNS\n"
            "• Load a profile to populate Configure page\n"
            "• DHCP profiles will switch to automatic mode\n"
            "• Profiles are saved locally on your machine"
        )
        ctk.CTkLabel(info_card, text=tips, font=FONT_SMALL,
                     text_color=C["text_muted"], justify="left").pack(
            anchor="w", padx=14, pady=(0, 14))

        # Profile list
        list_card = Card(self)
        list_card.pack(fill="both", expand=True)
        ctk.CTkLabel(list_card, text="Saved Profiles", font=FONT_HEADER,
                     text_color=C["text_bright"]).pack(anchor="w", padx=14, pady=(14, 6))

        self.list_frame = ctk.CTkScrollableFrame(
            list_card, fg_color="transparent", corner_radius=0
        )
        self.list_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self._render_list()

    def _render_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.profiles:
            ctk.CTkLabel(self.list_frame,
                         text="No profiles yet. Save a configuration above.",
                         font=FONT_BODY, text_color=C["text_muted"]).pack(pady=20)
            return

        for name, cfg in self.profiles.items():
            row = ctk.CTkFrame(self.list_frame, fg_color=C["bg_light"],
                               corner_radius=8)
            row.pack(fill="x", pady=(0, 8))
            row.columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text="⚙", font=("Segoe UI", 20),
                         text_color=C["accent"], width=40).grid(
                row=0, column=0, rowspan=2, padx=(12, 0), pady=10)

            ctk.CTkLabel(row, text=name, font=FONT_HEADER,
                         text_color=C["text_bright"], anchor="w").grid(
                row=0, column=1, sticky="w", padx=10, pady=(10, 0))
            mode = "DHCP  (Automatic)" if cfg.get("dhcp") is True else f"Static  {cfg.get('ip','')} / {cfg.get('prefix','')} — {cfg.get('gateway','no gw')}"
            ctk.CTkLabel(row, text=mode, font=FONT_SMALL,
                         text_color=C["text_muted"], anchor="w").grid(
                row=1, column=1, sticky="w", padx=10, pady=(0, 10))

            btn_f = ctk.CTkFrame(row, fg_color="transparent")
            btn_f.grid(row=0, column=2, rowspan=2, padx=(0, 12), pady=10)

            ctk.CTkButton(
                btn_f, text="Load", width=70, height=30,
                fg_color=C["accent"], hover_color=C["accent_hover"],
                text_color=C["text_bright"], font=FONT_SMALL, corner_radius=6,
                command=lambda n=name: self._load_profile(n)
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                btn_f, text="Delete", width=70, height=30,
                fg_color=C["red_dim"], hover_color=C["red"],
                text_color=C["text_bright"], font=FONT_SMALL, corner_radius=6,
                command=lambda n=name: self._delete_profile(n)
            ).pack(side="left")

    def _save_current(self):
        name = self.profile_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Enter a profile name.")
            return
        adapter = self.app.selected_adapter.get()
        if not adapter:
            messagebox.showerror("Error", "No adapter selected.")
            return
        info = get_adapter_info(adapter)
        if not info["dhcp"]:
            info["extra_ips"] = get_extra_ips(adapter)
        else:
            info["extra_ips"] = []
        self.profiles[name] = info
        self._save_profiles()
        self._render_list()
        self.profile_name.delete(0, "end")
        ToastNotification(self.app, f"Profile '{name}' saved.")

    def _load_profile(self, name: str):
        cfg = self.profiles[name]
        from .configure import ConfigurePage
        page: ConfigurePage = self.app.pages["Configure"]

        is_dhcp = cfg.get("dhcp") is True
        page.mode_var.set("dhcp" if is_dhcp else "static")

        for key in ("ip", "prefix", "mask", "gateway", "dns1", "dns2"):
            e = page.entries[key]
            e.configure(state="normal")
            e.delete(0, "end")
            e.insert(0, cfg.get(key, ""))

        page._clear_extra_rows()
        if not is_dhcp:
            for eip, emask in cfg.get("extra_ips", []):
                page._add_extra_row(ip=eip, mask=emask)

        page._toggle_mode()

        self.app.show_page("Configure")
        mode_label = "DHCP" if is_dhcp else "Static"
        ToastNotification(self.app, f"Profile '{name}' loaded  ({mode_label}).")

    def _delete_profile(self, name: str):
        if messagebox.askyesno("Delete", f"Delete profile '{name}'?"):
            del self.profiles[name]
            self._save_profiles()
            self._render_list()

    def on_show(self):
        self._render_list()
