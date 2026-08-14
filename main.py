

import tkinter as tk
from gui.login_screen import LoginScreen
from gui.splash_screen import SplashScreen
import os

DATA_DIR = r"C:\Users\A\OneDrive\Desktop"

def main():
    root = tk.Tk()
    root.title("JustB — Retail Management System")
    root.geometry("1024x700")
    root.minsize(800, 560)
    root.configure(bg="#F7F5FF")

    # Centre window on screen
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"1024x700+{(sw-1024)//2}+{(sh-700)//2}")

    # Hide main window during splash, then show login
    root.withdraw()

    def launch_login():
        root.deiconify()
        LoginScreen(root, DATA_DIR)

    SplashScreen(root, on_done=launch_login)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Allow clean exit when user interrupts via Ctrl+C in terminal
        print("Interrupted by user. Exiting...")