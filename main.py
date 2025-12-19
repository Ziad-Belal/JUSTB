import tkinter as tk
from gui.login_screen import LoginScreen

# Client PC data folder path
#DATA_DIR = r"C:\Users\A\Desktop\JustB\data"
DATA_DIR = r"C:\Users\Ziad\OneDrive\Documents\SMGS\gui\data"
# Initialize root window
root = tk.Tk()
root.title("SMGS")

# Launch login screen with forced data path
LoginScreen(root, DATA_DIR)
# Start GUI loop
root.mainloop()
#r"C:\Users\20102\Desktop\JustB\data" this is the original path I will use when the project runs after the testing.
