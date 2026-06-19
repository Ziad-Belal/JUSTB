import tkinter as tk
from tkinter import messagebox, ttk
from gui.pos_screen import POSScreen
from gui.product_management import ProductManagementScreen
from gui.promo_management import PromoManagementScreen
from gui.daily_feedback import DailyFeedbackScreen
from gui.receipt_database import ReceiptDatabaseScreen
from gui.settings_screen import SettingsScreen
from utils.helpers import load_json, save_json
from utils.security import verify_password, hash_password, is_hashed
import os


# ══════════════════════════════════════════════════════════════════════════════
#  Design tokens  — identical to the rest of the JustB system
# ══════════════════════════════════════════════════════════════════════════════
C = {
    "bg_root":    "#F7F5FF",
    "bg_card":    "#FFFFFF",
    "bg_panel":   "#F0EDFF",
    "bg_input":   "#FFFFFF",
    "purple":     "#8B5CF6",
    "purple_dk":  "#7C3AED",
    "teal":       "#1BBFBF",
    "pink":       "#F0569A",
    "orange":     "#F97316",
    "green":      "#22C55E",
    "border":     "#E8E4F8",
    "border_acc": "#C4B8F5",
    "text_dark":  "#1A1035",
    "text_mid":   "#6B6B8A",
    "text_light": "#A8A8C0",
    "success":    "#16A34A",
    "danger":     "#DC2626",
}
BRAND_COLORS  = ["#1BBFBF", "#F0569A", "#F97316", "#8B5CF6", "#22C55E"]
BRAND_LETTERS = list("JustB")

FONT_BRAND   = ("Georgia",  28, "bold")
FONT_HEAD    = ("Georgia",  13, "bold")
FONT_LABEL_B = ("Segoe UI", 10, "bold")
FONT_LABEL   = ("Segoe UI", 10)
FONT_ENTRY   = ("Segoe UI", 12)
FONT_BTN     = ("Segoe UI", 11, "bold")
FONT_SMALL   = ("Segoe UI",  9)
FONT_SECTION = ("Segoe UI",  8, "bold")


# ══════════════════════════════════════════════════════════════════════════════
#  Splash Screen
# ══════════════════════════════════════════════════════════════════════════════

