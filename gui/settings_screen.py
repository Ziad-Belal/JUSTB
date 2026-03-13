# gui/settings_screen.py
import tkinter as tk
from tkinter import ttk, messagebox
from utils.helpers import load_json, save_json
from utils.security import verify_password, hash_password
import os

C = {
    "bg_root":    "#F7F5FF",
    "bg_card":    "#FFFFFF",
    "bg_panel":   "#F0EDFF",
    "purple":     "#8B5CF6",
    "teal":       "#1BBFBF",
    "danger":     "#DC2626",
    "success":    "#16A34A",
    "border":     "#E8E4F8",
    "border_acc": "#C4B8F5",
    "text_dark":  "#1A1035",
    "text_mid":   "#6B6B8A",
    "text_light": "#A8A8C0",
}

FONT_HEAD    = ("Georgia",  13, "bold")
FONT_LABEL_B = ("Segoe UI", 10, "bold")
FONT_ENTRY   = ("Segoe UI", 11)
FONT_BTN     = ("Segoe UI", 10, "bold")
FONT_SMALL   = ("Segoe UI",  9)
FONT_SECTION = ("Segoe UI",  8, "bold")


def _entry(parent, show=None, width=28):
    return tk.Entry(parent, font=FONT_ENTRY, show=show or "", width=width,
                    bg="#FFFFFF", fg=C["text_dark"], relief="flat",
                    highlightthickness=2,
                    highlightbackground=C["border"],
                    highlightcolor=C["purple"])

def _btn(parent, text, command, bg, hover):
    b = tk.Label(parent, text=text, font=FONT_BTN,
                 bg=bg, fg="#FFFFFF", cursor="hand2",
                 relief="flat", padx=20, pady=9)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b

def _card(parent):
    return tk.Frame(parent, bg=C["bg_card"],
                    highlightthickness=1,
                    highlightbackground=C["border"],
                    padx=28, pady=24)


