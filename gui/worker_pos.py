# gui/worker_pos.py
import tkinter as tk
from tkinter import messagebox

class WorkerPOS(tk.Toplevel):
    def __init__(self, master, user_data):
        super().__init__(master)
        self.master = master
        self.user_data = user_data
        self.title(f"Worker POS - Welcome, {user_data['username']}")
        self.geometry("1024x768")
        self.master.withdraw() # Hide the main window if it's the root Tk() instance

        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="Point of Sale System (Worker Access)", font=("Arial", 20, "bold")).pack(pady=50)
        tk.Label(self, text="This will be the dedicated POS interface for cashiers.", font=("Arial", 12)).pack(pady=20)
        # TODO: Implement the actual POS interface here.

    def on_closing(self):
        if messagebox.askokcancel("Logout", "Are you sure you want to log out?"):
            self.destroy() # Close POS window
            self.master.deiconify() # Show main window (which will be the login window if root is Tk)