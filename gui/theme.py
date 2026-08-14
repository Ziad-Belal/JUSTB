"""
gui/theme.py
============

Single source of truth for the JustB visual system.

Before this module existed, the same color dict and font tuples were
duplicated across seven files with drift.  All callers should now do::

    from gui.theme import Palette, Font, BRAND_COLORS, BRAND_LETTERS
    from gui.theme import C, FONT_BRAND  # back-compat shims

The module also hosts the small set of *factories* that build reusable
visual primitives.  These are kept lightweight on purpose: the composed
widgets (RoundedCard, FocusRing, NumberRollup, etc.) live in
``gui/widgets.py``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from gui.animation import (
    Animator,
    Easing,
    hex_to_rgb,
    lerp_color,
    lighten,
    darken,
    rgb_to_hex,
)


# ── Color palette ────────────────────────────────────────────────────────────

class Palette:
    # Surfaces
    bg_root    = "#F7F5FF"   # soft lavender-white canvas
    bg_card    = "#FFFFFF"   # pure white card
    bg_panel   = "#F0EDFF"   # soft purple panel
    bg_input   = "#FFFFFF"   # input bg
    bg_row_alt = "#FAF8FF"   # alternating row tint
    bg_hover   = "#F4F0FF"   # subtle hover wash
    bg_dim     = "#EDEAFF"   # dimmed/decorative

    # JustB brand colors (one per letter, J→B)
    teal       = "#1BBFBF"   # J
    pink       = "#F0569A"   # U
    orange     = "#F97316"   # S
    purple     = "#8B5CF6"   # T
    purple_dk  = "#7C3AED"
    green      = "#22C55E"   # B

    # Text
    text_dark  = "#1A1035"
    text_mid   = "#6B6B8A"
    text_light = "#A8A8C0"
    text_white = "#FFFFFF"

    # Borders
    border     = "#E8E4F8"
    border_acc = "#C4B8F5"

    # Accents
    gold       = "#D97706"   # warm amber (used only for the TOTAL label)

    # Semantic
    success    = "#16A34A"
    success_dk = "#15803D"
    danger     = "#DC2626"
    danger_dk  = "#B91C1C"
    warning    = "#D97706"

    # Order matters - first to last letter of "JustB"
    BRAND_COLORS: List[str] = ["#1BBFBF", "#F0569A", "#F97316", "#8B5CF6", "#22C55E"]
    BRAND_LETTERS: List[str] = list("JustB")


# Module-level constants so callers can do `from gui.theme import BRAND_COLORS`.
# These mirror Palette attributes; re-exporting at module level keeps the
# existing `from gui.login_screen import BRAND_COLORS` import paths working.
BRAND_COLORS: List[str] = Palette.BRAND_COLORS
BRAND_LETTERS: List[str] = Palette.BRAND_LETTERS


# Back-compat shim so existing `C["purple"]` lookups keep working.
# (We use a fresh class so it does not shadow the class-level
# ``BRAND_COLORS`` attribute on :class:`Palette`.)
class _CDict:
    """Dict-like proxy that reads from :class:`Palette`."""

    def __getitem__(self, key: str) -> Any:
        return getattr(Palette, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(Palette, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(Palette, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(Palette, key, default)


# C is the dict-like shim. ``C["bg_root"]`` and ``C.bg_root`` both work
# because Palette attributes are accessible as module-level names too.
C = _CDict()


# ── Typography ───────────────────────────────────────────────────────────────

class Font:
    BRAND      = ("Georgia",  26, "bold")
    HEAD       = ("Georgia",  13, "bold")
    LABEL      = ("Segoe UI", 10)
    LABEL_B    = ("Segoe UI", 10, "bold")
    ENTRY      = ("Segoe UI", 11)
    BTN        = ("Segoe UI", 11, "bold")
    BTN_LG     = ("Segoe UI", 13, "bold")
    TOTAL      = ("Georgia",  20, "bold")
    SMALL      = ("Segoe UI",  9)
    SECTION    = ("Segoe UI",  9, "bold")
    MONO_DIGIT = ("Segoe UI", 10)
    ITALIC     = ("Segoe UI", 10, "italic")


# Aliases so `from gui.theme import FONT_BRAND` works in older code paths.
FONT_BRAND    = Font.BRAND
FONT_HEAD     = Font.HEAD
FONT_LABEL    = Font.LABEL
FONT_LABEL_B  = Font.LABEL_B
FONT_ENTRY    = Font.ENTRY
FONT_BTN      = Font.BTN
FONT_BTN_LG   = Font.BTN_LG
FONT_TOTAL    = Font.TOTAL
FONT_SMALL    = Font.SMALL
FONT_SECTION  = Font.SECTION


# ── Re-exports for callers that imported the helpers from the animation mod ─
# (Keeps the public surface flat.)

__all__ = [
    "Palette",
    "Font",
    "C",
    "BRAND_COLORS",
    "BRAND_LETTERS",
    "FONT_BRAND", "FONT_HEAD", "FONT_LABEL", "FONT_LABEL_B",
    "FONT_ENTRY", "FONT_BTN", "FONT_BTN_LG", "FONT_TOTAL",
    "FONT_SMALL", "FONT_SECTION",
    "rounded_rect",
    "draw_card_chrome",
    "make_rounded_button",
    "make_pill",
    "make_skeleton",
]


# ── Canvas primitives ───────────────────────────────────────────────────────

def rounded_rect(
    canvas: tk.Canvas,
    x1: float, y1: float, x2: float, y2: float,
    radius: int,
    **kw,
) -> int:
    """Draw a single rounded rectangle and return the canvas item id.

    Uses a 4-arc + 3-rect decomposition so the corners are smooth.
    ``kw`` is forwarded to ``canvas.create_*`` for the corner arcs;
    fills/colors for the rects are derived from the same kwargs.
    """
    r = max(0, int(radius))
    if r == 0:
        return canvas.create_rectangle(x1, y1, x2, y2, **kw)
    # Decide which kw dict drives the rects vs the arcs by separating
    # 'fill' (used by both) and the rest.  Tk requires the same set of
    # options on every primitive of a compound shape, so we pass through.
    def arc(xxa, yya, xxb, yyb):
        return canvas.create_arc(xxa, yya, xxb, yyb,
                                 start=90, extent=90, style="pieslice",
                                 **kw)
    def rect(xxa, yya, xxb, yyb):
        return canvas.create_rectangle(xxa, yya, xxb, yyb, **kw)
    arcs = [
        arc(x1, y1, x1 + 2 * r, y1 + 2 * r),
        arc(x2 - 2 * r, y1, x2, y1 + 2 * r),
        arc(x1, y2 - 2 * r, x1 + 2 * r, y2),
        arc(x2 - 2 * r, y2 - 2 * r, x2, y2),
    ]
    rects = [
        rect(x1 + r, y1, x2 - r, y1 + r),
        rect(x1 + r, y2 - r, x2 - r, y2),
        rect(x1, y1 + r, x2, y2 - r),
    ]
    return canvas.create_group(*arcs, *rects) if hasattr(canvas, "create_group") else arcs[0]


def draw_card_chrome(
    canvas: tk.Canvas,
    w: int, h: int,
    *,
    radius: int = 14,
    fill: str,
    border: Optional[str] = None,
    shadow: bool = True,
) -> List[int]:
    """Paint a rounded card background (and an optional 2-layer shadow).

    Returns the canvas item ids, bottom-to-top.
    """
    ids: List[int] = []
    if shadow:
        # Far shadow (more offset, lower alpha)
        ids.append(rounded_rect(
            canvas, 2, 4, w - 2, h - 1, radius + 1,
            fill="#1A1035", stipple="gray50", outline="",
        ))
        # Near shadow (closer, slightly stronger)
        ids.append(rounded_rect(
            canvas, 1, 2, w - 1, h, radius,
            fill="#1A1035", stipple="gray25", outline="",
        ))
    ids.append(rounded_rect(canvas, 0, 0, w, h, radius, fill=fill, outline=""))
    if border:
        ids.append(rounded_rect(canvas, 0, 0, w - 1, h - 1, radius,
                                fill="", outline=border))
    return ids


# ── Reusable widgets (low-level) ─────────────────────────────────────────────

class _LabelButton(tk.Label):
    """Internal: a flat ``tk.Label`` styled as a button.  This is the
    *base* that the public ``make_rounded_button`` upgrades with
    animation.  Kept around for screens that still want a no-frills
    label-as-button (the existing ``_tb_btn`` pattern)."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        command: Optional[Callable[[], Any]] = None,
        *,
        bg: str,
        hover: Optional[str] = None,
        fg: str = Palette.text_white,
        font: Tuple = Font.BTN,
        padx: int = 18,
        pady: int = 9,
        radius: int = 10,
        outlined: bool = False,
    ):
        kw: Dict[str, Any] = dict(
            text=text, bg=bg, fg=fg, font=font,
            padx=padx, pady=pady, cursor="hand2",
        )
        if outlined:
            kw["bg"] = Palette.bg_card
            kw["fg"] = bg
            kw["highlightthickness"] = 1
            kw["highlightbackground"] = bg
        else:
            kw["relief"] = "flat"
        super().__init__(parent, **kw)
        self._bg = bg
        self._hover = hover or (Palette.bg_hover if outlined else darken(bg, 0.10))
        self._fg = fg
        self._command = command
        self._outlined = outlined
        if hover is not None or not outlined:
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
        if command is not None:
            self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _e=None) -> None:
        if not self._outlined:
            self.config(bg=self._hover)
        else:
            self.config(bg=lighten(self._bg, 0.92))

    def _on_leave(self, _e=None) -> None:
        self.config(bg=Palette.bg_card if self._outlined else self._bg)

    def _on_click(self, _e=None) -> None:
        if self._command:
            try:
                self._command()
            except Exception as exc:
                print(f"[theme] _LabelButton click handler failed: {exc}")


