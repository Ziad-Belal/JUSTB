"""
gui/splash_screen.py
====================

Redesigned splash screen for JustB.

Same public API as before — ``SplashScreen(master, on_done)`` — so the
existing ``main.py`` import only needs the import path changed::

    from gui.splash_screen import SplashScreen

Visual sequence
---------------
1. Background card + soft lavender glow oval paint once.
2. Brand letters drop from y=-40 with ease_out_back, 80ms stagger.
3. Shimmer sweep moves a translucent white polygon across the wordmark.
4. Tagline fades from text_light -> text_dark over 320ms.
5. Rainbow dots appear left-to-right with 50ms stagger.
6. Progress bar fills with a 5-stop color gradient over 1400ms.
7. Brief green flash on the bar at 100%.
8. 240ms alpha fadeout, then ``on_done()``.

Total runtime: ~3.0s.
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from typing import Callable, List, Optional

from gui.animation import Animator, Easing, lerp_color, lighten
from gui.theme import (
    Palette,
    Font,
    BRAND_COLORS,
    BRAND_LETTERS,
    draw_card_chrome,
    rounded_rect,
)


class SplashScreen(tk.Toplevel):
    """Animated splash matching the new JustB visual system."""

    WIDTH = 520
    HEIGHT = 320

    def __init__(self, master: tk.Misc, on_done: Callable[[], None]):
        super().__init__(master)
        self._on_done = on_done
        self._closed = False

        self.overrideredirect(True)
        self.configure(bg=Palette.bg_root)

        W, H = self.WIDTH, self.HEIGHT
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        except Exception:
            self.geometry(f"{W}x{H}+200+200")
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.0)
        except tk.TclError:
            pass

        # The single Canvas that hosts every painted element
        self._canvas = tk.Canvas(
            self, width=W, height=H,
            bg=Palette.bg_root, highlightthickness=0, borderwidth=0,
        )
        self._canvas.pack(fill="both", expand=True)

        # Soft lavender glow behind the wordmark
        self._canvas.create_oval(
            60, 30, W - 60, 200,
            fill=lighten(Palette.purple, 0.82),
            outline="",
        )

        # Card chrome (rounded background + border)
        self._card_ids = draw_card_chrome(
            self._canvas, W, H, radius=18,
            fill=Palette.bg_card, border=Palette.border_acc, shadow=True,
        )

        # ── Wordmark letters — drawn in their final positions first, then
        #    we move them off-screen and animate them back in.
        self._letter_ids: List[int] = []
        font_obj = None
        try:
            import tkinter.font as tkf
            font_obj = tkf.Font(font=Font.BRAND)
        except Exception:
            font_obj = None

        total_w = 0
        widths: List[int] = []
        for ch in BRAND_LETTERS:
            if font_obj is not None:
                w = font_obj.measure(ch)
            else:
                w = 22
            widths.append(w)
            total_w += w
        total_w += 4 * (len(BRAND_LETTERS) - 1)
        start_x = (W - total_w) // 2
        letter_y = 110
        cursor = start_x
        for i, (ch, color) in enumerate(zip(BRAND_LETTERS, BRAND_COLORS)):
            cx = cursor + widths[i] // 2
            iid = self._canvas.create_text(
                cx, -40, text=ch, font=Font.BRAND,
                fill=color, anchor="center",
            )
            self._letter_ids.append((iid, cx, letter_y, color))
            cursor += widths[i] + 4

        # ── Shimmer sweep (drawn under the letters, above the card bg)
        self._shimmer_id = self._canvas.create_polygon(
            -200, 60, -140, 60, -200, 200, -260, 200,
            fill=Palette.text_white, stipple="gray12",
            outline="", smooth=True,
        )
        self._canvas.tag_lower(self._shimmer_id)
        for iid, _, _, _ in self._letter_ids:
            self._canvas.tag_raise(iid)

        # ── Tagline
        self._tag_id = self._canvas.create_text(
            W // 2, 165,
            text="Retail Management System",
            font=Font.ITALIC, fill=Palette.bg_card,
            anchor="center",
        )

        # ── Rainbow dot row
        self._dot_ids: List[int] = []
        dot_spacing = 18
        dot_y = 200
        dot_start = W // 2 - (len(BRAND_COLORS) - 1) * dot_spacing // 2
        for i, col in enumerate(BRAND_COLORS):
            iid = self._canvas.create_text(
                dot_start + i * dot_spacing, dot_y,
                text="●", font=("Segoe UI", 11, "bold"),
                fill=Palette.bg_card, anchor="center",
            )
            self._dot_ids.append((iid, col))

        # ── Progress bar
        bar_y = H - 50
        bar_h = 8
        bar_x1 = 70
        bar_x2 = W - 70
        self._canvas.create_rectangle(
            bar_x1, bar_y, bar_x2, bar_y + bar_h,
            fill=Palette.border, outline="",
        )
        # 5 segments (one per brand color) for the gradient
        self._bar_segments: List[int] = []
        seg_x1 = bar_x1
        seg_full = bar_x2 - bar_x1
        seg_w = seg_full // len(BRAND_COLORS)
        for i in range(len(BRAND_COLORS)):
            x2 = seg_x1 + seg_w if i < len(BRAND_COLORS) - 1 else bar_x2
            iid = self._canvas.create_rectangle(
                seg_x1, bar_y, seg_x1, bar_y + bar_h,
                fill=BRAND_COLORS[i], outline="",
            )
            self._bar_segments.append((iid, seg_x1, x2))
            seg_x1 = x2

        # Version label
        self._canvas.create_text(
            W // 2, H - 18, text="v2.0  ·  JustB Retail",
            font=Font.SMALL, fill=Palette.text_light, anchor="center",
        )

        # Animation engine
        self._animator = Animator(self, frame_budget_ms=16)

        # Fade the window in
        self._fade_window_in(0.0, 1.0, 200)
        # Kick off the main sequence after the fade-in
        self.after(220, self._run_sequence)

    # ── Window fade-in/out ───────────────────────────────────────────────

    def _fade_window_in(self, frm: float, to: float, duration_ms: int) -> None:
        start = time.time() * 1000

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start) / duration_ms)
            alpha = frm + (to - frm) * t
            try:
                self.attributes("-alpha", alpha)
            except tk.TclError:
                pass
            if t >= 1.0:
                try:
                    unsub()
                except Exception:
                    pass
        unsub = self._animator.on_frame(step)

    def _fade_window_out(self, duration_ms: int = 240) -> None:
        start = time.time() * 1000

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start) / duration_ms)
            alpha = 1.0 - t
            try:
                self.attributes("-alpha", alpha)
            except tk.TclError:
                pass
            if t >= 1.0:
                try:
                    unsub()
                except Exception:
                    pass
                self._finalize()
        unsub = self._animator.on_frame(step)

    # ── Letter drop ──────────────────────────────────────────────────────

    def _drop_letters(self, per_letter_delay_ms: int = 80,
                       duration_ms: int = 520) -> None:
        start_ms = time.time() * 1000
        n = len(self._letter_ids)

        def step(_dt: float, _now: float) -> None:
            elapsed = (time.time() * 1000) - start_ms
            for i, (iid, cx, target_y, _color) in enumerate(self._letter_ids):
                letter_start = i * per_letter_delay_ms
                letter_t = (elapsed - letter_start) / duration_ms
                if letter_t <= 0:
                    y = -40
                elif letter_t >= 1.0:
                    y = target_y
                else:
                    e = Easing.ease_out_back(letter_t)
                    y = -40 + (target_y - (-40)) * e
                self._canvas.coords(iid, cx, y)
            if elapsed >= (n - 1) * per_letter_delay_ms + duration_ms + 60:
                try:
                    unsub()
                except Exception:
                    pass

        unsub = self._animator.on_frame(step)

    # ── Shimmer sweep ────────────────────────────────────────────────────

    def _shimmer_sweep(self, duration_ms: int = 1600) -> None:
        start = time.time() * 1000
        W = self.WIDTH

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start) / duration_ms)
            e = Easing.ease_in_out_cubic(t)
            x = -200 + (W + 200) * e
            self._canvas.coords(
                self._shimmer_id,
                x, 60, x + 60, 60,
                x, 200, x - 60, 200,
            )
            if t >= 1.0:
                self._canvas.itemconfigure(self._shimmer_id, state="hidden")
                try:
                    unsub()
                except Exception:
                    pass
        unsub = self._animator.on_frame(step)

    # ── Tagline fade ─────────────────────────────────────────────────────

    def _fade_tagline(self, duration_ms: int = 320) -> None:
        start = time.time() * 1000

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start) / duration_ms)
            self._canvas.itemconfigure(
                self._tag_id,
                fill=lerp_color(Palette.bg_card, Palette.text_mid, t),
            )
            if t >= 1.0:
                try:
                    unsub()
                except Exception:
                    pass
        unsub = self._animator.on_frame(step)

    # ── Rainbow dots appear ─────────────────────────────────────────────

    def _dots_appear(self, per_dot_ms: int = 50, dot_step_ms: int = 180) -> None:
        start = time.time() * 1000

        def step(_dt: float, _now: float) -> None:
            elapsed = (time.time() * 1000) - start
            n = len(self._dot_ids)
            current = min(n, int(elapsed // dot_step_ms) + 1)
            for j, (iid, color) in enumerate(self._dot_ids):
                if j < current:
                    self._canvas.itemconfigure(iid, fill=color)
                else:
                    self._canvas.itemconfigure(iid, fill=Palette.bg_card)
            if current >= n and elapsed > n * dot_step_ms:
                try:
                    unsub()
                except Exception:
                    pass
        unsub = self._animator.on_frame(step)

    # ── Progress bar fill ────────────────────────────────────────────────

    def _fill_progress(self, duration_ms: int = 1400) -> None:
        start = time.time() * 1000
        n = len(self._bar_segments)

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start) / duration_ms)
            e = Easing.ease_out_cubic(t)
            # Each segment lights up at its own threshold
            for i, (iid, x1, x2) in enumerate(self._bar_segments):
                seg_threshold = i / n
                seg_t = max(0.0, min(1.0, (e - seg_threshold) * n))
                seg_t = Easing.ease_out_cubic(seg_t)
                new_x2 = x1 + (x2 - x1) * seg_t
                self._canvas.coords(iid, x1, self._canvas.coords(iid)[1],
                                     new_x2, self._canvas.coords(iid)[3])
            if t >= 1.0:
                # Snap each segment to its full extent
                for iid, x1, x2 in self._bar_segments:
                    bb = self._canvas.coords(iid)
                    if len(bb) == 4:
                        self._canvas.coords(iid, x1, bb[1], x2, bb[3])
                self._bar_flash()
                try:
                    unsub()
                except Exception:
                    pass
        unsub = self._animator.on_frame(step)

    def _bar_flash(self) -> None:
        # Create a white overlay rect that fades out
        bar_y = self.HEIGHT - 50
        bar_h = 8
        x1 = 70
        x2 = self.WIDTH - 70
        overlay = self._canvas.create_rectangle(
            x1, bar_y, x2, bar_y + bar_h,
            fill=Palette.text_white, stipple="gray25", outline="",
        )
        start = time.time() * 1000
        duration = 260

        def step(_dt: float, _now: float) -> None:
            t = min(1.0, ((time.time() * 1000) - start) / duration)
            if t >= 1.0:
                self._canvas.delete(overlay)
                try:
                    unsub()
                except Exception:
                    pass
                # Schedule window fadeout
                self.after(140, lambda: self._fade_window_out(240))
                return
            # We can't easily change stipple density; just delete when done.
        unsub = self._animator.on_frame(step)

    # ── Main sequence ────────────────────────────────────────────────────

    def _run_sequence(self) -> None:
        # All elements are already drawn; kick the animations.
        self._drop_letters()
        self._shimmer_sweep()
        # Tagline + dots start when letters are mostly settled
        self.after(900, lambda: (self._fade_tagline(), self._dots_appear()))
        # Progress bar after the tagline starts
        self.after(1100, self._fill_progress)

    def _finalize(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        except Exception:
            pass
        try:
            self._on_done()
        except Exception:
            pass


__all__ = ["SplashScreen"]
