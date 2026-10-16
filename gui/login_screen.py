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
from gui.theme import (
    C,
    Font,
    BRAND_COLORS,
    BRAND_LETTERS,
    make_rounded_button,
    make_pill,
)
from gui.widgets import (
    RoundedCard,
    BrandWordmark,
    FocusRing,
    Pill,
)
from gui.animation import Animator, Easing
import os
import traceback

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


# Back-compat aliases so the old FONT_* names used by AdminDashboard /
# CashierDashboard continue to work.
FONT_BRAND   = Font.BRAND
FONT_HEAD    = Font.HEAD
FONT_LABEL_B = Font.LABEL_B
FONT_LABEL   = Font.LABEL
FONT_ENTRY   = Font.ENTRY
FONT_BTN     = Font.BTN
FONT_SMALL   = Font.SMALL
FONT_SECTION = Font.SECTION
FONT_BTN_LG  = Font.BTN_LG
FONT_TOTAL   = Font.TOTAL

# ══════════════════════════════════════════════════════════════════════════════
#  Login Screen
# ══════════════════════════════════════════════════════════════════════════════

class LoginScreen:
    """
    Minimal JustB login card using the shared premium visual language.
    """

    def __init__(self, root, data_dir):
        self.root     = root
        self.data_dir = data_dir
        self._install_text_shortcuts()

        for w in self.root.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        self.root.configure(bg=C["bg_root"])

        # ── Quiet background surface ─────────────────────────────────────────
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
            padx=52, pady=42,
            highlightbackground=C["border"],
            highlightthickness=1,
        )
        self.card.pack()

        self._build_header()
        self._build_form()
        self._build_footer()

        self._slide_in()

    def _install_text_shortcuts(self):
        if getattr(self.root, "_justb_text_shortcuts_installed", False):
            return

        def select_all_widget(widget):
            if isinstance(widget, tk.Text):
                widget.tag_add(tk.SEL, "1.0", "end-1c")
                widget.mark_set(tk.INSERT, "1.0")
            else:
                widget.selection_range(0, tk.END)
                widget.icursor(tk.END)

        def select_all(event):
            select_all_widget(event.widget)
            return "break"

        def show_context_menu(event):
            widget = event.widget
            context_menu = getattr(widget, "_justb_text_context_menu", None)
            if context_menu is None:
                context_menu = tk.Menu(widget, tearoff=False)
                context_menu.add_command(
                    label="Cut",
                    command=lambda w=widget: w.event_generate("<<Cut>>"))
                context_menu.add_command(
                    label="Copy",
                    command=lambda w=widget: w.event_generate("<<Copy>>"))
                context_menu.add_command(
                    label="Paste",
                    command=lambda w=widget: w.event_generate("<<Paste>>"))
                context_menu.add_separator()
                context_menu.add_command(
                    label="Select All",
                    command=lambda w=widget: select_all_widget(w))
                widget._justb_text_context_menu = context_menu

            try:
                state = str(widget.cget("state"))
            except tk.TclError:
                state = "normal"

            editable = state not in ("disabled", "readonly")
            try:
                has_selection = (
                    bool(widget.tag_ranges(tk.SEL))
                    if isinstance(widget, tk.Text)
                    else bool(widget.selection_present()))
            except tk.TclError:
                has_selection = False

            context_menu.entryconfigure(
                "Cut", state="normal" if editable and has_selection else "disabled")
            context_menu.entryconfigure(
                "Copy", state="normal" if has_selection else "disabled")
            context_menu.entryconfigure(
                "Paste", state="normal" if editable else "disabled")
            context_menu.tk_popup(event.x_root, event.y_root)
            return "break"

        for widget_class in ("Entry", "Text", "TEntry", "TCombobox",
                             "Spinbox", "TSpinbox"):
            self.root.bind_class(widget_class, "<Control-a>", select_all)
            self.root.bind_class(widget_class, "<Control-A>", select_all)
            self.root.bind_class(
                widget_class, "<Button-3>", show_context_menu, add="+")
        self.root._justb_text_shortcuts_installed = True

    def _draw_background(self):
        return
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
        hdr.pack(pady=(0, 30))

        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "logo.png")
        if Image is not None and ImageTk is not None and os.path.exists(logo_path):
            logo_source = Image.open(logo_path).convert("RGBA")
            logo_image = ImageTk.PhotoImage(
                logo_source.resize((260, 173), Image.Resampling.LANCZOS))
            self._logo_image = logo_image
            tk.Label(hdr, image=logo_image, bg=C["bg_card"]).pack()
        else:
            tk.Label(hdr, text="JustB", font=("Georgia", 32, "bold"),
                     fg=C["text_dark"], bg=C["bg_card"]).pack()
            tk.Frame(hdr, bg=C["pink"], height=2, width=60).pack(pady=(12, 0))

        tk.Label(hdr,
                 text="RETAIL MANAGEMENT SYSTEM",
                 font=FONT_SMALL,
                 fg=C["text_light"], bg=C["bg_card"]).pack(pady=(4, 0))

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


