import customtkinter as ctk
import threading
from tkinter import StringVar
from .constants import C, FONT_SMALL, FONT_BADGE, FONT_TITLE, set_theme
from .utils import is_admin
from .core import get_adapters, get_adapter_info
from .widgets.sidebar_button import SidebarButton
from .widgets.section_label import SectionLabel
from .pages.dashboard import DashboardPage
from .pages.configure import ConfigurePage
from .pages.diagnostics import DiagnosticsPage
from .pages.profiles import ProfilesPage

class NetCordApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        set_theme()
        self.title("NetCord — IPv4 Network Manager")
        self.geometry("1060x700")
        self.minsize(900, 600)
        self.configure(fg_color=C["bg_dark"])

        # Set Window Icon
        try:
            import os
            icon_path = "media/netcord.ico"
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        self.selected_adapter: StringVar = StringVar(value="")
        self.pages: dict[str, ctk.CTkFrame] = {}
        self._sidebar_btns: dict[str, SidebarButton] = {}
        self._current_page = ""

        self._build_layout()
        self._populate_adapters()

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, fg_color=C["sidebar"],
                                     width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self._build_sidebar()

        # Content area
        self.content = ctk.CTkFrame(self, fg_color=C["bg_dark"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self._build_pages()

    def _build_sidebar(self):
        # Logo area
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color=C["bg_darkest"],
                                   height=64, corner_radius=0)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(logo_frame, text="⬡  NetCord",
                     font=("Segoe UI", 17, "bold"),
                     text_color=C["accent"]).place(relx=0.5, rely=0.5, anchor="center")

        # Adapter selector
        adapter_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        adapter_frame.pack(fill="x", padx=12, pady=(16, 4))
        SectionLabel(adapter_frame, "Network Adapter").pack(anchor="w", pady=(0, 4))

        self.adapter_menu = ctk.CTkOptionMenu(
            adapter_frame,
            variable=self.selected_adapter,
            values=["Loading…"],
            command=self._on_adapter_change,
            fg_color=C["input_bg"],
            button_color=C["accent"],
            button_hover_color=C["accent_hover"],
            text_color=C["text"],
            font=FONT_SMALL,
            corner_radius=6,
            height=34,
            dynamic_resizing=False,
        )
        self.adapter_menu.pack(fill="x")

        self.status_badge = ctk.CTkLabel(
            adapter_frame, text="●  Detecting…",
            font=FONT_BADGE, text_color=C["yellow"]
        )
        self.status_badge.pack(anchor="w", pady=(6, 0))

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=C["border"]).pack(
            fill="x", padx=12, pady=12)

        # Nav
        SectionLabel(self.sidebar, "Navigation").pack(anchor="w", padx=16, pady=(0, 6))
        nav_items = [
            ("Dashboard",   "📊"),
            ("Configure",   "⚙"),
            ("Diagnostics", "🔬"),
            ("Profiles",    "💾"),
        ]
        for label, icon in nav_items:
            btn = SidebarButton(self.sidebar, label, icon=icon,
                                command=lambda l=label: self.show_page(l))
            btn.pack(fill="x", padx=8, pady=2)
            self._sidebar_btns[label] = btn

        # Bottom info
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=12, pady=12)
        ctk.CTkFrame(bottom, height=1, fg_color=C["border"]).pack(fill="x", pady=(0, 10))

        admin_color = C["green"] if is_admin() else C["red"]
        admin_text  = "●  Administrator" if is_admin() else "●  Limited (No Admin)"
        ctk.CTkLabel(bottom, text=admin_text, font=FONT_BADGE,
                     text_color=admin_color).pack(anchor="w")
        ctk.CTkLabel(bottom, text="v1.1  •  Windows IPv4",
                     font=FONT_SMALL, text_color=C["text_muted"]).pack(anchor="w", pady=(4, 0))

    def _build_pages(self):
        pages = {
            "Dashboard":   DashboardPage,
            "Configure":   ConfigurePage,
            "Diagnostics": DiagnosticsPage,
            "Profiles":    ProfilesPage,
        }
        for name, cls in pages.items():
            page = cls(self.content, app=self)
            page.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
            page.grid_remove()
            self.pages[name] = page

        self.show_page("Dashboard")

    def show_page(self, name: str):
        if self._current_page:
            self.pages[self._current_page].grid_remove()
            self._sidebar_btns[self._current_page].set_active(False)

        self._current_page = name
        self.pages[name].grid()
        self._sidebar_btns[name].set_active(True)
        self.pages[name].on_show()

    def _populate_adapters(self):
        def worker():
            adapters = get_adapters()
            self.after(0, lambda: self._set_adapters(adapters))
        threading.Thread(target=worker, daemon=True).start()

    def _set_adapters(self, adapters: list[str]):
        if not adapters:
            adapters = ["No adapters found"]
        self.adapter_menu.configure(values=adapters)
        self.selected_adapter.set(adapters[0])
        self._on_adapter_change(adapters[0])

    def _on_adapter_change(self, adapter: str):
        self.status_badge.configure(text="●  Detecting…", text_color=C["yellow"])

        def worker():
            info = get_adapter_info(adapter)
            self.after(0, lambda: self._update_status(info))

        threading.Thread(target=worker, daemon=True).start()

        if self._current_page == "Dashboard":
            self.pages["Dashboard"]._refresh()

    def _update_status(self, info: dict):
        if info["status"] == "Connected":
            self.status_badge.configure(text="●  Connected", text_color=C["green"])
        else:
            self.status_badge.configure(text="●  Disconnected", text_color=C["red"])
