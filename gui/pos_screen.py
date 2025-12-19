# gui/pos_screen.py
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from utils.helpers import load_json, save_json, get_today_date
import os
import tempfile

# Try to import win32 printing libs for silent printing on Windows
try:
    import win32print
    import win32ui
    from win32.lib import win32con
    import win32api
    WIN32_AVAILABLE = True
    WIN32API_AVAILABLE = True
except Exception:
    WIN32_AVAILABLE = False
    WIN32API_AVAILABLE = False


class POSScreen:
    def __init__(self, root, data_dir, frame_parent=None, user=None):
        self.root = root
        self.data_dir = data_dir
        self.user = user or {"username": "Unknown"}
        self.user_name = self.user.get("username", "Unknown")
        self.frame = tk.Frame(frame_parent or root, padx=10, pady=10)
        self.frame.pack(fill="both", expand=True)

        self.cart = []

        # Barcode entry
        tk.Label(self.frame, text="Barcode:", font=("Helvetica", 12, "bold")).grid(row=0, column=0, pady=5, sticky="e")
        self.barcode_entry = tk.Entry(self.frame, font=("Helvetica", 12))
        self.barcode_entry.grid(row=0, column=1, pady=5, sticky="w")
        self.barcode_entry.bind("<Return>", lambda e: self.add_to_cart())
        self.barcode_entry.focus()

        # Promo code
        tk.Label(self.frame, text="Promo Code:", font=("Helvetica", 12, "bold")).grid(row=1, column=0, pady=5, sticky="e")
        self.promo_entry = tk.Entry(self.frame, font=("Helvetica", 12))
        self.promo_entry.grid(row=1, column=1, pady=5, sticky="w")
        tk.Button(self.frame, text="Apply Promo", command=self.apply_promo, bg="green", fg="white").grid(row=1, column=2, padx=5)

        # Add product button -> behaves like pressing Enter: checks barcode then asks quantity only
        tk.Button(self.frame, text="Add Product", command=self.add_to_cart, bg="blue", fg="white").grid(row=0, column=2, padx=5)

        # Cart treeview
        columns = ("Name", "Qty", "Unit Price", "Total")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.grid(row=2, column=0, columnspan=3, pady=10, sticky="nsew")

        # grid stretch
        self.frame.grid_rowconfigure(2, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)

        self.total_label = tk.Label(self.frame, text="Grand Total: EGP 0.00", font=("Helvetica", 14, "bold"))
        self.total_label.grid(row=3, column=0, columnspan=3, pady=10)

        # Buttons
        tk.Button(self.frame, text="Finalize Sale", command=self.finalize_sale, bg="green", fg="white").grid(row=4, column=0, pady=10)
        tk.Button(self.frame, text="Clear Cart", command=self.clear_cart, bg="red", fg="white").grid(row=4, column=1, pady=10)

    def _products_path(self):
        return os.path.join(self.data_dir, "products.json")

    def _sales_path(self):
        return os.path.join(self.data_dir, "sales.json")

    def add_to_cart(self):
        """Add product to cart: check barcode exists -> ask only for quantity -> ensure stock limits."""
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            return

        products = load_json(self._products_path())
        product = next((p for p in products if str(p.get("barcode", "")) == barcode), None)
        if not product:
            messagebox.showerror("Error", "Product not in inventory. Add it first in Products tab.")
            self.barcode_entry.delete(0, tk.END)
            return

        # Available and already-in-cart quantities
        available_qty = int(product.get("quantity", 0))
        in_cart_qty = sum(item["quantity"] for item in self.cart if item["barcode"] == barcode)
        remaining = max(0, available_qty - in_cart_qty)
        if remaining <= 0:
            messagebox.showinfo("Info", f"Cannot add more. Only {available_qty} available.")
            self.barcode_entry.delete(0, tk.END)
            return

        # Ask how many to add (bulk add) - only quantity prompt
        qty = simpledialog.askinteger("Quantity", f"How many to add? (max {remaining})", minvalue=1, maxvalue=remaining, parent=self.frame)
        if qty is None:
            self.barcode_entry.delete(0, tk.END)
            return

        # Add / increase in cart
        for item in self.cart:
            if item["barcode"] == barcode:
                item["quantity"] += qty
                self.update_tree()
                self.update_total()
                self.barcode_entry.delete(0, tk.END)
                return

        self.cart.append({
            "barcode": product["barcode"],
            "name": product["name"],
            "price": float(product["price"]),
            "quantity": qty
        })
        self.update_tree()
        self.update_total()
        self.barcode_entry.delete(0, tk.END)

    def update_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for item in self.cart:
            total = float(item["price"]) * int(item["quantity"])
            self.tree.insert("", "end", values=(item["name"], item["quantity"], f"{float(item['price']):.2f}", f"{total:.2f}"))

    def update_total(self, discount=0):
        total = sum(float(i["price"]) * int(i["quantity"]) for i in self.cart)
        total_after_discount = total * (1 - float(discount)/100.0)
        self.total_label.config(text=f"Grand Total: EGP {total_after_discount:.2f}")

    def apply_promo(self):
        code = self.promo_entry.get().strip()
        promo_path = os.path.join(self.data_dir, "promo_codes.json")
        promos = load_json(promo_path)
        promo = next((p for p in promos if p.get("code") == code and int(p.get("uses_left", 0)) > 0), None)
        if not promo:
            messagebox.showerror("Error", "Invalid promo code")
            return
        self.update_total(discount=float(promo.get("discount_percentage", 0)))
        messagebox.showinfo("Success", f"Promo applied: {promo.get('discount_percentage', 0)}% off")

    def finalize_sale(self):
        if not self.cart:
            return

        # Decrease inventory
        products = load_json(self._products_path())
        for item in self.cart:
            prod = next((p for p in products if str(p.get("barcode", "")) == str(item["barcode"])), None)
            if prod:
                prod["quantity"] = max(0, int(prod.get("quantity", 0)) - int(item["quantity"]))
        save_json(self._products_path(), products)

        # Save sale
        sales = load_json(self._sales_path())
        sale_id = len(sales) + 1
        total = sum(float(i["price"]) * int(i["quantity"]) for i in self.cart)
        sale_record = {
            "id": sale_id,
            "user": self.user_name,
            "items": self.cart,
            "total": total,
            "date": get_today_date()
        }
        sales.append(sale_record)
        save_json(self._sales_path(), sales)

        # Print receipt directly (NO SAVE POPUP)
        self.print_receipt_direct(sale_id, sale_record)
        self.clear_cart()

    def clear_cart(self):
        self.cart = []
        self.update_tree()
        self.update_total()

    def print_receipt_direct(self, sale_id, sale_record):
        """
        Auto-print receipt to a connected receipt printer (IBM) using pywin32 when available.
        Falls back to the Windows `print` command if pywin32 is not available.
        """
        receipt_lines = [f"Receipt #{sale_id} - {get_today_date()}", f"User: {self.user_name}", "-"*40]
        for i in sale_record["items"]:
            line = f"{i['name']} | Qty: {i['quantity']} | {i['price']} x {i['quantity']} = {float(i['price']) * int(i['quantity']):.2f}"
            receipt_lines.append(line)
        total = sale_record["total"]
        receipt_lines.append("-"*40)
        receipt_lines.append(f"Grand Total: EGP {total:.2f}")
        receipt_lines.append("\nThank you for shopping with JustB!")

        # Write to a temporary file (used by fallback and by some printers)
        temp = None
        try:
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w', encoding='utf-8')
            temp.write("\n".join(receipt_lines))
            temp.close()

            # Try win32api for silent printing
            if WIN32API_AVAILABLE:
                try:
                    win32api.ShellExecute(0, "print", temp.name, None, ".", 0)
                    messagebox.showinfo("Success", "Sale completed! Receipt printed.")
                    return
                except Exception as e:
                    print("win32api print failed:", e)

            # Fallback: use the Windows print command
            import subprocess
            try:
                subprocess.run(['cmd', '/c', f'print "{temp.name}"'], capture_output=True, timeout=10)
                messagebox.showinfo("Success", "Sale completed! Receipt printed (fallback).")
            except Exception as e:
                messagebox.showwarning("Error", f"Sale completed but printing failed: {e}")

        except Exception as e:
            messagebox.showwarning("Error", f"Sale completed but printing failed: {e}")
        finally:
            try:
                if temp is not None:
                    os.remove(temp.name)
            except Exception:
                pass