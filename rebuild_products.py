"""
rebuild_products.py - emergency recovery for a damaged products.json
====================================================================

Use this ONLY if products.json is damaged (empty / full of strange characters)
and there is no backup.

    python rebuild_products.py "C:\\path\\to\\data"

It does NOT touch sales.json. It rebuilds products.json from the sales history:
every product that was ever sold comes back with its barcode, name and latest
price. What CANNOT be recovered from sales:
    * the stock quantity   -> set to 0 (or the --stock value); recount and edit
    * the category         -> left empty
    * products never sold  -> add them again
The damaged file is kept next to it as products.json.damaged-<time>.
"""
import json, os, sys
from datetime import datetime


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    stock = 0
    if "--stock" in sys.argv:
        stock = int(sys.argv[sys.argv.index("--stock") + 1])
        args = [a for a in args if a != str(stock)]
    data_dir = args[0] if args else input("Path to the data folder: ").strip().strip('"')
    sales_path = os.path.join(data_dir, "sales.json")
    prod_path = os.path.join(data_dir, "products.json")

    print("\nChecking the data folder:")
    for name in sorted(os.listdir(data_dir)):
        if name.endswith(".json"):
            try:
                read_json(os.path.join(data_dir, name)); status = "OK"
            except Exception:
                status = "DAMAGED"
            print(f"  {name:28s} {status}")

    try:
        sales = read_json(sales_path)
    except Exception as exc:
        print(f"\nCannot read sales.json ({exc}). Nothing to rebuild from.")
        sys.exit(1)

    try:
        current = read_json(prod_path)
        if current:
            print(f"\nproducts.json is fine ({len(current)} products). Nothing to do.")
            return
    except Exception:
        pass   # damaged or empty -> rebuild

    def when(s):
        return f"{s.get('date', '')} {s.get('time', '')}"

    found = {}
    for sale in sorted(sales, key=when):                 # oldest -> newest, so latest price wins
        for it in sale.get("items", []):
            code = str(it.get("barcode", "")).strip()
            if not code:
                continue
            found[code] = {"barcode": code,
                           "name": it.get("name", code),
                           "category": "",
                           "price": float(it.get("price", 0)),
                           "quantity": stock}
    if not found:
        print("\nNo products found in sales history.")
        sys.exit(1)

    if os.path.exists(prod_path):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        os.replace(prod_path, f"{prod_path}.damaged-{stamp}")
    with open(prod_path, "w", encoding="utf-8") as f:
        json.dump(sorted(found.values(), key=lambda p: p["name"].lower()),
                  f, indent=4, ensure_ascii=False)
    print(f"\nRebuilt products.json with {len(found)} products (stock = {stock}).")
    print("Next: open Product Management and enter the real stock quantities.")


if __name__ == "__main__":
    main()