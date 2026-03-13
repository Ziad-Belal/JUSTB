# gui/settings_screen.py
import tkinter as tk
from tkinter import messagebox
from utils.helpers import load_json, save_json
from utils.security import verify_password, hash_password
import os

C = {
    "bg_root":    "#F7F5FF",
    "bg_card":    "#FFFFFF",
    "bg_panel":   "#F0EDFF",
    "purple":     "#8B5CF6",
    "danger":     "#DC2626",
    "success":    "#16A34A",
    "border":     "#E8E4F8",
    "text_dark":  "#1A1035",
    "text_mid":   "#6B6B8A",
    "text_light": "#A8A8C0",
}

FONT_HEAD    = ("Georgia",  13, "bold")
FONT_LABEL   = ("Segoe UI", 10)
FONT_LABEL_B = ("Segoe UI", 10, "bold")
FONT_ENTRY   = ("Segoe UI", 11)
FONT_BTN     = ("Segoe UI", 10, "bold")
FONT_SMALL   = ("Segoe UI",  9)
FONT_SECTION = ("Segoe UI",  8, "bold")


class SettingsScreen:
    def __init__(self, root, data_dir, frame_parent=None, user=None):
        self.root      = root
        self.data_dir  = data_dir
        self.user      = user or {}

        self.frame = tk.Frame(frame_parent or root, bg=C["bg_root"])
        self.frame.pack(fill="both", expand=True)

        self._build()

    def _build(self):
        # ── Page header ───────────────────────────────────────────────
        hdr = tk.Frame(self.frame, bg=C["bg_card"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        hdr.pack(fill="x")
        tk.Label(hdr, text="Settings",
                 font=FONT_HEAD, bg=C["bg_card"],
                 fg=C["text_dark"]).pack(side="left", padx=20, pady=12)

        # ── Change Password card ──────────────────────────────────────
        card = tk.Frame(self.frame, bg=C["bg_card"],
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        padx=28, pady=24)
        card.pack(padx=40, pady=30, anchor="n", fill="x")

        # Purple accent bar
        tk.Frame(card, bg=C["purple"], height=3).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        tk.Label(card, text="CHANGE PASSWORD",
                 font=FONT_SECTION, bg=C["bg_card"],
                 fg=C["text_light"]).grid(
                     row=1, column=0, columnspan=2, sticky="w", pady=(0, 16))

        # Current password
        tk.Label(card, text="Current password",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=2, column=0, sticky="w", pady=6, padx=(0, 20))
        self.old_entry = tk.Entry(card, font=FONT_ENTRY, show="*", width=28,
                                   bg="#FFFFFF", fg=C["text_dark"],
                                   relief="flat", highlightthickness=2,
                                   highlightbackground=C["border"],
                                   highlightcolor=C["purple"])
        self.old_entry.grid(row=2, column=1, sticky="w", pady=6, ipady=6)

        # New password
        tk.Label(card, text="New password",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=3, column=0, sticky="w", pady=6, padx=(0, 20))
        self.new_entry = tk.Entry(card, font=FONT_ENTRY, show="*", width=28,
                                   bg="#FFFFFF", fg=C["text_dark"],
                                   relief="flat", highlightthickness=2,
                                   highlightbackground=C["border"],
                                   highlightcolor=C["purple"])
        self.new_entry.grid(row=3, column=1, sticky="w", pady=6, ipady=6)

        # Confirm new password
        tk.Label(card, text="Confirm new password",
                 font=FONT_LABEL_B, bg=C["bg_card"],
                 fg=C["text_mid"]).grid(row=4, column=0, sticky="w", pady=6, padx=(0, 20))
        self.confirm_entry = tk.Entry(card, font=FONT_ENTRY, show="*", width=28,
                                       bg="#FFFFFF", fg=C["text_dark"],
                                       relief="flat", highlightthickness=2,
                                       highlightbackground=C["border"],
                                       highlightcolor=C["purple"])
        self.confirm_entry.grid(row=4, column=1, sticky="w", pady=6, ipady=6)
        self.confirm_entry.bind("<Return>", lambda e: self._change_password())

        # Status label
        self.status = tk.Label(card, text="", font=FONT_SMALL,
                                bg=C["bg_card"], fg=C["success"])
        self.status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # Save button
        btn = tk.Label(card, text="Save new password",
                       font=FONT_BTN, bg=C["purple"], fg="#FFFFFF",
                       cursor="hand2", relief="flat", padx=20, pady=9)
        btn.grid(row=6, column=0, columnspan=2, sticky="w", pady=(14, 0))
        btn.bind("<Button-1>", lambda e: self._change_password())
        btn.bind("<Enter>",    lambda e: btn.config(bg="#7C3AED"))
        btn.bind("<Leave>",    lambda e: btn.config(bg=C["purple"]))

    # ─────────────────────────────────────────────────────────────────
    def _change_password(self):
        old     = self.old_entry.get()
        new     = self.new_entry.get()
        confirm = self.confirm_entry.get()

        if not old or not new or not confirm:
            self._status("All fields are required.", error=True)
            return

        if new != confirm:
            self._status("New passwords do not match.", error=True)
            return

        if len(new) < 6:
            self._status("New password must be at least 6 characters.", error=True)
            return

        # Load users and find this admin
        users_path = os.path.join(self.data_dir, "users.json")
        users      = load_json(users_path)
        username   = self.user.get("username", "")
        user_obj   = next((u for u in users
                           if u.get("username") == username), None)

        if not user_obj:
            self._status("User not found in database.", error=True)
            return

        # Verify current password
        if not verify_password(user_obj["password"], old):
            self._status("Current password is incorrect.", error=True)
            self.old_entry.delete(0, tk.END)
            self.old_entry.focus()
            return

        # Hash and save new password
        user_obj["password"] = hash_password(new)
        save_json(users_path, users)

        # Clear fields
        self.old_entry.delete(0, tk.END)
        self.new_entry.delete(0, tk.END)
        self.confirm_entry.delete(0, tk.END)

        self._status("Password changed successfully.", error=False)

    def _status(self, msg, error=False):
        self.status.config(text=msg,
                           fg=C["danger"] if error else C["success"])