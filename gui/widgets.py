"""
gui/widgets.py
==============

Composed widgets built on top of :mod:`gui.theme` and :mod:`gui.animation`.

Public widgets
--------------
- :class:`RoundedCard`    - a Canvas-backed container with rounded chrome
                            and a transparent inner Frame for content
- :class:`BrandWordmark`  - the 5-colored "JustB" wordmark, drawn on a Canvas
- :class:`FocusRing`      - a 2px focus ring around a ``tk.Entry`` that
                            expands/collapses on focus events
- :class:`Pill`           - a true rounded pill label (Canvas-backed)
- :class:`PulsingGlow`    - a halo around a widget that pulses
- :class:`Shimmer`        - skeleton block that shimmers while loading
- :class:`NumberRollup`   - a Label that animates from old value -> new value
- :class:`QuantityPrompt` - a themed modal qty stepper
- :class:`SuccessBanner`  - a top-of-window toast with a checkmark
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from gui.animation import (
    Animator,
    Easing,
    hex_to_rgb,
    lerp,
    lerp_color,
    lighten,
    darken,
    rgb_to_hex,
)
from gui.theme import (
    Palette,
    Font,
    C,
    BRAND_COLORS,
    BRAND_LETTERS,
    rounded_rect,
    draw_card_chrome,
)


# ── RoundedCard ─────────────────────────────────────────────────────────────

class RoundedCard(tk.Canvas):
    """A Canvas that paints a rounded background and hosts a child Frame.

    Use ``.inner`` to add children::

        card = RoundedCard(parent, radius=14, fill=Palette.bg_card)
        tk.Label(card.inner, text="hello").pack()

    The card is sized to fill its parent (``pack(fill="both", expand=True)``
    recommended) and re-paints on ``<Configure>``.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        radius: int = 14,
        fill: str = Palette.bg_card,
        border: Optional[str] = None,
        shadow: bool = True,
        bg: str = Palette.bg_root,    # parent-style bg to blend against
        highlightthickness: int = 0,
    ):
        super().__init__(
            parent,
            bg=bg,
            highlightthickness=highlightthickness,
            borderwidth=0,
        )
        self._radius = radius
        self._fill = fill
        self._border = border
        self._shadow = shadow
        self._item_ids: List[int] = []
        self._inner: Optional[tk.Frame] = None

        self.bind("<Configure>", self._on_configure)
        # Build the inner content frame once
        self._inner = tk.Frame(self, bg=fill, highlightthickness=0, borderwidth=0)
        self._inner_id = self.create_window(
            0, 0, window=self._inner, anchor="nw",
        )
        self._painted = False

    @property
    def inner(self) -> tk.Frame:
        assert self._inner is not None
        return self._inner

    def set_fill(self, new_fill: str) -> None:
        self._fill = new_fill
        if self._inner is not None:
            self._inner.configure(bg=new_fill)
        self._painted = False
        self._on_configure()

    def _on_configure(self, _e: Optional[tk.Event] = None) -> None:
        w = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        # Pad for shadow
        pad = 4 if self._shadow else 0
        if w <= pad * 2 or h <= pad * 2:
            return
        if not self._painted:
            self._paint(w, h, pad)
        else:
            # Resize the existing items
            self.coords(self._inner_id, pad, pad)
            if self._inner is not None:
                self.itemconfigure(self._inner_id, width=w - 2 * pad,
                                   height=h - 2 * pad)
            for iid in self._item_ids:
                try:
                    self.coords(iid, *self._compute_item_coords(iid, w, h, pad))
                except Exception:
                    pass

    def _compute_item_coords(self, iid: int, w: int, h: int, pad: int) -> Tuple[float, ...]:
        # Heuristic: pull the bounding box and recenter with new dims.
        try:
            bb = self.bbox(iid)
        except Exception:
            return (0, 0, 0, 0)
        if not bb:
            return (0, 0, 0, 0)
        x1, y1, x2, y2 = bb
        # We can't easily tell which primitive it is; re-draw from scratch
        # on resize when the item is one of the chrome rects.
        return (x1, y1, x2, y2)

    def _paint(self, w: int, h: int, pad: int) -> None:
        for iid in self._item_ids:
            self.delete(iid)
        self._item_ids.clear()
        ids = draw_card_chrome(
            self, w, h,
            radius=self._radius,
            fill=self._fill,
            border=self._border,
            shadow=self._shadow,
        )
        self._item_ids.extend(ids)
        # The inner frame sits on top of all chrome
        for iid in ids:
            self.tag_lower(iid)
        self.tag_raise(self._inner_id)
        # Place inner
        self.coords(self._inner_id, pad, pad)
        if self._inner is not None:
            self.itemconfigure(
                self._inner_id, width=w - 2 * pad, height=h - 2 * pad
            )
        self._painted = True


