import customtkinter as ctk

# Discord-like palette
C = {
    "bg_darkest":   "#1e2124",
    "bg_dark":      "#282b30",
    "bg_mid":       "#36393f",
    "bg_light":     "#3f4248",
    "sidebar":      "#2f3136",
    "accent":       "#5865f2",
    "accent_hover": "#4752c4",
    "accent_dim":   "#3c4494",
    "green":        "#3ba55c",
    "green_dim":    "#2d7d46",
    "red":          "#ed4245",
    "red_dim":      "#a12d2f",
    "yellow":       "#faa61a",
    "text":         "#dcddde",
    "text_muted":   "#72767d",
    "text_bright":  "#ffffff",
    "border":       "#202225",
    "input_bg":     "#202225",
    "card":         "#2f3136",
}

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_HEADER = ("Segoe UI", 13, "bold")
FONT_BODY   = ("Segoe UI", 12)
FONT_MONO   = ("Consolas", 11)
FONT_SMALL  = ("Segoe UI", 10)
FONT_BADGE  = ("Segoe UI", 9, "bold")

def set_theme():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