class SettingsScreen:
    def __init__(self, root, data_dir, frame_parent=None, user=None):
        self.root     = root
        self.data_dir = data_dir
        self.user     = user or {}

        self.frame = tk.Frame(frame_parent or root, bg=C["bg_root"])
        self.frame.pack(fill="both", expand=True)

        self._build()

    def _users_path(self):
        return os.path.join(self.data_dir, "users.json")

    def _build(self):
        hdr = tk.Frame(self.frame, bg=C["bg_card"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="Settings", font=FONT_HEAD,
                 bg=C["bg_card"], fg=C["text_dark"]).pack(
                     side="left", padx=20, pady=12)

        body = tk.Frame(self.frame, bg=C["bg_root"])
        body.pack(fill="both", expand=True, padx=40, pady=20)

        self._build_my_password(body)
        self._build_cashier_password(body)

    # ── Card 1: Change my own password ───────────────────────────────
    def _build_my_password(self, parent):
        card = _card(parent)
        card.pack(fill="x", pady=(0, 20))

        tk.Frame(card, bg=C["purple"], height=3).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        tk.Label(card, text="CHANGE MY PASSWORD",
                 font=FONT_SECTION, bg=C["bg_card"],
                 fg=C["text_light"]).grid(
                     row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        tk.Label(card, text="Current password", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=2, column=0, sticky="w", pady=6, padx=(0, 20))
        self.my_old = _entry(card, show="*")
        self.my_old.grid(row=2, column=1, sticky="w", pady=6, ipady=6)

        tk.Label(card, text="New password", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=3, column=0, sticky="w", pady=6, padx=(0, 20))
        self.my_new = _entry(card, show="*")
        self.my_new.grid(row=3, column=1, sticky="w", pady=6, ipady=6)

        tk.Label(card, text="Confirm new password", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=4, column=0, sticky="w", pady=6, padx=(0, 20))
        self.my_confirm = _entry(card, show="*")
        self.my_confirm.grid(row=4, column=1, sticky="w", pady=6, ipady=6)
        self.my_confirm.bind("<Return>", lambda e: self._change_my_password())

        self.my_status = tk.Label(card, text="", font=FONT_SMALL,
                                   bg=C["bg_card"], fg=C["success"])
        self.my_status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        _btn(card, "Save new password",
             self._change_my_password, C["purple"], "#7C3AED").grid(
                 row=6, column=0, columnspan=2, sticky="w", pady=(14, 0))

    # ── Card 2: Change a cashier's password ──────────────────────────
    def _build_cashier_password(self, parent):
        card = _card(parent)
        card.pack(fill="x", pady=(0, 20))

        tk.Frame(card, bg=C["teal"], height=3).grid(
            row=0, column=0, columnspan=3, sticky="ew", pady=(0, 14))
        tk.Label(card, text="CHANGE A CASHIER'S PASSWORD",
                 font=FONT_SECTION, bg=C["bg_card"],
                 fg=C["text_light"]).grid(
                     row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        tk.Label(card, text="Select cashier", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=2, column=0, sticky="w", pady=6, padx=(0, 20))
        self.cashier_var = tk.StringVar()
        self.cashier_cb  = ttk.Combobox(card, textvariable=self.cashier_var,
                                         state="readonly", width=26,
                                         font=FONT_ENTRY)
        self.cashier_cb.grid(row=2, column=1, sticky="w", pady=6, ipady=4)

        refresh = tk.Label(card, text="↺ Refresh", font=FONT_SMALL,
                           bg=C["bg_card"], fg=C["purple"], cursor="hand2")
        refresh.grid(row=2, column=2, padx=(10, 0))
        refresh.bind("<Button-1>", lambda e: self._load_cashiers())

        tk.Label(card, text="New password", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=3, column=0, sticky="w", pady=6, padx=(0, 20))
        self.c_new = _entry(card, show="*")
        self.c_new.grid(row=3, column=1, sticky="w", pady=6, ipady=6)

        tk.Label(card, text="Confirm new password", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=4, column=0, sticky="w", pady=6, padx=(0, 20))
        self.c_confirm = _entry(card, show="*")
        self.c_confirm.grid(row=4, column=1, sticky="w", pady=6, ipady=6)
        self.c_confirm.bind("<Return>", lambda e: self._change_cashier_password())

        self.c_status = tk.Label(card, text="", font=FONT_SMALL,
                                  bg=C["bg_card"], fg=C["success"])
        self.c_status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        _btn(card, "Set cashier password",
             self._change_cashier_password, C["teal"], "#159F9F").grid(
                 row=6, column=0, columnspan=2, sticky="w", pady=(14, 0))

        self._load_cashiers()

    def _load_cashiers(self):
        users    = load_json(self._users_path())
        cashiers = [u["username"] for u in users
                    if u.get("role", "").strip().lower() != "admin"]
        self.cashier_cb["values"] = cashiers
        self.cashier_cb.set(cashiers[0] if cashiers else "")

    # ── Logic ─────────────────────────────────────────────────────────
    def _change_my_password(self):
        old, new, confirm = self.my_old.get(), self.my_new.get(), self.my_confirm.get()

        if not all([old, new, confirm]):
            self._status(self.my_status, "All fields are required.", error=True); return
        if new != confirm:
            self._status(self.my_status, "New passwords do not match.", error=True); return
        if len(new) < 6:
            self._status(self.my_status, "Minimum 6 characters required.", error=True); return

        users    = load_json(self._users_path())
        user_obj = next((u for u in users
                         if u.get("username") == self.user.get("username")), None)
        if not user_obj:
            self._status(self.my_status, "User not found.", error=True); return
        if not verify_password(user_obj["password"], old):
            self._status(self.my_status, "Current password is incorrect.", error=True)
            self.my_old.delete(0, tk.END); self.my_old.focus(); return

        user_obj["password"] = hash_password(new)
        save_json(self._users_path(), users)
        for e in (self.my_old, self.my_new, self.my_confirm): e.delete(0, tk.END)
        self._status(self.my_status, "Password changed successfully.")

    def _change_cashier_password(self):
        target  = self.cashier_var.get().strip()
        new     = self.c_new.get()
        confirm = self.c_confirm.get()

        if not target:
            self._status(self.c_status, "Please select a cashier.", error=True); return
        if not new or not confirm:
            self._status(self.c_status, "Both password fields are required.", error=True); return
        if new != confirm:
            self._status(self.c_status, "Passwords do not match.", error=True); return
        if len(new) < 6:
            self._status(self.c_status, "Minimum 6 characters required.", error=True); return

        users    = load_json(self._users_path())
        user_obj = next((u for u in users if u.get("username") == target), None)

        if not user_obj:
            self._status(self.c_status, f"'{target}' not found.", error=True); return
        # Safety: block changing another admin's password through this section
        if user_obj.get("role", "").strip().lower() == "admin":
            self._status(self.c_status, "Cannot change an admin password here.", error=True); return

        user_obj["password"] = hash_password(new)
        save_json(self._users_path(), users)
        self.c_new.delete(0, tk.END); self.c_confirm.delete(0, tk.END)
        self._status(self.c_status, f"Password for '{target}' updated successfully.")

    def _status(self, label, msg, error=False):
        label.config(text=msg, fg=C["danger"] if error else C["success"])