# ── BrandWordmark ───────────────────────────────────────────────────────────

class BrandWordmark(tk.Canvas):
    """A Canvas that draws the colored "JustB" wordmark."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        letters: Optional[List[str]] = None,
        colors: Optional[List[str]] = None,
        font: Tuple = Font.BRAND,
        gap: int = 4,
        bg: str = Palette.bg_root,
    ):
        super().__init__(parent, bg=bg, highlightthickness=0, borderwidth=0)
        self._letters = letters or BRAND_LETTERS
        self._colors = colors or BRAND_COLORS
        self._font = font
        self._gap = gap
        self._ids: List[int] = []
        self.bind("<Configure>", self._paint)
        # Animation state
        self._letter_states: List[Dict[str, Any]] = []
        self._animator: Optional[Animator] = None
        self._on_done_cb: Optional[Callable] = None

    def animate_in(
        self,
        animator: Animator,
        *,
        per_letter_delay_ms: int = 80,
        duration_ms: int = 520,
        start_y: int = -40,
        end_y: int = 0,
        easing=Easing.ease_out_back,
        on_done: Optional[Callable] = None,
    ) -> None:
        self._animator = animator
        self._on_done_cb = on_done
        # Snapshot starting positions
        centers = self._letter_centers()
        self._letter_states = []
        for i, (cx, color) in enumerate(zip(centers, self._colors)):
            self._letter_states.append({
                "cx": cx, "color": color,
                "y": start_y, "target_y": end_y, "final_y": 0,
            })
        # Per-letter drop animation, staggered.
        def drop(i: int) -> None:
            if i >= len(self._letter_states):
                if on_done:
                    on_done()
                return
            st = self._letter_states[i]
            st["final_y"] = end_y  # we use coords at the bottom of the canvas
            # Animate ``y`` from start_y -> end_y
            def fr_y(): return {"y": start_y}
            def to_y(): return {"y": end_y}
            # Use tween_many on a dict-state object via per-frame callback
            start_ms = time.time() * 1000

            def step(_dt: float, _now: float) -> None:
                t = min(1.0, ((time.time() * 1000) - start_ms) / duration_ms)
                e = easing(t)
                st["y"] = start_y + (end_y - start_y) * e
                self._redraw_letters()
                if t >= 1.0:
                    self._animator._frame_callbacks  # noqa
                    return _stop

            unsub = self._animator.on_frame(step)
            def _stop() -> None:
                try:
                    unsub()
                except Exception:
                    pass
            # Schedule the next letter after the delay
            self.after(per_letter_delay_ms * (i + 1), lambda i=i: drop(i + 1))

        # After canvas paints, kick off
        self.after(20, lambda: drop(0))

    def _letter_centers(self) -> List[int]:
        """Compute horizontal centers for each letter given current font."""
        w = max(1, self.winfo_width())
        # Use Tk's font metrics for each letter to get widths.
        try:
            font_obj = tk.font.Font(font=self._font)
        except Exception:
            font_obj = None
        widths: List[int] = []
        for ch in self._letters:
            if font_obj is not None:
                widths.append(font_obj.measure(ch))
            else:
                widths.append(20)
        total = sum(widths) + self._gap * (len(self._letters) - 1)
        start = (w - total) // 2
        centers: List[int] = []
        cursor = start
        for ww in widths:
            centers.append(cursor + ww // 2)
            cursor += ww + self._gap
        return centers

    def _paint(self, _e: Optional[tk.Event] = None) -> None:
        for iid in self._ids:
            self.delete(iid)
        self._ids.clear()
        self._redraw_letters()

    def _redraw_letters(self) -> None:
        h = max(1, self.winfo_height())
        cy = h // 2
        for iid in self._ids:
            self.delete(iid)
        self._ids.clear()
        if not self._letter_states:
            centers = self._letter_centers()
            for ch, color, cx in zip(self._letters, self._colors, centers):
                iid = self.create_text(cx, cy, text=ch, font=self._font,
                                       fill=color, anchor="center")
                self._ids.append(iid)
        else:
            for ch, st in zip(self._letters, self._letter_states):
                iid = self.create_text(st["cx"], cy + st["y"],
                                       text=ch, font=self._font,
                                       fill=st["color"], anchor="center")
                self._ids.append(iid)


# ── FocusRing ───────────────────────────────────────────────────────────────

class FocusRing:
    """An animated 2px ring that hugs a ``tk.Entry`` widget.

    Implementation: a transparent ``tk.Frame`` placed over the entry's parent
    (slightly larger), with a Canvas child.  On FocusIn the ring expands from
    radius 4 to radius 10 with ``ease_out_back`` over 180ms; on FocusOut it
    collapses over 140ms.
    """

    def __init__(self, entry: tk.Entry, *, color: str, animator: Animator,
                 width: int = 2):
        self.entry = entry
        self.color = color
        self.animator = animator
        self.width = width
        self._ring_id: Optional[int] = None
        self._canvas: Optional[tk.Canvas] = None
        self._frame: Optional[tk.Frame] = None
        self._create_overlay()
        entry.bind("<FocusIn>", self._on_focus_in, add="+")
        entry.bind("<FocusOut>", self._on_focus_out, add="+")
        entry.bind("<Destroy>", self._on_destroy, add="+")

    def _create_overlay(self) -> None:
        parent = self.entry.master
        # We assume the entry is packed with some padx/pady in its parent.
        # We use place() to overlay a frame exactly on the entry's bbox.
        self.entry.update_idletasks()
        x = self.entry.winfo_x()
        y = self.entry.winfo_y()
        w = self.entry.winfo_width()
        h = self.entry.winfo_height()
        self._frame = tk.Frame(parent, bg=Palette.bg_root,
                                highlightthickness=0, borderwidth=0)
        self._frame.place(x=x, y=y, width=w, height=h)
        self._canvas = tk.Canvas(
            self._frame, bg=Palette.bg_root,
            highlightthickness=0, borderwidth=0,
        )
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._ring_id = None
        self._r = 4  # current animated radius
        self._draw_ring(0.0)  # hidden initially
        # Resize the ring when the entry moves/resizes
        self.entry.bind("<Configure>", self._sync_overlay, add="+")
        self.entry.bind("<Map>", self._sync_overlay, add="+")
        self._frame.lift()

    def _sync_overlay(self, _e: Optional[tk.Event] = None) -> None:
        if self._frame is None:
            return
        self.entry.update_idletasks()
        self._frame.place(
            x=self.entry.winfo_x(),
            y=self.entry.winfo_y(),
            width=self.entry.winfo_width(),
            height=self.entry.winfo_height(),
        )

    def _draw_ring(self, alpha: float) -> None:
        if self._canvas is None:
            return
        c = self._canvas
        c.delete("ring")
        if alpha <= 0.01:
            return
        # We can't easily alpha-blend on a Canvas; vary the color luminance
        # to fake a fade.  At alpha=0 we just don't draw.
        # Interpolate from bg to color
        col = lerp_color(Palette.bg_root, self.color, alpha)
        r = self._r
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 2 or h < 2:
            return
        c.create_rectangle(r, r, w - r, h - r,
                           outline=col, width=self.width, tags="ring")

    def _on_focus_in(self, _e: Optional[tk.Event] = None) -> None:
        if self._canvas is None:
            return
        start_r, end_r = 4, 10
        start_alpha, end_alpha = 0.0, 1.0
        start_ms = time.time() * 1000
        duration = 180

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start_ms) / duration)
            e = Easing.ease_out_back(t)
            self._r = start_r + (end_r - start_r) * e
            self._draw_ring(start_alpha + (end_alpha - start_alpha) * e)
            if t >= 1.0:
                unsub()
                return _stop

        unsub = self.animator.on_frame(step)
        def _stop(): pass
        # Placeholder
        return _stop

    def _on_focus_out(self, _e: Optional[tk.Event] = None) -> None:
        if self._canvas is None:
            return
        start_r, end_r = self._r, 4
        start_alpha, end_alpha = 1.0, 0.0
        start_ms = time.time() * 1000
        duration = 140

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start_ms) / duration)
            e = Easing.eASE_OUT_QUAD(t) if False else t  # linear is fine
            self._r = start_r + (end_r - start_r) * e
            self._draw_ring(start_alpha + (end_alpha - start_alpha) * e)
            if t >= 1.0:
                unsub()
                return _stop

        unsub = self.animator.on_frame(step)
        def _stop(): pass
        return _stop

    def _on_destroy(self, _e: Optional[tk.Event] = None) -> None:
        try:
            if self._frame is not None:
                self._frame.destroy()
        except Exception:
            pass
        self._frame = None
        self._canvas = None

    def destroy(self) -> None:
        self._on_destroy()


# ── Pill (Canvas-backed rounded label) ──────────────────────────────────────

class Pill(tk.Canvas):
    """A small rounded label (e.g. for the cashier name badge)."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        *,
        bg: str = Palette.purple,
        fg: str = Palette.text_white,
        font: Tuple = Font.LABEL_B,
        padx: int = 12,
        pady: int = 4,
    ):
        super().__init__(parent, bg=Palette.bg_root,
                         highlightthickness=0, borderwidth=0)
        self._bg = bg
        self._fg = fg
        self._font = font
        self._text = text
        self._padx = padx
        self._pady = pady
        self.bind("<Configure>", self._paint)
        self._text_id: Optional[int] = None

    def set_text(self, text: str) -> None:
        self._text = text
        self._paint()

    def set_colors(self, bg: str, fg: Optional[str] = None) -> None:
        self._bg = bg
        if fg is not None:
            self._fg = fg
        self._paint()

    def _paint(self, _e: Optional[tk.Event] = None) -> None:
        for iid in self.find_all():
            self.delete(iid)
        w = max(40, self.winfo_width())
        h = max(20, self.winfo_height())
        r = h // 2
        # Pill background
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=180,
                        style="pieslice", fill=self._bg, outline="")
        self.create_arc(w - 2 * r, 0, w, 2 * r, start=270, extent=180,
                        style="pieslice", fill=self._bg, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=self._bg, outline="")
        self.create_text(w // 2, h // 2, text=self._text, font=self._font,
                         fill=self._fg, anchor="center")


