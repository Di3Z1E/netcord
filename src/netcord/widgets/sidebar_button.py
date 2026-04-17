import customtkinter as ctk
from ..constants import C, FONT_BODY

class SidebarButton(ctk.CTkButton):
    def __init__(self, master, text, icon="", command=None, **kwargs):
        super().__init__(
            master,
            text=f"  {icon}  {text}" if icon else f"  {text}",
            command=command,
            anchor="w",
            height=40,
            corner_radius=6,
            fg_color="transparent",
            text_color=C["text_muted"],
            hover_color=C["bg_light"],
            font=FONT_BODY,
            **kwargs,
        )
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        if active:
            self.configure(fg_color=C["accent_dim"], text_color=C["text_bright"])
        else:
            self.configure(fg_color="transparent", text_color=C["text_muted"])