def make_rounded_button(
    parent: tk.Misc,
    text: str,
    command: Optional[Callable[[], Any]] = None,
    *,
    bg: str,
    hover: Optional[str] = None,
    fg: str = Palette.text_white,
    font: Tuple = Font.BTN,
    padx: int = 18,
    pady: int = 9,
    radius: int = 10,
    animator: Optional[Animator] = None,
    outlined: bool = False,
) -> tk.Widget:
    """Create a button with optional animated bg tween on hover.

    Falls back to a flat :class:`_LabelButton` if no animator is provided.
    """
    btn = _LabelButton(
        parent, text, command,
        bg=bg, hover=hover, fg=fg, font=font,
        padx=padx, pady=pady, radius=radius, outlined=outlined,
    )

    if animator is None or outlined:
        return btn

    # Wire animated hover
    from_color = bg
    to_color = hover or darken(bg, 0.12)

    def enter(_e=None):
        animator.tween(btn, to={"bg": to_color}, duration=180,
                      easing=Easing.ease_out_quad)

    def leave(_e=None):
        animator.tween(btn, to={"bg": from_color}, duration=240,
                      easing=Easing.ease_out_quad)

    btn.bind("<Enter>", enter, add="+")
    btn.bind("<Leave>", leave, add="+")

    return btn