# ── PulsingGlow ─────────────────────────────────────────────────────────────

class PulsingGlow:
    """A halo of 6 pre-allocated rects that pulse around a target widget.

    Cheap to run: per frame we only move existing rects via ``coords()``.
    """

    def __init__(self, target: tk.Widget, *, color: str, animator: Animator,
                 min_scale: float = 1.0, max_scale: float = 1.04,
                 period_ms: int = 1400):
        self.target = target
        self.color = color
        self.animator = animator
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.period_ms = period_ms
        self._overlay: Optional[tk.Canvas] = None
        self._rect_ids: List[int] = []
        self._running = False
        self._unsub = None
        self._start_ms = 0.0
        target.bind("<Configure>", self._sync, add="+")
        target.bind("<Destroy>", lambda _e: self.destroy(), add="+")

    def start(self) -> None:
        if self._running:
            return
        self._ensure_overlay()
        if self._overlay is None:
            return
        self._running = True
        self._start_ms = time.time() * 1000
        self._unsub = self.animator.on_frame(self._tick)

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._unsub is not None:
            try:
                self._unsub()
            except Exception:
                pass
        self._unsub = None
        if self._overlay is not None:
            for iid in self._rect_ids:
                self._overlay.itemconfigure(iid, state="hidden")

    def destroy(self) -> None:
        self.stop()
        if self._overlay is not None:
            try:
                self._overlay.destroy()
            except Exception:
                pass
        self._overlay = None

    def _ensure_overlay(self) -> None:
        if self._overlay is not None:
            self._sync()
            return
        parent = self.target.master
        try:
            self.target.update_idletasks()
            x = self.target.winfo_x()
            y = self.target.winfo_y()
            w = self.target.winfo_width()
            h = self.target.winfo_height()
        except Exception:
            return
        self._overlay = tk.Canvas(
            parent, bg=parent.cget("bg") if hasattr(parent, "cget") else Palette.bg_root,
            highlightthickness=0, borderwidth=0,
        )
        self._overlay.place(x=x, y=y, width=w, height=h)
        self._overlay.lower(self.target)
        # Pre-allocate 6 halo rects with varying stipple
        for i in range(6):
            iid = self._overlay.create_rectangle(
                0, 0, 0, 0, outline="", fill=self.color,
                stipple="gray25" if i % 2 == 0 else "gray12",
                state="hidden",
            )
            self._rect_ids.append(iid)

    def _sync(self, _e: Optional[tk.Event] = None) -> None:
        if self._overlay is None:
            return
        try:
            self.target.update_idletasks()
            self._overlay.place(
                x=self.target.winfo_x(),
                y=self.target.winfo_y(),
                width=self.target.winfo_width(),
                height=self.target.winfo_height(),
            )
        except Exception:
            pass

    def _tick(self, _dt: float, _now: float) -> None:
        if not self._running or self._overlay is None:
            return
        try:
            w = self.target.winfo_width()
            h = self.target.winfo_height()
        except Exception:
            return
        if w < 2 or h < 2:
            return
        elapsed = (time.time() * 1000) - self._start_ms
        phase = (elapsed % self.period_ms) / self.period_ms
        # Triangle wave 0..1..0
        tri = 1 - abs(2 * phase - 1)
        scale = self.min_scale + (self.max_scale - self.min_scale) * tri
        pad_x = int(w * (scale - 1) / 2) + 4
        pad_y = int(h * (scale - 1) / 2) + 4
        for i, iid in enumerate(self._rect_ids):
            extra = i * 2
            self._overlay.coords(
                iid,
                -pad_x - extra, -pad_y - extra,
                w + pad_x + extra, h + pad_y + extra,
            )
            self._overlay.itemconfigure(iid, state="normal")