_TAB_IMAGES = []     # keep references so Tk does not garbage-collect the images


def _make_tab_images():
    """Draw rounded-top tab backgrounds (normal / hover / selected) with Pillow."""
    from PIL import Image, ImageDraw, ImageTk
    S, W, H, GAP, R = 4, 48, 40, 2, 10      # supersample, size, side gap, radius

    def build(fill, outline, accent=None):
        big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        box = [GAP * S, 0, (W - GAP) * S - 1, H * S + R * S]   # bottom corners cut off
        d.rounded_rectangle(box, radius=R * S, fill=outline)
        inner = [box[0] + S, S, box[2] - S, box[3]]
        d.rounded_rectangle(inner, radius=(R - 1) * S, fill=fill)
        if accent:
            bar = Image.new("RGBA", big.size, (0, 0, 0, 0))
            ImageDraw.Draw(bar).rounded_rectangle(box, radius=R * S, fill=accent)
            mask = Image.new("L", big.size, 0)
            ImageDraw.Draw(mask).rectangle([0, 0, W * S, 3 * S], fill=255)
            bar.putalpha(Image.composite(bar.getchannel("A"), Image.new("L", big.size, 0), mask))
            big = Image.alpha_composite(big, bar)
        return ImageTk.PhotoImage(big.resize((W, H), Image.LANCZOS))

    return (build(C["bg_panel"], C["border"]),
            build("#E9E2FF", C["border_acc"]),
            build(C["bg_card"], C["border_acc"], accent=C["purple"]))


def _configure_shell_styles():
    style = ttk.Style()
    # Set the theme ONCE, before any style is configured. Styles are stored
    # per-theme, so switching theme later (the POS screen used to do this every
    # time a POS tab was created) wipes the tab styling and makes tabs glitch.
    if style.theme_use() != "clam":
        style.theme_use("clam")
    style.configure(
        "JustB.TNotebook",
        background=C["bg_root"],
        bordercolor=C["bg_root"], lightcolor=C["bg_root"], darkcolor=C["bg_root"],
        borderwidth=0,
        tabmargins=(12, 8, 12, 0),
    )
    style.configure(
        "JustB.TNotebook.Tab",
        background=C["bg_panel"],
        foreground=C["text_mid"],
        font=("Segoe UI", 10, "bold"),
        padding=(16, 8),
        borderwidth=0,
    )
    style.map(
        "JustB.TNotebook.Tab",
        background=[("selected", C["bg_card"]), ("active", C["bg_hover"])],
        foreground=[("selected", C["purple"]), ("active", C["text_dark"])],
        expand=[("selected", (0, 0, 0, 0))],
    )

    # Rounded tab shapes. Falls back to the flat style above if Pillow is missing.
    try:
        if not _TAB_IMAGES:
            _TAB_IMAGES.extend(_make_tab_images())
        normal, hover, selected = _TAB_IMAGES
        try:
            style.element_create(
                "JB.tab", "image", normal,
                ("selected", selected), ("active", hover),
                border=(14, 12, 14, 2), sticky="nsew")
        except tk.TclError:
            pass   # element already exists (dashboard re-opened after logout)
        style.layout("JustB.TNotebook.Tab", [
            ("JB.tab", {"sticky": "nswe", "children": [
                ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                    ("Notebook.label", {"side": "top", "sticky": ""})]})]})])
    except Exception as exc:
        print(f"[theme] rounded tabs unavailable, using flat tabs: {exc}")


