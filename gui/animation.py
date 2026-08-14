"""
gui/animation.py
================

Reusable tween / animation engine for the JustB Tkinter UI.

Goals
-----
- One single ``after(16, ...)`` ticker drives every active tween (≈60fps)
- Easing functions: linear, quad-in/out, cubic-in-out, back-out, elastic-out
- Color and numeric interpolation built-in
- Every ``widget.config`` is wrapped so a destroyed widget does not spam
  ``TclError`` to the console
- Skips ``config`` on unmapped widgets but keeps the clock running so the
  end value is correct when the widget reappears

Public API
----------
- :class:`Easing`         - easings, all ``f(t) -> float`` with ``t in [0, 1]``
- :class:`Animator`        - the engine. ``tween``, ``tween_many``,
                             ``sequence``, ``parallel``, ``cancel``,
                             ``cancel_all``, ``on_frame``
- :func:`hex_to_rgb`, :func:`rgb_to_hex`, :func:`lerp_color`, :func:`lerp`
"""

from __future__ import annotations

import math
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Tuple


# ── Easing ───────────────────────────────────────────────────────────────────

class Easing:
    """All easings take t in [0, 1] and return a value in [0, 1] (or beyond
    for back / elastic, which is the whole point of those curves)."""

    @staticmethod
    def linear(t: float) -> float:
        return t

    @staticmethod
    def ease_in_quad(t: float) -> float:
        return t * t

    @staticmethod
    def ease_out_quad(t: float) -> float:
        return 1 - (1 - t) * (1 - t)

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        p = 2 * t - 2
        return 0.5 * p * p * p + 1

    @staticmethod
    def ease_out_cubic(t: float) -> float:
        p = t - 1
        return p * p * p + 1

    @staticmethod
    def ease_out_back(t: float) -> float:
        c1 = 1.70158
        c3 = c1 + 1
        p = t - 1
        return 1 + c3 * p * p * p + c1 * p * p

    @staticmethod
    def ease_out_elastic(t: float) -> float:
        if t == 0 or t == 1:
            return t
        c4 = (2 * math.pi) / 3
        return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


# ── Color helpers ────────────────────────────────────────────────────────────

_hex_cache: Dict[str, Tuple[int, int, int]] = {}


def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    """``"#1BBFBF"`` -> ``(27, 191, 191)``. Accepts ``#RGB`` and ``#RRGGBB``."""
    s = h.strip()
    if s in _hex_cache:
        return _hex_cache[s]
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    _hex_cache[s] = (r, g, b)
    return r, g, b


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex((lerp(r1, r2, t), lerp(g1, g2, t), lerp(b1, b2, t)))


def lighten(hex_color: str, amount: float) -> str:
    """Move ``hex_color`` toward white by ``amount`` in [0, 1]."""
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex((
        lerp(r, 255, amount),
        lerp(g, 255, amount),
        lerp(b, 255, amount),
    ))


def darken(hex_color: str, amount: float) -> str:
    """Move ``hex_color`` toward black by ``amount`` in [0, 1]."""
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hex((lerp(r, 0, amount), lerp(g, 0, amount), lerp(b, 0, amount)))


# ── The engine ───────────────────────────────────────────────────────────────

class _Tween:
    __slots__ = (
        "tid", "widget", "props", "fr", "to", "duration", "delay", "easing",
        "start_ms", "on_done", "done", "tag",
    )

    def __init__(
        self,
        tid: int,
        widget: Any,
        fr: Dict[str, Any],
        to: Dict[str, Any],
        duration: int,
        delay: int,
        easing: Callable[[float], float],
        on_done: Optional[Callable],
    ):
        self.tid = tid
        self.widget = widget
        self.props = list(to.keys())
        self.fr = fr
        self.to = to
        self.duration = max(1, duration)
        self.delay = max(0, delay)
        self.easing = easing
        self.start_ms = int(time.time() * 1000) + self.delay
        self.on_done = on_done
        self.done = False
        self.tag = None  # for grouping / batched cancel


