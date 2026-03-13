import tkinter as tk
from tkinter import messagebox
from gui.pos_screen import POSScreen
from gui.product_management import ProductManagementScreen
from gui.promo_management import PromoManagementScreen
from gui.daily_feedback import DailyFeedbackScreen
from gui.receipt_database import ReceiptDatabaseScreen
from utils.helpers import load_json
import os

class LoginScreen:
    def __init__(self, root, data_dir):
        self.root = root
        self.data_dir = data_dir

        # Clear any existing widgets (supports switch-user re-launch)
        for widget in self.root.winfo_children():
            try:
                widget.destroy()
            except Exception:
                pass

        self.frame = tk.Frame(root, padx=30, pady=30)
        self.frame.pack(expand=True)

        tk.Label(self.frame, text="Username:", font=("Helvetica", 14)).grid(row=0, column=0, sticky="e", pady=5)
        tk.Label(self.frame, text="Password:", font=("Helvetica", 14)).grid(row=1, column=0, sticky="e", pady=5)

        self.username_entry = tk.Entry(self.frame, font=("Helvetica", 14))
        self.password_entry = tk.Entry(self.frame, font=("Helvetica", 14), show="*")
        self.username_entry.grid(row=0, column=1, pady=5)
        self.password_entry.grid(row=1, column=1, pady=5)

        self.username_entry.focus()
        self.password_entry.bind("<Return>", lambda e: self.login())

        tk.Button(self.frame, text="Login", font=("Helvetica", 14, "bold"),
                  bg="green", fg="white",
                  command=self.login).grid(row=2, column=0, columnspan=2,
                                           pady=15, ipadx=20)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        users_path = os.path.join(self.data_dir, "users.json")
        users = load_json(users_path)

        user = next((u for u in users
                     if u.get("username", "").strip() == username
                     and u.get("password", "").strip() == password), None)

        if user:
            messagebox.showinfo("Success", f"Logged in as {user.get('role', 'User')}")
            try:
                self.frame.destroy()
            except Exception:
                pass

            role = user.get("role", "User").strip().lower()
            if role == "admin":
                AdminDashboard(self.root, self.data_dir, user)
            else:
                POSScreen(self.root, self.data_dir, user=user)
        else:
            messagebox.showerror("Error", "Invalid username or password")


class AdminDashboard:
    def __init__(self, root, data_dir, user=None):
        import tkinter.ttk as ttk
        self.root = root
        self.data_dir = data_dir
        self.user = user or {"username": "Admin", "role": "admin"}

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self.pos_tab      = POSScreen(root, data_dir=self.data_dir,
                                       frame_parent=self.notebook,
                                       user=self.user).frame
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

        self.notebook.add(self.pos_tab,      text="POS")
        self.notebook.add(self.product_tab,  text="Products")
        self.notebook.add(self.promo_tab,    text="Promotions")
        self.notebook.add(self.feedback_tab, text="Daily Feedback")
        self.notebook.add(self.receipt_tab,  text="📋 Receipts")