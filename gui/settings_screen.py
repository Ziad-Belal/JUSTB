# gui/settings_screen.py
import tkinter as tk
from tkinter import ttk, messagebox
from utils.helpers import load_json, save_json
from utils.security import verify_password, hash_password
import os

# ── Design tokens ──────────────────────────────────────────────────────────────
C = {
    "bg_root":    "#F7F5FF",
    "bg_card":    "#FFFFFF",
    "bg_panel":   "#F0EDFF",
    "bg_row_alt": "#FAF8FF",
    "purple":     "#8B5CF6",
    "teal":       "#1BBFBF",
    "green":      "#22C55E",
    "danger":     "#DC2626",
    "success":    "#16A34A",
    "border":     "#E8E4F8",
    "text_dark":  "#1A1035",
    "text_mid":   "#6B6B8A",
    "text_light": "#A8A8C0",
}
BRAND_COLORS = ["#1BBFBF", "#F0569A", "#F97316", "#8B5CF6", "#22C55E"]

FONT_HEAD    = ("Georgia",  13, "bold")
FONT_LABEL_B = ("Segoe UI", 10, "bold")
FONT_ENTRY   = ("Segoe UI", 11)
FONT_BTN     = ("Segoe UI", 10, "bold")
FONT_SMALL   = ("Segoe UI",  9)
FONT_SECTION = ("Segoe UI",  8, "bold")


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _entry(parent, show=None, width=26):
    return tk.Entry(parent, font=FONT_ENTRY, show=show or "", width=width,
                    bg="#FFFFFF", fg=C["text_dark"], relief="flat",
                    highlightthickness=2,
                    highlightbackground=C["border"],
                    highlightcolor=C["purple"])

def _btn(parent, text, command, bg, hover, fg="#FFFFFF", padx=20, pady=9):
    b = tk.Label(parent, text=text, font=FONT_BTN,
                 bg=bg, fg=fg, cursor="hand2",
                 relief="flat", padx=padx, pady=pady)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b

def _card(parent, accent=None):
    """White card with optional top accent colour bar."""
    outer = tk.Frame(parent, bg=C["bg_card"],
                     highlightthickness=1,
                     highlightbackground=C["border"])
    if accent:
        tk.Frame(outer, bg=accent, height=3).pack(fill="x")
    inner = tk.Frame(outer, bg=C["bg_card"], padx=28, pady=20)
    inner.pack(fill="both", expand=True)
    return outer, inner

def _section_title(parent, text):
    tk.Label(parent, text=text, font=FONT_SECTION,
             bg=C["bg_card"], fg=C["text_light"]).grid(
                 row=0, column=0, columnspan=3,
                 sticky="w", pady=(0, 14))

def _field(parent, row, label, widget):
    tk.Label(parent, text=label, font=FONT_LABEL_B,
             bg=C["bg_card"], fg=C["text_mid"]).grid(
                 row=row, column=0, sticky="w", pady=6, padx=(0, 20))
    widget.grid(row=row, column=1, sticky="w", pady=6, ipady=6)

def _status_lbl(parent, row):
    lbl = tk.Label(parent, text="", font=FONT_SMALL,
                   bg=C["bg_card"], fg=C["success"])
    lbl.grid(row=row, column=0, columnspan=3, sticky="w", pady=(6, 0))
    return lbl

def _set_status(label, msg, error=False):
    label.config(text=msg, fg=C["danger"] if error else C["success"])


