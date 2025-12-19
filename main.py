import tkinter as tk
from gui.login_screen import LoginScreen
import os

# Client PC data folder path
DATA_DIR = r"C:\Users\A\Desktop\JustB\data"


# Initialize root window
root = tk.Tk()
root.title("SMGS")

# Set window icon
icon_path = r"C:\Users\Ziad\OneDrive\Documents\SMGS\WhatsApp Image 2025-12-16 at 12.28.37 AM.ico"
if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Could not load icon: {e}")
else:
    print(f"Icon file not found at: {icon_path}")

# Launch login screen with forced data path
LoginScreen(root, DATA_DIR)

# Start GUI loop
root.mainloop()

#r"C:\Users\20102\Desktop\JustB\data" this is the original path I will use when the project runs after the testing.