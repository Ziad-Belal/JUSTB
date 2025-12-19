import tkinter as tk
from tkinter import ttk, messagebox
from utils.helpers import load_json, save_json
import os
import tempfile
import subprocess

# Try to import win32api for printing
try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

class ProductManagementScreen:
    def __init__(self, root, data_dir, frame_parent=None):
        self.root = root
        self.data_dir = data_dir
        self.frame = tk.Frame(frame_parent or root, padx=10, pady=10)
        self.frame.pack(fill="both", expand=True)

        # Search bar section
        search_frame = tk.Frame(self.frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Search:", font=("Helvetica", 11, "bold")).pack(side="left", padx=(0, 5))
        
        self.search_entry = tk.Entry(search_frame, font=("Helvetica", 11), width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.search_products())
        
        tk.Button(search_frame, text="Clear", command=self.clear_search, bg="gray", fg="white").pack(side="left", padx=5)
        
        # Search filter dropdown
        tk.Label(search_frame, text="Search by:", font=("Helvetica", 10)).pack(side="left", padx=(15, 5))
        self.search_filter = ttk.Combobox(search_frame, values=["All", "Barcode", "Name", "Price", "Quantity"], 
                                          state="readonly", width=12)
        self.search_filter.set("All")
        self.search_filter.pack(side="left")
        self.search_filter.bind("<<ComboboxSelected>>", lambda e: self.search_products())

        # Table with vertical scrollbar
        tree_frame = tk.Frame(self.frame)
        tree_frame.pack(fill="both", expand=True, pady=(0,8))

        self.tree = ttk.Treeview(tree_frame, columns=("Barcode","Name","Price","Qty"), show="headings", selectmode="extended")
        for col in ("Barcode","Name","Price","Qty"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=140)
        self.tree.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")

        # Results label
        self.results_label = tk.Label(self.frame, text="", font=("Helvetica", 9), fg="gray")
        self.results_label.pack(anchor="w", pady=(0, 5))

        # Buttons
        btns = tk.Frame(self.frame)
        btns.pack(anchor="w")
        tk.Button(btns, text="Add Product", command=self.add_product_popup, bg="green", fg="white").pack(side="left", padx=5, pady=5)
        tk.Button(btns, text="Edit Product", command=self.edit_product_popup, bg="orange", fg="white").pack(side="left", padx=5, pady=5)
        tk.Button(btns, text="Delete Product", command=self.delete_product, bg="red", fg="white").pack(side="left", padx=5, pady=5)
        tk.Button(btns, text="Print Product", command=self.print_product, bg="blue", fg="white").pack(side="left", padx=5, pady=5)
        tk.Button(btns, text="Refresh", command=self.load_products).pack(side="left", padx=5, pady=5)

        self.all_products = []  # Store all products for filtering
        self.load_products()

    def _products_path(self):
        return os.path.join(self.data_dir, "products.json")

    def load_products(self):
        """Load all products from JSON file"""
        self.all_products = load_json(self._products_path())
        self.display_products(self.all_products)

    def display_products(self, products):
        """Display products in the treeview"""
        # Clear table
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        # Add products to table
        for p in products:
            self.tree.insert("", "end", values=(p["barcode"], p["name"], p["price"], p.get("quantity", 0)))
        
        # Update results label
        total = len(self.all_products)
        shown = len(products)
        if shown == total:
            self.results_label.config(text=f"Showing all {total} product(s)")
        else:
            self.results_label.config(text=f"Showing {shown} of {total} product(s)")

    def search_products(self):
        """Filter products based on search query"""
        query = self.search_entry.get().strip().lower()
        filter_by = self.search_filter.get()
        
        if not query:
            self.display_products(self.all_products)
            return
        
        filtered = []
        
        for product in self.all_products:
            barcode = str(product.get("barcode", "")).lower()
            name = str(product.get("name", "")).lower()
            price = str(product.get("price", "")).lower()
            qty = str(product.get("quantity", 0)).lower()
            
            # Check based on filter selection
            if filter_by == "All":
                if query in barcode or query in name or query in price or query in qty:
                    filtered.append(product)
            elif filter_by == "Barcode":
                if query in barcode:
                    filtered.append(product)
            elif filter_by == "Name":
                if query in name:
                    filtered.append(product)
            elif filter_by == "Price":
                if query in price:
                    filtered.append(product)
            elif filter_by == "Quantity":
                if query in qty:
                    filtered.append(product)
        
        self.display_products(filtered)

    def clear_search(self):
        """Clear search and show all products"""
        self.search_entry.delete(0, tk.END)
        self.search_filter.set("All")
        self.display_products(self.all_products)

    def add_product_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Product")
        popup.resizable(False, False)

        tk.Label(popup, text="Barcode:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        barcode_entry = tk.Entry(popup)
        barcode_entry.grid(row=0, column=1, padx=6, pady=6)
        barcode_entry.focus()

        tk.Label(popup, text="Name:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        name_entry = tk.Entry(popup)
        name_entry.grid(row=1, column=1, padx=6, pady=6)

        tk.Label(popup, text="Price:").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        price_entry = tk.Entry(popup)
        price_entry.grid(row=2, column=1, padx=6, pady=6)

        tk.Label(popup, text="Quantity:").grid(row=3, column=0, sticky="e", padx=6, pady=6)
        qty_entry = tk.Entry(popup)
        qty_entry.grid(row=3, column=1, padx=6, pady=6)

        def save_product():
            barcode = barcode_entry.get().strip()
            name = name_entry.get().strip()
            price_raw = price_entry.get().strip()
            qty_raw = qty_entry.get().strip()

            if not barcode:
                messagebox.showerror("Error", "Barcode is required")
                return
            if not name:
                messagebox.showerror("Error", "Name is required")
                return
            try:
                price = float(price_raw)
                if price < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Price must be a non-negative number")
                return
            try:
                qty = int(qty_raw)
                if qty < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Quantity must be a non-negative integer")
                return

            products_path = self._products_path()
            products = load_json(products_path)

            # Check if barcode already exists
            existing = next((p for p in products if p["barcode"] == barcode), None)
            if existing:
                messagebox.showerror("Error", "Product with this barcode already exists! Use Edit to modify it.")
                return

            # Add new product
            products.append({
                "barcode": barcode,
                "name": name,
                "price": price,
                "quantity": qty
            })

            save_json(products_path, products)
            messagebox.showinfo("Success", "Product added successfully")
            popup.destroy()
            self.load_products()

        tk.Button(popup, text="Save", command=save_product, bg="green", fg="white").grid(row=4, column=0, columnspan=2, pady=10)

    def edit_product_popup(self):
        # Check if a product is selected
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Please select a product to edit")
            return
        
        if len(selected) > 1:
            messagebox.showinfo("Info", "Please select only one product to edit")
            return

        # Get current product data
        current_values = self.tree.item(selected[0])["values"]
        old_barcode = str(current_values[0])
        old_name = current_values[1]
        old_price = current_values[2]
        old_qty = current_values[3]

        # Create popup
        popup = tk.Toplevel(self.root)
        popup.title("Edit Product")
        popup.resizable(False, False)

        tk.Label(popup, text="Barcode:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        barcode_entry = tk.Entry(popup)
        barcode_entry.insert(0, old_barcode)
        barcode_entry.grid(row=0, column=1, padx=6, pady=6)

        tk.Label(popup, text="Name:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        name_entry = tk.Entry(popup)
        name_entry.insert(0, old_name)
        name_entry.grid(row=1, column=1, padx=6, pady=6)

        tk.Label(popup, text="Price:").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        price_entry = tk.Entry(popup)
        price_entry.insert(0, old_price)
        price_entry.grid(row=2, column=1, padx=6, pady=6)

        tk.Label(popup, text="Quantity:").grid(row=3, column=0, sticky="e", padx=6, pady=6)
        qty_entry = tk.Entry(popup)
        qty_entry.insert(0, old_qty)
        qty_entry.grid(row=3, column=1, padx=6, pady=6)

        def update_product():
            new_barcode = barcode_entry.get().strip()
            new_name = name_entry.get().strip()
            price_raw = price_entry.get().strip()
            qty_raw = qty_entry.get().strip()

            if not new_barcode:
                messagebox.showerror("Error", "Barcode is required")
                return
            if not new_name:
                messagebox.showerror("Error", "Name is required")
                return
            try:
                new_price = float(price_raw)
                if new_price < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Price must be a non-negative number")
                return
            try:
                new_qty = int(qty_raw)
                if new_qty < 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "Quantity must be a non-negative integer")
                return

            products_path = self._products_path()
            products = load_json(products_path)

            # Check if new barcode conflicts with another product
            if new_barcode != old_barcode:
                conflict = next((p for p in products if p["barcode"] == new_barcode), None)
                if conflict:
                    messagebox.showerror("Error", "Another product already has this barcode!")
                    return

            # Find and update the product
            for p in products:
                if p["barcode"] == old_barcode:
                    p["barcode"] = new_barcode
                    p["name"] = new_name
                    p["price"] = new_price
                    p["quantity"] = new_qty
                    break

            save_json(products_path, products)
            messagebox.showinfo("Success", "Product updated successfully")
            popup.destroy()
            self.load_products()

        tk.Button(popup, text="Update", command=update_product, bg="orange", fg="white").grid(row=4, column=0, columnspan=2, pady=10)

    def delete_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a product to delete")
            return

        if not messagebox.askyesno("Confirm", "Delete selected product(s)?"):
            return

        products_path = self._products_path()
        products = load_json(products_path)

        # Collect barcodes to remove
        barcodes_to_remove = set()
        for sel in selected:
            vals = self.tree.item(sel)["values"]
            if vals:
                barcodes_to_remove.add(str(vals[0]))

        # Filter products
        new_products = [p for p in products if str(p.get("barcode", "")) not in barcodes_to_remove]
        save_json(products_path, new_products)

        self.load_products()
        messagebox.showinfo("Success", "Product(s) deleted")

    def print_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a product to print")
            return

        try:
            for sel in selected:
                vals = self.tree.item(sel)["values"]
                if not vals:
                    continue
                text = (
                    f"Product\n"
                    f"-------\n"
                    f"Name: {vals[1]}\n"
                    f"Barcode: {vals[0]}\n"
                    f"Price: {vals[2]}\n"
                    f"Quantity: {vals[3]}\n"
                )

                # Temp file
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8')
                temp.write(text)
                temp.close()
                
                if WIN32_AVAILABLE:
                    # Send directly to printer using win32api
                    win32api.ShellExecute(0, "print", temp.name, None, ".", 0)
                    messagebox.showinfo("Printed", "Product info sent to printer.")
                else:
                    # Fallback: try to print using Notepad (silent print on Windows)
                    try:
                        subprocess.run(['notepad', '/p', temp.name], check=False)
                        messagebox.showinfo("Printed", "Product info sent to printer.")
                    except Exception:
                        messagebox.showerror("Printer Error", "Failed to send product info to printer. Install pywin32 for automatic printing: pip install pywin32")
                    
        except Exception as e:
            messagebox.showerror("Printer Error", f"Error: {e}")