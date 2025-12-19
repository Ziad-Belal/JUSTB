import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.helpers import load_json, get_today_date
import os

class DailyFeedbackScreen:
    def __init__(self, root, data_dir=None, frame_parent=None, admin=False):
        self.root = root
        self.data_dir = data_dir
        self.admin = admin
        self.frame = tk.Frame(frame_parent or root, padx=10, pady=10)
        self.frame.pack(fill="both", expand=True)

        # Labels
        tk.Label(self.frame, text="Total Revenue Today:").grid(row=0, column=0, sticky="w")
        tk.Label(self.frame, text="Total Sales Today:").grid(row=1, column=0, sticky="w")
        self.total_revenue_label = tk.Label(self.frame, text="EGP 0.00")
        self.total_sales_label = tk.Label(self.frame, text="0")
        self.total_revenue_label.grid(row=0, column=1, sticky="w")
        self.total_sales_label.grid(row=1, column=1, sticky="w")

        # Treeview for product-wise sales
        columns = ("Product", "Qty Sold", "Revenue")
        self.tree = ttk.Treeview(self.frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=120)
        self.tree.grid(row=2, column=0, columnspan=3, pady=10)

        # Admin buttons
        if self.admin:
            tk.Button(self.frame, text="Refresh", command=self.load_data).grid(row=3, column=0)
            tk.Button(self.frame, text="Print Report", command=self.print_report).grid(row=3, column=1)
            tk.Button(self.frame, text="Set Feedback Date", command=self.set_feedback_date).grid(row=3, column=2)

        # Default date
        self.feedback_date = get_today_date()
        self.load_data()

    def set_feedback_date(self):
        from tkinter.simpledialog import askstring
        date_str = askstring("Feedback Date", "Enter date (YYYY-MM-DD):", initialvalue=self.feedback_date)
        if date_str:
            self.feedback_date = date_str
            self.load_data()

    def load_data(self):
        # Clear tree
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Load sales and products
        sales_path = os.path.join(self.data_dir, "sales.json")
        products_path = os.path.join(self.data_dir, "products.json")
        sales = load_json(sales_path)
        products = load_json(products_path)

        total_revenue = 0
        total_sales_count = 0
        product_summary = {}

        for sale in sales:
            sale_date = sale.get("date", get_today_date())
            if sale_date == self.feedback_date:
                total_sales_count += 1
                total_revenue += sale["total"]
                for item in sale["items"]:
                    code = item["barcode"]
                    if code not in product_summary:
                        product_summary[code] = {"name": item["name"], "qty": 0, "revenue": 0}
                    product_summary[code]["qty"] += item["quantity"]
                    product_summary[code]["revenue"] += item["price"] * item["quantity"]

        self.total_revenue_label.config(text=f"EGP {total_revenue:.2f}")
        self.total_sales_label.config(text=str(total_sales_count))

        for code, summary in product_summary.items():
            self.tree.insert("", "end", values=(summary["name"], summary["qty"], f"EGP {summary['revenue']:.2f}"))

    def print_report(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
        if not file_path:
            return

        with open(file_path, "w") as f:
            f.write(f"Daily Feedback Report - {self.feedback_date}\n")
            f.write(f"Total Revenue: {self.total_revenue_label.cget('text')}\n")
            f.write(f"Total Sales: {self.total_sales_label.cget('text')}\n\n")
            f.write("Product-wise Sales:\n")
            for item in self.tree.get_children():
                values = self.tree.item(item)["values"]
                f.write(f"{values[0]} | Qty: {values[1]} | Revenue: {values[2]}\n")

        messagebox.showinfo("Success", f"Report saved as {file_path}")