# ══════════════════════════════════════════════════════════════════════════════
class SettingsScreen:

    def __init__(self, root, data_dir, frame_parent=None, user=None):
        self.root     = root
        self.data_dir = data_dir
        self.user     = user or {}

        # Scrollable container
        outer = tk.Frame(frame_parent or root, bg=C["bg_root"])
        outer.pack(fill="both", expand=True)

        # Header
        hdr = tk.Frame(outer, bg=C["bg_card"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
        hdr.pack(fill="x")

        dots = tk.Frame(hdr, bg=C["bg_card"])
        dots.pack(side="left", padx=(16, 4), pady=10)
        for col in BRAND_COLORS:
            tk.Label(dots, text="●", font=("Segoe UI", 9),
                     bg=C["bg_card"], fg=col).pack(side="left", padx=1)
        tk.Label(hdr, text="Settings", font=FONT_HEAD,
                 bg=C["bg_card"], fg=C["text_dark"]).pack(
                     side="left", padx=(6, 0), pady=10)

        # Canvas + scrollbar for body
        canvas = tk.Canvas(outer, bg=C["bg_root"], highlightthickness=0)
        vsb    = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.body = tk.Frame(canvas, bg=C["bg_root"])
        win_id = canvas.create_window((0, 0), window=self.body, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(win_id, width=e.width)
        def _on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))

        canvas.bind("<Configure>", _on_resize)
        self.body.bind("<Configure>", _on_frame_configure)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self.frame = outer   # expose .frame so login_screen can add it to notebook

        self._build()

    def _users_path(self):
        return os.path.join(self.data_dir, "users.json")

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        pad = {"padx": 30, "pady": (16, 0), "fill": "x"}

        card1, inner1 = _card(self.body, accent=C["purple"])
        card1.pack(**pad)
        self._build_my_password(inner1)

        card2, inner2 = _card(self.body, accent=C["green"])
        card2.pack(**pad)
        self._build_create_cashier(inner2)

        card3, inner3 = _card(self.body, accent=C["teal"])
        card3.pack(padx=30, pady=(16, 30), fill="x")
        self._build_cashier_password(inner3)

        # Now all widgets exist — safe to populate
        self._refresh_cashier_list()

    # ══════════════════════════════════════════════════════════════════
    #  Card 1 — Change MY password
    # ══════════════════════════════════════════════════════════════════
    def _build_my_password(self, p):
        _section_title(p, "CHANGE MY PASSWORD")

        self.my_old     = _entry(p, show="*")
        self.my_new     = _entry(p, show="*")
        self.my_confirm = _entry(p, show="*")

        _field(p, 1, "Current password",     self.my_old)
        _field(p, 2, "New password",          self.my_new)
        _field(p, 3, "Confirm new password",  self.my_confirm)

        self.my_confirm.bind("<Return>", lambda e: self._change_my_password())

        self.my_status = _status_lbl(p, 4)
        _btn(p, "Save new password",
             self._change_my_password,
             C["purple"], "#7C3AED").grid(
                 row=5, column=0, columnspan=2, sticky="w", pady=(14, 4))

    # ══════════════════════════════════════════════════════════════════
    #  Card 2 — Create cashier account
    # ══════════════════════════════════════════════════════════════════
    def _build_create_cashier(self, p):
        _section_title(p, "CREATE CASHIER ACCOUNT")

        self.new_uname  = _entry(p)
        self.new_pass   = _entry(p, show="*")
        self.new_pass2  = _entry(p, show="*")

        _field(p, 1, "Username",         self.new_uname)
        _field(p, 2, "Password",         self.new_pass)
        _field(p, 3, "Confirm password", self.new_pass2)

        self.new_pass2.bind("<Return>", lambda e: self._create_cashier())

        self.create_status = _status_lbl(p, 4)

        btn_row = tk.Frame(p, bg=C["bg_card"])
        btn_row.grid(row=5, column=0, columnspan=3, sticky="w", pady=(14, 4))

        _btn(btn_row, "Create account",
             self._create_cashier,
             C["green"], "#16A34A").pack(side="left", padx=(0, 12))

        # Live cashier list — sits to the right inside the same card
        list_frame = tk.Frame(p, bg=C["bg_card"],
                              highlightthickness=1,
                              highlightbackground=C["border"])
        list_frame.grid(row=1, column=2, rowspan=5,
                        padx=(30, 0), pady=0, sticky="nsew")

        tk.Label(list_frame, text="EXISTING CASHIERS",
                 font=FONT_SECTION, bg=C["bg_panel"],
                 fg=C["text_mid"],
                 padx=10, pady=6).pack(fill="x")

        self.cashier_list = tk.Listbox(
            list_frame, font=("Segoe UI", 10),
            bg=C["bg_card"], fg=C["text_dark"],
            selectbackground=C["bg_panel"],
            selectforeground=C["purple"],
            relief="flat", highlightthickness=0,
            activestyle="none", width=22, height=6)
        self.cashier_list.pack(fill="both", expand=True, padx=8, pady=8)

        _btn(list_frame, "🗑  Delete selected",
             self._delete_cashier,
             C["danger"], "#B91C1C",
             padx=12, pady=6).pack(fill="x", padx=8, pady=(0, 8))


    # ══════════════════════════════════════════════════════════════════
    #  Card 3 — Change a cashier's password
    # ══════════════════════════════════════════════════════════════════
    def _build_cashier_password(self, p):
        _section_title(p, "CHANGE A CASHIER'S PASSWORD")

        self.cashier_var = tk.StringVar()
        self.cashier_cb  = ttk.Combobox(p, textvariable=self.cashier_var,
                                         state="readonly", width=24,
                                         font=FONT_ENTRY)

        tk.Label(p, text="Select cashier", font=FONT_LABEL_B,
                 bg=C["bg_card"], fg=C["text_mid"]).grid(
                     row=1, column=0, sticky="w", pady=6, padx=(0, 20))
        self.cashier_cb.grid(row=1, column=1, sticky="w", pady=6, ipady=4)

        refresh = tk.Label(p, text="↺", font=FONT_LABEL_B,
                           bg=C["bg_card"], fg=C["purple"], cursor="hand2")
        refresh.grid(row=1, column=2, padx=(8, 0))
        refresh.bind("<Button-1>", lambda e: self._load_cashier_dropdown())

        self.c_new     = _entry(p, show="*")
        self.c_confirm = _entry(p, show="*")

        _field(p, 2, "New password",         self.c_new)
        _field(p, 3, "Confirm new password",  self.c_confirm)

        self.c_confirm.bind("<Return>", lambda e: self._change_cashier_password())

        self.c_status = _status_lbl(p, 4)
        _btn(p, "Set cashier password",
             self._change_cashier_password,
             C["teal"], "#159F9F").grid(
                 row=5, column=0, columnspan=2, sticky="w", pady=(14, 4))


    # ─────────────────────────────────────────────────────────────────
    def _refresh_cashier_list(self):
        self.cashier_list.delete(0, tk.END)
        users = load_json(self._users_path())
        for u in users:
            if u.get("role", "").strip().lower() != "admin":
                self.cashier_list.insert(tk.END, u["username"])
        self._load_cashier_dropdown()

    def _load_cashier_dropdown(self):
        users    = load_json(self._users_path())
        cashiers = [u["username"] for u in users
                    if u.get("role", "").strip().lower() != "admin"]
        self.cashier_cb["values"] = cashiers
        self.cashier_cb.set(cashiers[0] if cashiers else "")

    # ── Logic: change my password ──────────────────────────────────────
    def _change_my_password(self):
        old, new, confirm = (self.my_old.get(),
                             self.my_new.get(),
                             self.my_confirm.get())
        if not all([old, new, confirm]):
            _set_status(self.my_status, "All fields are required.", error=True); return
        if new != confirm:
            _set_status(self.my_status, "New passwords do not match.", error=True); return
        if len(new) < 6:
            _set_status(self.my_status, "Minimum 6 characters.", error=True); return

        users    = load_json(self._users_path())
        user_obj = next((u for u in users
                         if u.get("username") == self.user.get("username")), None)
        if not user_obj:
            _set_status(self.my_status, "User not found.", error=True); return
        if not verify_password(user_obj["password"], old):
            _set_status(self.my_status, "Current password is incorrect.", error=True)
            self.my_old.delete(0, tk.END); self.my_old.focus(); return

        user_obj["password"] = hash_password(new)
        save_json(self._users_path(), users)
        for e in (self.my_old, self.my_new, self.my_confirm):
            e.delete(0, tk.END)
        _set_status(self.my_status, "Password changed successfully.")

    # ── Logic: create cashier account ─────────────────────────────────
    def _create_cashier(self):
        uname   = self.new_uname.get().strip()
        pwd     = self.new_pass.get()
        confirm = self.new_pass2.get()

        if not uname:
            _set_status(self.create_status, "Username is required.", error=True); return
        if len(uname) < 3:
            _set_status(self.create_status, "Username must be at least 3 characters.", error=True); return
        if not pwd or not confirm:
            _set_status(self.create_status, "Both password fields are required.", error=True); return
        if pwd != confirm:
            _set_status(self.create_status, "Passwords do not match.", error=True); return
        if len(pwd) < 6:
            _set_status(self.create_status, "Minimum 6 characters for password.", error=True); return

        users = load_json(self._users_path())
        if any(u.get("username", "").strip().lower() == uname.lower() for u in users):
            _set_status(self.create_status,
                        f"Username '{uname}' already exists.", error=True); return

        users.append({
            "username": uname,
            "password": hash_password(pwd),
            "role":     "worker",
        })
        save_json(self._users_path(), users)

        self.new_uname.delete(0, tk.END)
        self.new_pass.delete(0, tk.END)
        self.new_pass2.delete(0, tk.END)
        self.new_uname.focus()

        self._refresh_cashier_list()
        _set_status(self.create_status,
                    f"Account '{uname}' created successfully.")

    # ── Logic: delete cashier account ─────────────────────────────────
    def _delete_cashier(self):
        sel = self.cashier_list.curselection()
        if not sel:
            messagebox.showinfo("Select Cashier",
                                "Select a cashier from the list first.")
            return
        uname = self.cashier_list.get(sel[0])
        if not messagebox.askyesno("Delete Account",
                                   f"Permanently delete account '{uname}'?\n"
                                   "This cannot be undone."):
            return
        users = load_json(self._users_path())
        users = [u for u in users if u.get("username") != uname]
        save_json(self._users_path(), users)
        self._refresh_cashier_list()
        _set_status(self.create_status, f"Account '{uname}' deleted.")

    # ── Logic: change cashier password ────────────────────────────────
    def _change_cashier_password(self):
        target  = self.cashier_var.get().strip()
        new     = self.c_new.get()
        confirm = self.c_confirm.get()

        if not target:
            _set_status(self.c_status, "Please select a cashier.", error=True); return
        if not new or not confirm:
            _set_status(self.c_status, "Both fields are required.", error=True); return
        if new != confirm:
            _set_status(self.c_status, "Passwords do not match.", error=True); return
        if len(new) < 6:
            _set_status(self.c_status, "Minimum 6 characters.", error=True); return

        users    = load_json(self._users_path())
        user_obj = next((u for u in users if u.get("username") == target), None)

        if not user_obj:
            _set_status(self.c_status, f"'{target}' not found.", error=True); return
        if user_obj.get("role", "").strip().lower() == "admin":
            _set_status(self.c_status,
                        "Cannot change an admin password here.", error=True); return

        user_obj["password"] = hash_password(new)
        save_json(self._users_path(), users)
        self.c_new.delete(0, tk.END)
        self.c_confirm.delete(0, tk.END)
        _set_status(self.c_status,
                    f"Password for '{target}' updated successfully.")