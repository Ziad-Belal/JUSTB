import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.helpers import load_json, save_json
import qrcode
import os

class PromoManagementScreen:
    def __init__(self, root, frame_parent=None, data_dir=None):
        self.root = root
        self.data_dir = data_dir
        self.frame = tk.Frame(frame_parent or root, padx=10, pady=10)
        self.frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(self.frame, columns=("Code", "Discount", "Uses Left"), show="headings")
        for col in ("Code", "Discount", "Uses Left"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.grid(row=0, column=0, rowspan=5, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.load_selected)

        tk.Label(self.frame, text="Code").grid(row=0, column=1, sticky="e")
        tk.Label(self.frame, text="Discount %").grid(row=1, column=1, sticky="e")
        tk.Label(self.frame, text="Max Uses").grid(row=2, column=1, sticky="e")

        self.code_entry = tk.Entry(self.frame)
        self.discount_entry = tk.Entry(self.frame)
        self.max_entry = tk.Entry(self.frame)

        self.code_entry.grid(row=0, column=2)
        self.discount_entry.grid(row=1, column=2)
        self.max_entry.grid(row=2, column=2)

        tk.Button(self.frame, text="Add New Code", command=self.add_code).grid(row=3, column=1, pady=5)
        tk.Button(self.frame, text="Delete Selected Code", command=self.delete_code).grid(row=3, column=2, pady=5)
        tk.Button(self.frame, text="Generate QR Code", command=self.generate_qr).grid(row=4, column=1, columnspan=2, pady=5)

        self.load_codes()

    def load_codes(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        promos = load_json(os.path.join(self.data_dir, "promo_codes.json"))
        for promo in promos:
            self.tree.insert("", "end", values=(promo["code"], promo["discount_percentage"], promo["uses_left"]))

    def load_selected(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])["values"]
            self.code_entry.delete(0, tk.END)
            self.code_entry.insert(0, values[0])
            self.discount_entry.delete(0, tk.END)
            self.discount_entry.insert(0, values[1])
            self.max_entry.delete(0, tk.END)
            self.max_entry.insert(0, values[2])

    def add_code(self):
        code = self.code_entry.get().strip()
        discount = float(self.discount_entry.get().strip())
        max_uses = int(self.max_entry.get().strip())
        if not all([code, discount, max_uses]):
            messagebox.showerror("Error", "All fields required")
            return
        promos = load_json(os.path.join(self.data_dir, "promo_codes.json"))
        promos.append({"code": code, "discount_percentage": discount, "max_uses": max_uses, "uses_left": max_uses})
        save_json(os.path.join(self.data_dir, "promo_codes.json"), promos)
        messagebox.showinfo("Success", "Promo code added")
        self.load_codes()

    def delete_code(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a code first")
            return
        code = self.tree.item(selected[0])["values"][0]
        promos = load_json(os.path.join(self.data_dir, "promo_codes.json"))
        promos = [p for p in promos if p["code"] != code]
        save_json(os.path.join(self.data_dir, "promo_codes.json"), promos)
        messagebox.showinfo("Success", "Promo code deleted")
        self.load_codes()

    def generate_qr(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select a code first")
            return
        code = self.tree.item(selected[0])["values"][0]

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png")],
            title="Save QR Code As",
            initialfile=f"{code}_qr.png"
        )
        if not file_path:
            return

        qr_img = qrcode.make(code)
        qr_img.save(file_path)
        messagebox.showinfo("Success", f"QR Code saved at:\n{file_path}")