# ── Shimmer ─────────────────────────────────────────────────────────────────

class Shimmer:
    """Skeleton block that shimmers (moves a highlight across it)."""

    def __init__(self, canvas: tk.Canvas, x: int, y: int, w: int, h: int,
                 *, radius: int = 6, animator: Optional[Animator] = None,
                 color: str = Palette.bg_panel):
        self.canvas = canvas
        self.x, self.y, self.w, self.h = x, y, w, h
        self.color = color
        self._animator = animator
        self._bg_id = rounded_rect(canvas, x, y, x + w, y + h, radius,
                                    fill=color, outline="")
        self._highlight_id: Optional[int] = None
        self._running = False
        self._unsub = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        if self._animator is None:
            return
        # Pre-create the moving highlight
        self._highlight_id = self.canvas.create_rectangle(
            self.x, self.y, self.x + 60, self.y + self.h,
            fill="#FFFFFF", stipple="gray12", outline="",
        )
        period_ms = 1400

        def step(_dt: float, _now: float) -> None:
            if not self._running or self._highlight_id is None:
                return
            ms = time.time() * 1000
            phase = (ms % period_ms) / period_ms
            x = self.x - 60 + (self.w + 60) * phase
            self.canvas.coords(
                self._highlight_id, x, self.y, x + 60, self.y + self.h,
            )

        self._unsub = self._animator.on_frame(step)

    def stop(self) -> None:
        self._running = False
        if self._unsub is not None:
            try:
                self._unsub()
            except Exception:
                pass
        self._unsub = None
        if self._highlight_id is not None:
            try:
                self.canvas.delete(self._highlight_id)
            except Exception:
                pass
        self._highlight_id = None

    def destroy(self) -> None:
        self.stop()
        try:
            self.canvas.delete(self._bg_id)
        except Exception:
            pass