def make_pill(
    parent: tk.Misc,
    text: str,
    *,
    bg: str = Palette.purple,
    fg: str = Palette.text_white,
    font: Tuple = Font.LABEL_B,
    padx: int = 12,
    pady: int = 4,
) -> tk.Label:
    """A simple pill-style label (rounded look via padx/pady)."""
    lbl = tk.Label(
        parent, text=f"  {text}  ",
        bg=bg, fg=fg, font=font,
        padx=padx, pady=pady,
    )
    return lbl


def make_skeleton(
    canvas: tk.Canvas,
    x: int, y: int, w: int, h: int,
    *,
    radius: int = 6,
) -> int:
    """Draw a skeleton placeholder block.  Returns the canvas item id."""
    return rounded_rect(canvas, x, y, x + w, y + h, radius,
                        fill=Palette.bg_panel, outline="")


# ── ttk.Treeview global style ───────────────────────────────────────────────

def configure_ttk_styles() -> None:
    """Apply our base ttk styles.  Idempotent; call once at app startup."""
    style = ttk.Style()
    # ``clam`` is needed for the per-row striping tags to render correctly
    # on Windows (the default ``vista`` theme ignores some style overrides).
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(
        "JB.Treeview",
        background=Palette.bg_card,
        fieldbackground=Palette.bg_card,
        foreground=Palette.text_dark,
        rowheight=34,
        borderwidth=0,
        font=Font.LABEL,
    )
    style.configure(
        "JB.Treeview.Heading",
        background=Palette.bg_panel,
        foreground=Palette.text_mid,
        font=Font.SECTION,
        relief="flat",
        borderwidth=0,
    )
    style.map(
        "JB.Treeview",
        background=[("selected", lighten(Palette.purple, 0.78))],
        foreground=[("selected", Palette.text_dark)],
    )