def _is_widget_alive(w: Any) -> bool:
    if w is None:
        return False
    try:
        # winfo_id raises TclError if the widget is destroyed
        w.winfo_id()
        return True
    except Exception:
        return False


def _is_widget_mapped(w: Any) -> bool:
    if w is None:
        return False
    try:
        return bool(w.winfo_ismapped())
    except Exception:
        return False


def _apply_tween(t: _Tween) -> bool:
    """Mutate widget props for tween ``t``. Returns True if the tween is done."""
    now = int(time.time() * 1000)
    elapsed = now - t.start_ms
    if elapsed < 0:
        return False
    progress = min(1.0, elapsed / t.duration)
    eased = t.easing(progress)

    if _is_widget_alive(t.widget) and _is_widget_mapped(t.widget):
        try:
            cfg: Dict[str, Any] = {}
            for k in t.props:
                fv = t.fr.get(k)
                tv = t.to[k]
                if isinstance(fv, (int, float)) and isinstance(tv, (int, float)):
                    cfg[k] = fv + (tv - fv) * eased
                elif isinstance(fv, str) and isinstance(tv, str):
                    if fv.startswith("#") and tv.startswith("#") and len(fv) == 7 and len(tv) == 7:
                        cfg[k] = lerp_color(fv, tv, eased)
                    else:
                        # E.g. font tuples: snap at the halfway point
                        cfg[k] = tv if eased >= 0.5 else fv
                else:
                    cfg[k] = tv
            if cfg:
                t.widget.config(**cfg)
        except tk.TclError:
            return True  # dead widget — drop the tween
    if progress >= 1.0:
        t.done = True
        if t.on_done is not None:
            try:
                t.on_done()
            except Exception:
                pass
        return True
    return False


