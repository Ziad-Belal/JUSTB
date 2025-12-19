# gui/admin_dashboard.py
import tkinter as tk
from tkinter import ttk, messagebox


class AdminDashboard(tk.Toplevel):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.master = master
        self.user_data = user_data
        self.title(f"Admin Dashboard - Welcome, {user_data['username']}")
        self.geometry("1024x768")
        self.master.withdraw() # Hide the main window if it's the root Tk() instance

        self.create_widgets()

    def create_widgets(self):
        # Create a Notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # Tabs for Admin
        self.pos_frame = tk.Frame(self.notebook)
        self.product_frame = tk.Frame(self.notebook)
        self.promotion_frame = tk.Frame(self.notebook)
        self.feedback_frame = tk.Frame(self.notebook)

        self.notebook.add(self.pos_frame, text="Point of Sale")
        self.notebook.add(self.product_frame, text="Product Management")
        self.notebook.add(self.promotion_frame, text="Promotion Management")
        self.notebook.add(self.feedback_frame, text="Daily Feedback")

        # --- Placeholder content for each tab ---
        tk.Label(self.pos_frame, text="POS System (Admin Access)", font=("Arial", 16)).pack(pady=50)
        tk.Label(self.product_frame, text="Product Management (CRUD)", font=("Arial", 16)).pack(pady=50)
        tk.Label(self.promotion_frame, text="Promotion Management", font=("Arial", 16)).pack(pady=50)
        tk.Label(self.feedback_frame, text="Daily Sales Feedback", font=("Arial", 16)).pack(pady=50)

        # TODO: Implement actual panel content for each tab
        # We will create specific panel classes for each feature later.

    def on_closing(self):
        if messagebox.askokcancel("Logout", "Are you sure you want to log out?"):
            self.destroy() # Close dashboard
            self.master.deiconify() # Show main window (which will be the login window if root is Tk)