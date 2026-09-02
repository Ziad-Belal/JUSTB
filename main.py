

import tkinter as tk
from gui.login_screen import LoginScreen
from gui.splash_screen import SplashScreen
from gui.theme import Palette
from utils.helpers import load_json
import os

DATA_DIR = r"C:\Users\Ziad\JUSTB\gui\data"

def main():
    settings = load_json(os.path.join(DATA_DIR, "system_settings.json"))
    Palette.set_dark(bool(settings.get("dark_mode", False)) if isinstance(settings, dict) else False)
    root = tk.Tk()
    root.title("JustB — Retail Management System")
    root.geometry("1024x700")
    root.minsize(800, 560)
    root.configure(bg=Palette.bg_root)

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