# ── NumberRollup ────────────────────────────────────────────────────────────

class NumberRollup(tk.Label):
    """A label that animates a numeric value from old to new over time."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        animator: Optional[Animator] = None,
        prefix: str = "EGP ",
        suffix: str = "",
        font: Tuple = Font.TOTAL,
        fg: str = Palette.text_dark,
        bg: str = Palette.bg_card,
        decimals: int = 2,
        initial: float = 0.0,
        **kw,
    ):
        super().__init__(parent, bg=bg, fg=fg, font=font, **kw)
        self._animator = animator
        self._prefix = prefix
        self._suffix = suffix
        self._decimals = decimals
        self._current = float(initial)
        self._target = float(initial)
        self._tween = None
        self._render()
        self.bind("<Destroy>", self._on_destroy, add="+")

    def set(self, value: float, *, duration: int = 250,
            easing=Easing.ease_out_quad) -> None:
        new_value = float(value)
        if abs(new_value - self._target) < 1e-6 and self._current == self._target:
            return
        self._current = self._current  # keep until tween starts
        if duration <= 0 or self._animator is None:
            self._current = new_value
            self._target = new_value
            self._render()
            return
        start = self._current
        end = new_value
        start_ms = time.time() * 1000
        self._target = end
        # Cancel any previous tween by overwriting _current target
        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start_ms) / duration)
            e = easing(t)
            self._current = start + (end - start) * e
            self._render()
            if t >= 1.0:
                self._tween = None
                try:
                    unsub()
                except Exception:
                    pass

        if self._tween is not None:
            try:
                self._tween()
            except Exception:
                pass
        unsub = self._animator.on_frame(step)
        self._tween = unsub

    def _render(self) -> None:
        s = f"{self._prefix}{self._current:,.{self._decimals}f}{self._suffix}"
        try:
            self.configure(text=s)
        except tk.TclError:
            pass

    def _on_destroy(self, _e: Optional[tk.Event] = None) -> None:
        if self._tween is not None:
            try:
                self._tween()
            except Exception:
                pass
        self._tween = None


# ── QuantityPrompt ──────────────────────────────────────────────────────────

class QuantityPrompt(tk.Toplevel):
    """A themed modal qty stepper.  Returns the int or None."""

    def __init__(
        self,
        parent: tk.Misc,
        prompt: str,
        *,
        initial: int = 1,
        min_qty: int = 1,
        max_qty: int = 9999,
        animator: Optional[Animator] = None,
    ):
        super().__init__(parent)
        self.title("Quantity")
        self.configure(bg=Palette.bg_root)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._animator = animator
        self._result: Optional[int] = None
        self._qty = max(min_qty, initial)
        self._min = min_qty
        self._max = max_qty

        # Center
        W, H = 320, 220
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        except Exception:
            self.geometry(f"{W}x{H}")

        card = RoundedCard(self, radius=14, fill=Palette.bg_card,
                           shadow=True)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(
            card.inner, text=prompt, font=Font.HEAD,
            bg=Palette.bg_card, fg=Palette.text_dark,
        ).pack(pady=(8, 4))

        # Stepper row
        row = tk.Frame(card.inner, bg=Palette.bg_card)
        row.pack(pady=12)

        self._minus = tk.Label(row, text="−", font=("Segoe UI", 18, "bold"),
                                bg=Palette.bg_panel, fg=Palette.text_dark,
                                width=3, cursor="hand2", pady=6)
        self._minus.pack(side="left", padx=(0, 8))
        self._minus.bind("<Button-1>", lambda _e: self._delta(-1))

        self._val_lbl = tk.Label(row, text=str(self._qty), font=Font.TOTAL,
                                  bg=Palette.bg_card, fg=Palette.purple,
                                  width=5, anchor="center")
        self._val_lbl.pack(side="left", padx=4)

        self._plus = tk.Label(row, text="+", font=("Segoe UI", 18, "bold"),
                               bg=Palette.purple, fg=Palette.text_white,
                               width=3, cursor="hand2", pady=6)
        self._plus.pack(side="left", padx=(8, 0))
        self._plus.bind("<Button-1>", lambda _e: self._delta(1))

        # OK / Cancel
        btn_row = tk.Frame(card.inner, bg=Palette.bg_card)
        btn_row.pack(pady=(12, 4))

        cancel = tk.Label(btn_row, text="  Cancel  ", font=Font.BTN,
                          bg=Palette.bg_card, fg=Palette.text_mid,
                          highlightthickness=1,
                          highlightbackground=Palette.border,
                          cursor="hand2", pady=6)
        cancel.pack(side="left", padx=4)
        cancel.bind("<Button-1>", lambda _e: self._close(None))

        ok = tk.Label(btn_row, text="  OK  ", font=Font.BTN,
                      bg=Palette.success, fg=Palette.text_white,
                      cursor="hand2", pady=6, padx=12)
        ok.pack(side="left", padx=4)
        ok.bind("<Button-1>", lambda _e: self._close(self._qty))

        self.bind("<Key-plus>", lambda _e: self._delta(1))
        self.bind("<Key-minus>", lambda _e: self._delta(-1))
        self.bind("<Return>", lambda _e: self._close(self._qty))
        self.bind("<Escape>", lambda _e: self._close(None))

    def _delta(self, n: int) -> None:
        new = self._qty + n
        new = max(self._min, min(self._max, new))
        if new == self._qty:
            return
        self._qty = new
        self._val_lbl.configure(text=str(self._qty))

    def _close(self, value: Optional[int]) -> None:
        self._result = value
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    @classmethod
    def ask(cls, parent: tk.Misc, prompt: str, *, initial: int = 1,
            min_qty: int = 1, max_qty: int = 9999,
            animator: Optional[Animator] = None) -> Optional[int]:
        dlg = cls(parent, prompt, initial=initial, min_qty=min_qty,
                  max_qty=max_qty, animator=animator)
        parent.wait_window(dlg)
        return dlg._result


# ── SuccessBanner ───────────────────────────────────────────────────────────

class SuccessBanner(tk.Toplevel):
    """A top-of-window toast with a spring-easing checkmark.

    The banner is placed via ``overrideredirect`` so it floats over any parent.
    Pass the *parent* window to position it correctly.
    """

    def __init__(
        self,
        parent: tk.Misc,
        message: str = "Sale Complete",
        *,
        animator: Optional[Animator] = None,
        duration_ms: int = 2200,
    ):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=Palette.bg_root)
        self._animator = animator
        self._message = message

        W, H = 360, 64
        try:
            parent.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            x = px + (pw - W) // 2
            y = py + 16
            self.geometry(f"{W}x{H}+{x}+{y}")
        except Exception:
            self.geometry(f"{W}x{H}+200+200")

        # Rounded background
        self._canvas = tk.Canvas(self, bg=Palette.bg_root,
                                  width=W, height=H,
                                  highlightthickness=0, borderwidth=0)
        self._canvas.pack()
        draw_card_chrome(self._canvas, W, H, radius=14,
                          fill=Palette.success, shadow=True)
        # Checkmark circle
        self._check_id = self._canvas.create_oval(14, 14, 50, 50,
                                                   fill=Palette.text_white,
                                                   outline="")
        self._check_path: List[int] = []
        # Message text
        self._msg_id = self._canvas.create_text(
            64, H // 2, text=message, font=Font.BTN_LG,
            fill=Palette.text_white, anchor="w",
        )

        # Animations: spring check + slide in
        if animator is not None:
            self._animate_in(animator)
        # Auto-dismiss
        self.after(duration_ms, self._fade_out)

    def _animate_in(self, animator: Animator) -> None:
        # Checkmark path animation: a polyline drawn in two strokes.
        # Use a polyline that grows over time.
        # Center of circle: (32, 32), radius 18.
        cx, cy, r = 32, 32, 18
        # Path: from (cx - 8, cy) to (cx - 2, cy + 6) to (cx + 10, cy - 6)
        p1 = (cx - 8, cy)
        p2 = (cx - 2, cy + 6)
        p3 = (cx + 10, cy - 6)
        duration = 360
        start_ms = time.time() * 1000

        def draw(t: float) -> None:
            # First half: draw p1->p2
            # Second half: draw p2->p3
            for iid in self._check_path:
                self._canvas.delete(iid)
            self._check_path.clear()
            if t < 0.5:
                k = t / 0.5
                x = p1[0] + (p2[0] - p1[0]) * k
                y = p1[1] + (p2[1] - p1[1]) * k
                iid = self._canvas.create_line(
                    p1[0], p1[1], x, y,
                    fill=Palette.success, width=3, capstyle="round",
                )
                self._check_path.append(iid)
            else:
                k = (t - 0.5) / 0.5
                x = p2[0] + (p3[0] - p2[0]) * k
                y = p2[1] + (p3[1] - p2[1]) * k
                iid = self._canvas.create_line(
                    p1[0], p1[1], p2[0], p2[1],
                    fill=Palette.success, width=3, capstyle="round",
                )
                self._check_path.append(iid)
                iid2 = self._canvas.create_line(
                    p2[0], p2[1], x, y,
                    fill=Palette.success, width=3, capstyle="round",
                )
                self._check_path.append(iid2)

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start_ms) / duration)
            e = Easing.ease_out_back(t)
            draw(e)
            if t >= 1.0:
                try:
                    unsub()
                except Exception:
                    pass

        unsub = animator.on_frame(step)

    def _fade_out(self) -> None:
        try:
            self.destroy()
        except Exception:
            pass


__all__ = [
    "RoundedCard",
    "BrandWordmark",
    "FocusRing",
    "Pill",
    "PulsingGlow",
    "Shimmer",
    "NumberRollup",
    "QuantityPrompt",
    "SuccessBanner",
]