def _build_app_shell(outer, user, add_pos, remove_pos):
    toolbar = tk.Frame(outer, bg=C["bg_card"],
                       highlightthickness=1,
                       highlightbackground=C["border"])
    toolbar.pack(fill="x", side="top")

    brand = tk.Frame(toolbar, bg=C["bg_card"])
    brand.pack(side="left", padx=(18, 24), pady=8)
    tk.Label(brand, text="JUSTB", font=("Georgia", 15, "bold"),
             bg=C["bg_card"], fg=C["text_dark"]).pack(anchor="w")
    tk.Label(brand, text="RETAIL OPERATIONS", font=("Segoe UI", 7, "bold"),
             bg=C["bg_card"], fg=C["text_light"]).pack(anchor="w")

    tk.Frame(toolbar, bg=C["border"], width=1, height=34).pack(
        side="left", pady=7)
    tk.Label(toolbar, text="POS STATIONS", font=("Segoe UI", 8, "bold"),
             bg=C["bg_card"], fg=C["text_mid"]).pack(
                 side="left", padx=(18, 8), pady=6)
    _tb_btn(toolbar, "+ Add POS", add_pos,
            bg=C["teal"], hover="#159F9F").pack(side="left", padx=(0, 4), pady=6)
    _tb_btn(toolbar, "Remove POS", remove_pos,
            bg=C["bg_panel"], hover=C["border_acc"],
            fg=C["text_mid"]).pack(side="left", padx=(0, 12), pady=6)

    identity = tk.Frame(toolbar, bg=C["bg_card"])
    identity.pack(side="right", padx=18, pady=7)
    username = user.get("username", "User")
    role = user.get("role", "worker").strip().upper()
    tk.Label(identity, text=username, font=("Segoe UI", 9, "bold"),
             bg=C["bg_card"], fg=C["text_dark"]).pack(anchor="e")
    tk.Label(identity, text=f"{role} SESSION", font=("Segoe UI", 8),
             bg=C["bg_card"], fg=C["text_light"]).pack(anchor="e")

    return ttk.Notebook(outer, style="JustB.TNotebook")


# ══════════════════════════════════════════════════════════════════════════════
#  Admin Dashboard
# ══════════════════════════════════════════════════════════════════════════════

class AdminDashboard:
    def __init__(self, root, data_dir, user=None):
        self.root       = root
        self.data_dir   = data_dir
        self.user       = user or {"username": "Admin", "role": "admin"}
        self._pos_count = 1   # how many POS tabs exist
        _configure_shell_styles()

        # ── Outer frame holds toolbar + notebook ──────────────────────────────
        outer = tk.Frame(root, bg=C["bg_root"])
        outer.pack(fill="both", expand=True)

        self.notebook = _build_app_shell(
            outer, self.user, self._add_pos_tab, self._remove_pos_tab)
        self.notebook.pack(fill="both", expand=True)

        # Register each tab immediately. A data problem in one screen must not
        # prevent the remaining admin tabs from appearing.
        self._pos_frames = []
        first_pos = self._create_admin_tab(
            "POS 1",
            lambda: POSScreen(root, data_dir=self.data_dir,
                              frame_parent=self.notebook,
                              user=self.user).frame)
        self._pos_frames.append(first_pos)

        self.product_tab = self._create_admin_tab(
            "Products",
            lambda: ProductManagementScreen(
                root, data_dir=self.data_dir,
                frame_parent=self.notebook).frame)
        self.promo_tab = self._create_admin_tab(
            "Promotions",
            lambda: PromoManagementScreen(
                root, data_dir=self.data_dir,
                frame_parent=self.notebook).frame)
        self.feedback_tab = self._create_admin_tab(
            "Feedback",
            lambda: DailyFeedbackScreen(
                root, data_dir=self.data_dir,
                frame_parent=self.notebook, admin=True).frame)
        self.receipt_tab = self._create_admin_tab(
            "Receipts",
            lambda: ReceiptDatabaseScreen(
                root, data_dir=self.data_dir,
                frame_parent=self.notebook, admin=True).frame)
        self.settings_tab = self._create_admin_tab(
            "Settings",
            lambda: SettingsScreen(
                root, data_dir=self.data_dir,
                frame_parent=self.notebook, user=self.user).frame)

    def _create_admin_tab(self, title, factory):
        """Create and register one tab even if its screen has an init error."""
        try:
            frame = factory()
        except Exception as error:
            traceback.print_exc()
            frame = tk.Frame(self.notebook, bg=C["bg_root"])
            tk.Label(
                frame,
                text=f"{title} could not be loaded.\n{error}",
                font=FONT_LABEL,
                bg=C["bg_root"],
                fg=C["danger"],
                justify="center",
            ).pack(expand=True)
        self.notebook.add(frame, text=title)
        return frame

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
        _configure_shell_styles()

        # ── Outer frame ───────────────────────────────────────────────────────
        outer = tk.Frame(root, bg=C["bg_root"])
        outer.pack(fill="both", expand=True)

        self.notebook = _build_app_shell(
            outer, self.user, self._add_pos_tab, self._remove_pos_tab)
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