class SplashScreen(tk.Toplevel):
    """
    Bright splash screen matching JustB's lavender-white theme.
    Animations:
      1. Each brand letter drops and bounces into place (staggered)
      2. Tagline and dots fade in
      3. Purple progress bar fills, then calls on_done()
    """

    BAR_STEPS = 55

    def __init__(self, master, on_done):
        super().__init__(master)
        self.on_done = on_done

        self.overrideredirect(True)
        self.configure(bg=C["bg_root"])

        W, H = 460, 300
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")
        self.lift()
        self.attributes("-topmost", True)

        self.canvas = tk.Canvas(self, width=W, height=H,
                                bg=C["bg_root"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Thin purple border
        self.canvas.create_rectangle(1, 1, W-2, H-2,
                                     outline=C["border_acc"], width=2)

        # Soft lavender glow blob behind letters
        self.canvas.create_oval(60, 30, 400, 200,
                                fill="#EDE9FF", outline="")

        # ── Brand letters (start above canvas, will drop in) ──────────────────
        self._letter_ids = []
        letter_y_final = 105
        letter_start_x = W // 2 - 86

        for i, (ch, col) in enumerate(zip(BRAND_LETTERS, BRAND_COLORS)):
            lx  = letter_start_x + i * 36
            lid = self.canvas.create_text(
                lx, -30, text=ch,
                font=FONT_BRAND, fill=col, anchor="center"
            )
            self._letter_ids.append((lid, lx, letter_y_final))

        # ── Tagline ───────────────────────────────────────────────────────────
        self._tag_id = self.canvas.create_text(
            W // 2, 150,
            text="Retail Management System",
            font=("Segoe UI", 11, "italic"),
            fill=C["bg_root"],
            anchor="center"
        )

        # ── Rainbow dot row ───────────────────────────────────────────────────
        dot_spacing = 18
        dot_start   = W // 2 - (len(BRAND_COLORS) - 1) * dot_spacing // 2
        self._dot_ids = []
        for i, col in enumerate(BRAND_COLORS):
            did = self.canvas.create_text(
                dot_start + i * dot_spacing, 174,
                text="●", font=("Segoe UI", 9),
                fill=C["bg_root"], anchor="center"
            )
            self._dot_ids.append((did, col))

        # ── Progress bar ──────────────────────────────────────────────────────
        bar_y  = H - 38
        bar_x1 = 60
        bar_x2 = W - 60
        self.canvas.create_rectangle(bar_x1, bar_y, bar_x2, bar_y + 5,
                                     fill=C["border"], outline="")
        self._bar    = self.canvas.create_rectangle(
            bar_x1, bar_y, bar_x1, bar_y + 5,
            fill=C["purple"], outline=""
        )
        self._bar_x1  = bar_x1
        self._bar_x2  = bar_x2
        self._bar_y   = bar_y
        self._bar_step = 0

        self.canvas.create_text(
            W // 2, H - 16, text="v2.0",
            font=FONT_SMALL, fill=C["text_light"], anchor="center"
        )

        # Kick off
        self._drop_letter(0)

    def _drop_letter(self, index):
        if index >= len(self._letter_ids):
            self.after(120, self._show_tagline)
            return

        lid, lx, target_y = self._letter_ids[index]
        steps     = 16
        overshoot = target_y + 10
        bounce_at = steps - 4

        def _step(i=0):
            if i <= bounce_at:
                t = i / bounce_at
                y = -30 + (overshoot + 30) * (t * t)
            else:
                t = (i - bounce_at) / (steps - bounce_at)
                y = overshoot - (overshoot - target_y) * t
            self.canvas.coords(lid, lx, y)
            if i < steps:
                self.after(14, lambda: _step(i + 1))
            else:
                self.canvas.coords(lid, lx, target_y)
                self.after(60, lambda: self._drop_letter(index + 1))

        _step()

    def _show_tagline(self):
        steps = 16

        def _step(i=0):
            if i > steps:
                self._animate_bar()
                return
            t  = i / steps
            # interpolate bg_root (#F7F5FF) → text_mid (#6B6B8A)
            r  = int(0xF7 + (0x6B - 0xF7) * t)
            g  = int(0xF5 + (0x6B - 0xF5) * t)
            b  = int(0xFF + (0x8A - 0xFF) * t)
            self.canvas.itemconfig(self._tag_id, fill=f"#{r:02x}{g:02x}{b:02x}")

            dot_threshold = max(1, steps // len(self._dot_ids))
            dot_idx = min(i // dot_threshold, len(self._dot_ids) - 1)
            for j, (did, dcol) in enumerate(self._dot_ids):
                self.canvas.itemconfig(did,
                    fill=dcol if j <= dot_idx else C["bg_root"])

            self.after(22, lambda: _step(i + 1))

        _step()

    def _animate_bar(self):
        self._bar_step += 1
        frac   = self._bar_step / self.BAR_STEPS
        new_x2 = self._bar_x1 + int((self._bar_x2 - self._bar_x1) * frac)
        self.canvas.coords(self._bar,
                           self._bar_x1, self._bar_y,
                           new_x2,       self._bar_y + 5)
        if self._bar_step < self.BAR_STEPS:
            self.after(10 + int(20 * frac), self._animate_bar)
        else:
            self.after(180, self._finish)

    def _finish(self):
        self.destroy()
        self.on_done()


# ══════════════════════════════════════════════════════════════════════════════
#  Login Screen
# ══════════════════════════════════════════════════════════════════════════════

class LoginScreen:
    """
    Bright JustB-themed login card.
    Matches the system palette exactly: lavender-white bg, white card,
    purple accents, coloured brand letters, Segoe UI typography.
    """

    def __init__(self, root, data_dir):
        self.root     = root
        self.data_dir = data_dir

        for w in self.root.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        self.root.configure(bg=C["bg_root"])

        # ── Soft background decoration ────────────────────────────────────────
        self.bg_canvas = tk.Canvas(self.root, bg=C["bg_root"],
                                   highlightthickness=0)
        self.bg_canvas.place(relwidth=1, relheight=1)
        self.root.update_idletasks()
        self._draw_background()

        # ── Centred wrapper ───────────────────────────────────────────────────
        self.wrapper = tk.Frame(self.root, bg=C["bg_root"])
        self.wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # ── Card ─────────────────────────────────────────────────────────────
        self.card = tk.Frame(
            self.wrapper,
            bg=C["bg_card"],
            padx=48, pady=36,
            highlightbackground=C["border"],
            highlightthickness=1,
        )
        self.card.pack()

        self._build_header()
        self._build_form()
        self._build_footer()

        self._slide_in()

    def _draw_background(self):
        W = self.root.winfo_screenwidth()
        H = self.root.winfo_screenheight()
        cx, cy = W // 2, H // 2

        # Soft lavender blobs
        for r, col in [(420, "#EDEAFF"), (280, "#E8E4F8"), (160, "#DDD8F8")]:
            self.bg_canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                       fill=col, outline="")

        # Dot grid
        for x in range(0, W, 40):
            for y in range(0, H, 40):
                self.bg_canvas.create_oval(x-1, y-1, x+1, y+1,
                                           fill=C["border_acc"], outline="")

        # Soft coloured blobs in the corners
        for bx, by, col in [(0, 0, C["teal"]), (W, 0, C["pink"]),
                             (0, H, C["orange"]), (W, H, C["green"])]:
            r = 120
            self.bg_canvas.create_oval(bx-r, by-r, bx+r, by+r,
                                       fill=col, outline=col)

    def _slide_in(self):
        steps = 20

        def _step(i=0):
            if i > steps:
                return
            t   = i / steps
            eas = 1 - (1 - t) ** 3
            self.wrapper.place_configure(rely=0.57 + (0.5 - 0.57) * eas)
            self.root.after(13, lambda: _step(i + 1))

        _step()

    def _build_header(self):
        hdr = tk.Frame(self.card, bg=C["bg_card"])
        hdr.pack(pady=(0, 26))

        # Coloured brand letters
        letter_row = tk.Frame(hdr, bg=C["bg_card"])
        letter_row.pack()
        for ch, col in zip(BRAND_LETTERS, BRAND_COLORS):
            tk.Label(letter_row, text=ch,
                     font=FONT_BRAND, fg=col, bg=C["bg_card"]).pack(side="left")

        tk.Label(hdr,
                 text="Retail Management System",
                 font=("Segoe UI", 10, "italic"),
                 fg=C["text_light"], bg=C["bg_card"]).pack(pady=(4, 0))

        # Rainbow dot divider
        dot_row = tk.Frame(hdr, bg=C["bg_card"])
        dot_row.pack(pady=(10, 0))
        for col in BRAND_COLORS:
            tk.Label(dot_row, text="●", font=("Segoe UI", 8),
                     fg=col, bg=C["bg_card"]).pack(side="left", padx=2)

    def _build_form(self):
        form = tk.Frame(self.card, bg=C["bg_card"])
        form.pack()

        self.username_entry = self._labeled_entry(form, "USERNAME", row=0)
        self.password_entry = self._labeled_entry(form, "PASSWORD", row=2, secret=True)
        self.password_entry.bind("<Return>", lambda e: self.login())

        self.status_label = tk.Label(
            form, text="", font=FONT_SMALL,
            fg=C["danger"], bg=C["bg_card"], width=32, anchor="w"
        )
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(4, 0))

        self.btn_lbl = tk.Label(
            form, text="SIGN IN", font=FONT_BTN,
            bg=C["purple"], fg="#FFFFFF",
            cursor="hand2", relief="flat",
            padx=0, pady=12, width=28,
        )
        self.btn_lbl.grid(row=5, column=0, columnspan=2,
                          pady=(18, 0), sticky="ew")
        self.btn_lbl.bind("<Button-1>", lambda e: self.login())
        self.btn_lbl.bind("<Enter>",    lambda e: self.btn_lbl.config(bg=C["purple_dk"]))
        self.btn_lbl.bind("<Leave>",    lambda e: self.btn_lbl.config(bg=C["purple"]))

    def _labeled_entry(self, parent, label, row, secret=False):
        tk.Label(parent, text=label,
                 font=FONT_SECTION, fg=C["text_light"], bg=C["bg_card"],
                 anchor="w").grid(row=row, column=0, columnspan=2,
                                  sticky="w", pady=(12, 3))
        entry = tk.Entry(
            parent,
            font=FONT_ENTRY,
            fg=C["text_dark"], bg=C["bg_input"],
            insertbackground=C["purple"],
            relief="flat",
            highlightthickness=2,
            highlightbackground=C["border"],
            highlightcolor=C["purple"],
            show="•" if secret else "",
            width=30,
        )
        entry.grid(row=row + 1, column=0, columnspan=2,
                   sticky="ew", ipady=8)
        return entry

    def _build_footer(self):
        tk.Label(self.card,
                 text="© JustB — Authorized Personnel Only",
                 font=FONT_SMALL, fg=C["text_light"], bg=C["bg_card"]
                 ).pack(pady=(22, 0))

    def _shake(self):
        offsets = [10, -10, 8, -8, 5, -5, 2, -2, 0]
        base_x  = self.root.winfo_width() // 2 - self.card.winfo_width() // 2

        def _step(i=0):
            if i >= len(offsets):
                self.wrapper.place_configure(relx=0.5, x=0)
                return
            self.wrapper.place_configure(relx=0, x=base_x + offsets[i])
            self.root.after(45, lambda: _step(i + 1))

        _step()

    def login(self):
        username   = self.username_entry.get().strip()
        plain_pass = self.password_entry.get().strip()

        if not username or not plain_pass:
            self._show_status("Please enter your credentials.")
            self._shake()
            return

        users_path = os.path.join(self.data_dir, "users.json")
        users      = load_json(users_path)
        user       = next((u for u in users
                           if u.get("username", "").strip() == username), None)

        if not user:
            self._show_status("Invalid username or password.")
            self._shake()
            return

        stored = user.get("password", "")

        if not is_hashed(stored):
            if stored != plain_pass:
                self._show_status("Invalid username or password.")
                self._shake()
                return
            user["password"] = hash_password(plain_pass)
            save_json(users_path, users)
            print(f"[Security] Password for '{username}' upgraded to bcrypt hash.")
        else:
            if not verify_password(stored, plain_pass):
                self._show_status("Invalid username or password.")
                self._shake()
                return

        role = user.get("role", "worker").strip().lower()
        self._launch(role, user)

    def _show_status(self, msg):
        # Cancel any previous pending clear so we don't update a dead widget
        if hasattr(self, "_status_after_id") and self._status_after_id:
            try:
                self.root.after_cancel(self._status_after_id)
            except Exception:
                pass
            self._status_after_id = None

        try:
            self.status_label.config(text=msg)
        except Exception:
            return

        def _clear():
            try:
                self.status_label.config(text="")
            except Exception:
                pass
            self._status_after_id = None

        self._status_after_id = self.root.after(4000, _clear)

    def _launch(self, role, user):
        for w in self.root.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        if role == "admin":
            AdminDashboard(self.root, self.data_dir, user)
        else:
            CashierDashboard(self.root, self.data_dir, user)


# ══════════════════════════════════════════════════════════════════════════════
#  Shared helper: toolbar button
# ══════════════════════════════════════════════════════════════════════════════

def _tb_btn(parent, text, command, bg=C["purple"], hover=C["purple_dk"], fg="#FFFFFF"):
    b = tk.Label(parent, text=text, font=("Segoe UI", 9, "bold"),
                 bg=bg, fg=fg, cursor="hand2",
                 relief="flat", padx=10, pady=5)
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>",    lambda e: b.config(bg=hover))
    b.bind("<Leave>",    lambda e: b.config(bg=bg))
    return b


# ══════════════════════════════════════════════════════════════════════════════
#  Admin Dashboard
# ══════════════════════════════════════════════════════════════════════════════

class AdminDashboard:
    def __init__(self, root, data_dir, user=None):
        self.root       = root
        self.data_dir   = data_dir
        self.user       = user or {"username": "Admin", "role": "admin"}
        self._pos_count = 1   # how many POS tabs exist

        # ── Outer frame holds toolbar + notebook ──────────────────────────────
        outer = tk.Frame(root, bg=C["bg_root"])
        outer.pack(fill="both", expand=True)

        # ── Top toolbar ───────────────────────────────────────────────────────
        toolbar = tk.Frame(outer, bg=C["bg_panel"],
                           highlightthickness=1,
                           highlightbackground=C["border"])
        toolbar.pack(fill="x", side="top")

        tk.Label(toolbar, text="  ➕ POS Stations:",
                 font=("Segoe UI", 9), bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left", padx=(8, 4), pady=6)

        _tb_btn(toolbar, "+ Add POS", self._add_pos_tab,
                bg=C["teal"], hover="#159F9F").pack(side="left", padx=(0, 4), pady=6)

        _tb_btn(toolbar, "✕ Remove POS", self._remove_pos_tab,
                bg=C["danger"], hover="#B91C1C").pack(side="left", padx=(0, 12), pady=6)

        # ── Notebook ──────────────────────────────────────────────────────────
        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        # Fixed first POS tab
        first_pos = POSScreen(root, data_dir=self.data_dir,
                              frame_parent=self.notebook,
                              user=self.user).frame
        self.notebook.add(first_pos, text="POS 1")
        self._pos_frames = [first_pos]

        # Other tabs
        self.product_tab  = ProductManagementScreen(root, data_dir=self.data_dir,
                                                     frame_parent=self.notebook).frame
        self.promo_tab    = PromoManagementScreen(root, data_dir=self.data_dir,
                                                   frame_parent=self.notebook).frame
        self.feedback_tab = DailyFeedbackScreen(root, data_dir=self.data_dir,
                                                 frame_parent=self.notebook,
                                                 admin=True).frame
        self.receipt_tab  = ReceiptDatabaseScreen(root, data_dir=self.data_dir,
                                                   frame_parent=self.notebook,
                                                   admin=True).frame
        self.settings_tab = SettingsScreen(root, data_dir=self.data_dir,
                                            frame_parent=self.notebook,
                                            user=self.user).frame

        self.notebook.add(self.product_tab,  text="Products")
        self.notebook.add(self.promo_tab,    text="Promotions")
        self.notebook.add(self.feedback_tab, text="Feedback")
        self.notebook.add(self.receipt_tab,  text="Receipts")
        self.notebook.add(self.settings_tab, text="Settings")

    def _add_pos_tab(self):
        self._pos_count += 1
        new_pos = POSScreen(self.root, data_dir=self.data_dir,
                            frame_parent=self.notebook,
                            user=self.user).frame
        self._pos_frames.append(new_pos)
        # Insert new POS tab right after the last existing POS tab
        insert_pos = len(self._pos_frames) - 1
        self.notebook.insert(insert_pos, new_pos, text=f"POS {self._pos_count}")
        self.notebook.select(insert_pos)

    def _remove_pos_tab(self):
        if len(self._pos_frames) <= 1:
            messagebox.showinfo("Cannot Remove",
                "At least one POS tab must remain.")
            return
        # Always remove the last POS tab
        last_frame = self._pos_frames.pop()
        # Find its index in the notebook
        for idx in range(self.notebook.index("end")):
            if str(self.notebook.tabs()[idx]) == str(last_frame):
                self.notebook.forget(idx)
                last_frame.destroy()
                break
        self._pos_count -= 1


# ══════════════════════════════════════════════════════════════════════════════
#  Cashier Dashboard
# ══════════════════════════════════════════════════════════════════════════════

class CashierDashboard:
    def __init__(self, root, data_dir, user=None):
        self.root       = root
        self.data_dir   = data_dir
        self.user       = user or {"username": "Cashier", "role": "worker"}
        self._pos_count = 1

        # ── Outer frame ───────────────────────────────────────────────────────
        outer = tk.Frame(root, bg=C["bg_root"])
        outer.pack(fill="both", expand=True)

        # ── Top toolbar ───────────────────────────────────────────────────────
        toolbar = tk.Frame(outer, bg=C["bg_panel"],
                           highlightthickness=1,
                           highlightbackground=C["border"])
        toolbar.pack(fill="x", side="top")

        tk.Label(toolbar, text="  ➕ POS Stations:",
                 font=("Segoe UI", 9), bg=C["bg_panel"],
                 fg=C["text_mid"]).pack(side="left", padx=(8, 4), pady=6)

        _tb_btn(toolbar, "+ Add POS", self._add_pos_tab,
                bg=C["teal"], hover="#159F9F").pack(side="left", padx=(0, 4), pady=6)

        _tb_btn(toolbar, "✕ Remove POS", self._remove_pos_tab,
                bg=C["danger"], hover="#B91C1C").pack(side="left", padx=(0, 12), pady=6)

        # ── Notebook ──────────────────────────────────────────────────────────
        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        first_pos = POSScreen(root, data_dir=self.data_dir,
                              frame_parent=self.notebook,
                              user=self.user).frame
        self.notebook.add(first_pos, text="POS 1")
        self._pos_frames = [first_pos]

        self.product_tab = ProductManagementScreen(root, data_dir=self.data_dir,
                                                    frame_parent=self.notebook,
                                                    cashier_mode=True).frame
        self.receipt_tab = ReceiptDatabaseScreen(root, data_dir=self.data_dir,
                                                  frame_parent=self.notebook,
                                                  admin=False).frame

        self.notebook.add(self.product_tab, text="Products")
        self.notebook.add(self.receipt_tab, text="Receipts")

    def _add_pos_tab(self):
        self._pos_count += 1
        new_pos = POSScreen(self.root, data_dir=self.data_dir,
                            frame_parent=self.notebook,
                            user=self.user).frame
        self._pos_frames.append(new_pos)
        insert_pos = len(self._pos_frames) - 1
        self.notebook.insert(insert_pos, new_pos, text=f"POS {self._pos_count}")
        self.notebook.select(insert_pos)

    def _remove_pos_tab(self):
        if len(self._pos_frames) <= 1:
            messagebox.showinfo("Cannot Remove",
                "At least one POS tab must remain.")
            return
        last_frame = self._pos_frames.pop()
        for idx in range(self.notebook.index("end")):
            if str(self.notebook.tabs()[idx]) == str(last_frame):
                self.notebook.forget(idx)
                last_frame.destroy()
                break
        self._pos_count -= 1