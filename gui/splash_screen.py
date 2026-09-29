"""
gui/splash_screen.py
====================

Minimal premium splash screen for JustB.

Same public API as before — ``SplashScreen(master, on_done)`` — so the
existing ``main.py`` import only needs the import path changed::

    from gui.splash_screen import SplashScreen

Visual sequence
---------------
1. A quiet white card fades in around the complete JustB logo.
2. A single teal progress rule fills beneath it.
3. The splash fades out into the application.

Total runtime: ~3.0s.
"""

from __future__ import annotations

import math
import os
import time
import tkinter as tk
from typing import Callable, List, Optional

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

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

    WIDTH = 500
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

        # Quiet white surface with a barely visible border.
        self._card_ids = draw_card_chrome(
            self._canvas, W, H, radius=10,
            fill=Palette.bg_card, border=Palette.border, shadow=False,
        )

        # Keep the supplied logo static and centered on the splash.
        self._draw_static_logo()

        self._tag_id = self._canvas.create_text(
            W // 2, 260, text="RETAIL MANAGEMENT SYSTEM",
            font=Font.ITALIC, fill=Palette.bg_card,
            anchor="center",
        )

        # Thin progress rule near the bottom of the card.
        bar_y = H - 42
        bar_h = 3
        bar_x1 = 58
        bar_x2 = W - 58
        self._canvas.create_rectangle(
            bar_x1, bar_y, bar_x2, bar_y + bar_h,
            fill=Palette.border, outline="",
        )
        self._bar_segments: List[int] = []
        iid = self._canvas.create_rectangle(
            bar_x1, bar_y, bar_x1, bar_y + bar_h,
            fill=Palette.teal, outline="",
        )
        self._bar_segments.append((iid, bar_x1, bar_x2))

        # Animation engine
        self._animator = Animator(self, frame_budget_ms=16)

        # Fade the window in
        self._fade_window_in(0.0, 1.0, 200)
        # Kick off the main sequence after the fade-in
        self.after(220, self._run_sequence)

    def _draw_static_logo(self):
        """Render the complete supplied logo without animation."""
        source_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logo.png")
        if Image is not None and ImageTk is not None and os.path.exists(source_path):
            source = Image.open(source_path).convert("RGBA")
            image = source.resize((370, 247), Image.Resampling.LANCZOS)
            self._logo_image = ImageTk.PhotoImage(image)
            self._canvas.create_image(
                self.WIDTH // 2, 126, image=self._logo_image, anchor="center")
            return

        self._draw_text_fallback()

    def _draw_logo_composition(self):
        """Animate separate logo artwork pieces into their final positions."""
        if Image is None or ImageTk is None:
            self._draw_text_fallback()
            return

        source_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logo.png")
        if not os.path.exists(source_path):
            self._draw_text_fallback()
            return

        source = Image.open(source_path).convert("RGBA")
        scale = 0.67
        self._logo_images = []
        self._stationery = []

        # Source rectangles follow the actual illustrated logo: each sprite is
        # rendered independently, so no full logo image ever appears.
        pieces = [
            ((100, 82, 222, 238), (65, 68), (-155, 45)),   # notebook
            ((210, 68, 286, 180), (184, 42), (128, -72)),  # pencil
            ((315, 67, 377, 185), (302, 43), (150, 72)),  # pens
            ((370, 73, 516, 239), (342, 58), (150, -65)), # gift
            ((205, 48, 326, 143), (176, 37), (-135, -85)),# stars
            ((133, 128, 472, 253), (132, 74), (0, 92)),    # JUSTB wordmark
            ((99, 231, 516, 320), (58, 190), (0, 115)),   # ribbon
        ]
        for crop_box, target, offset in pieces:
            crop = source.crop(crop_box)
            size = (max(1, int(crop.width * scale)),
                    max(1, int(crop.height * scale)))
            sprite = ImageTk.PhotoImage(crop.resize(size, Image.Resampling.LANCZOS))
            self._logo_images.append(sprite)
            item_id = self._canvas.create_image(
                target[0] + offset[0], target[1] + offset[1],
                image=sprite, anchor="nw")
            self._stationery.append(([item_id], offset))

    def _draw_text_fallback(self):
        letters = "JUSTB"
        for index, (letter, color) in enumerate(zip(letters, BRAND_COLORS)):
            self._canvas.create_text(
                166 + index * 38, 137, text=letter,
                font=("Georgia", 34, "bold"), fill=color, anchor="center")
        self._stationery = []

    def _assemble_logo(self, duration_ms=720):
        start = time.time() * 1000
        previous_eased = 0.0

        def step():
            nonlocal previous_eased
            elapsed = time.time() * 1000 - start
            progress = min(1.0, elapsed / duration_ms)
            eased = Easing.ease_out_back(progress)
            for item_ids, offset in self._stationery:
                current_x = offset[0] * (previous_eased - eased)
                current_y = offset[1] * (previous_eased - eased)
                for item_id in item_ids:
                    self._canvas.move(item_id, current_x, current_y)
            previous_eased = eased
            if progress < 1.0:
                self.after(32, step)

        step()

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
        bar_y = self.HEIGHT - 42
        bar_h = 3
        x1 = 58
        x2 = self.WIDTH - 58
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
        self._fade_tagline(260)
        self.after(220, self._fill_progress)

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