class Animator:
    """A single shared ticker that drives all active tweens for one root."""

    def __init__(self, root: tk.Misc, frame_budget_ms: int = 16):
        self._root = root
        self._frame_budget_ms = frame_budget_ms
        self._tweens: List[_Tween] = []
        self._next_id = 1
        self._after_id: Optional[str] = None
        self._frame_callbacks: List[Callable[[float, float], None]] = []
        self._stopped = False

    # ── public ───────────────────────────────────────────────────────────

    def tween(
        self,
        widget: Any,
        *,
        to: Dict[str, Any],
        duration: int = 200,
        easing: Callable[[float], float] = Easing.ease_out_quad,
        delay: int = 0,
        on_done: Optional[Callable] = None,
    ) -> int:
        """Tween ``widget``'s properties from their current value to ``to``."""
        fr: Dict[str, Any] = {}
        if _is_widget_alive(widget):
            try:
                cur = widget.config()
                for k in to:
                    val = cur.get(k)
                    fr[k] = val[-1] if isinstance(val, tuple) else val
            except Exception:
                pass
        return self._start(fr, to, widget, duration, delay, easing, on_done)

    def tween_many(
        self,
        widget: Any,
        *,
        fr: Dict[str, Any],
        to: Dict[str, Any],
        duration: int = 200,
        easing: Callable[[float], float] = Easing.ease_out_quad,
        delay: int = 0,
        on_done: Optional[Callable] = None,
    ) -> int:
        """Tween ``widget``'s properties from ``fr`` (explicit) to ``to``."""
        return self._start(fr, to, widget, duration, delay, easing, on_done)

    def sequence(
        self,
        steps: List[Dict[str, Any]],
        *,
        easing: Callable[[float], float] = Easing.ease_out_quad,
        on_done: Optional[Callable] = None,
    ) -> int:
        """Run steps in order. Each step: ``{"to": {...}, "duration": int, "delay": int}``."""
        if not steps:
            if on_done:
                on_done()
            return -1

        def runner(i: int = 0) -> None:
            if i >= len(steps):
                if on_done:
                    on_done()
                return
            s = steps[i]
            widget = s.get("widget")
            to = s.get("to", {})
            duration = s.get("duration", 200)
            delay = s.get("delay", 0)
            on_step_done = s.get("on_done")
            if widget is None:
                runner(i + 1)
                return

            def after_step() -> None:
                if on_step_done:
                    try:
                        on_step_done()
                    except Exception:
                        pass
                runner(i + 1)

            self.tween(
                widget,
                to=to,
                duration=duration,
                delay=delay,
                easing=s.get("easing", easing),
                on_done=after_step,
            )

        runner(0)
        return -1

    def parallel(
        self,
        steps: List[Dict[str, Any]],
        *,
        easing: Callable[[float], float] = Easing.ease_out_quad,
        on_done: Optional[Callable] = None,
    ) -> int:
        """Run all steps simultaneously. Fires ``on_done`` after the last one."""
        if not steps:
            if on_done:
                on_done()
            return -1
        remaining = [len(steps)]

        def make_done(i: int) -> Callable:
            def _done() -> None:
                remaining[0] -= 1
                if remaining[0] <= 0 and on_done:
                    on_done()
            return _done

        for i, s in enumerate(steps):
            widget = s.get("widget")
            if widget is None:
                remaining[0] -= 1
                continue
            self.tween(
                widget,
                to=s.get("to", {}),
                duration=s.get("duration", 200),
                delay=s.get("delay", 0),
                easing=s.get("easing", easing),
                on_done=make_done(i),
            )
        return -1

    def cancel(self, tween_id: int) -> None:
        self._tweens = [t for t in self._tweens if t.tid != tween_id]

    def cancel_all(self) -> None:
        self._tweens.clear()
        self._frame_callbacks.clear()

    def on_frame(
        self,
        callback: Callable[[float, float], None],
    ) -> Callable[[], None]:
        """Subscribe a per-frame callback. Returns an ``unsubscribe`` callable."""
        self._frame_callbacks.append(callback)
        # Make sure the ticker is running so the callback actually fires.
        self._ensure_ticker()

        def _unsub() -> None:
            try:
                self._frame_callbacks.remove(callback)
            except ValueError:
                pass

        return _unsub

    def is_running(self, tween_id: int) -> bool:
        return any(t.tid == tween_id and not t.done for t in self._tweens)

    def stop(self) -> None:
        """Hard stop — cancels all tweens and unsubscribes the ticker."""
        self._stopped = True
        if self._after_id is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
        self._tweens.clear()
        self._frame_callbacks.clear()

    # ── internal ─────────────────────────────────────────────────────────

    def _start(
        self,
        fr: Dict[str, Any],
        to: Dict[str, Any],
        widget: Any,
        duration: int,
        delay: int,
        easing: Callable[[float], float],
        on_done: Optional[Callable],
    ) -> int:
        if self._stopped:
            return -1
        tid = self._next_id
        self._next_id += 1
        self._tweens.append(_Tween(tid, widget, None, fr, to, duration, delay, easing, on_done))
        self._ensure_ticker()
        return tid

    def _ensure_ticker(self) -> None:
        if self._after_id is not None or self._stopped:
            return
        try:
            self._after_id = self._root.after(self._frame_budget_ms, self._tick)
        except Exception:
            self._after_id = None

    def _tick(self) -> None:
        self._after_id = None
        if self._stopped:
            return
        if not self._tweens and not self._frame_callbacks:
            return
        now = time.time()
        # Apply tweens
        if self._tweens:
            done: List[_Tween] = []
            for t in self._tweens:
                if _apply_tween(t):
                    done.append(t)
            for t in done:
                if t in self._tweens:
                    self._tweens.remove(t)
        # Per-frame callbacks
        if self._frame_callbacks:
            dt = self._frame_budget_ms / 1000.0
            for cb in list(self._frame_callbacks):
                try:
                    cb(dt, now)
                except Exception:
                    pass
        if self._tweens or self._frame_callbacks:
            self._ensure_ticker()


__all__ = [
    "Easing",
    "Animator",
    "hex_to_rgb",
    "rgb_to_hex",
    "lerp",
    "lerp_color",
    "lighten",
    "darken",
]
