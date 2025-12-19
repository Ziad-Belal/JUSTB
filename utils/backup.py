import mysql.connector
import sqlite3
import os
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

BACKUP_FILE = "backup.db"

def init_backup():
    if not os.path.exists(BACKUP_FILE):
        conn = sqlite3.connect(BACKUP_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            sale_date TEXT,
            total_amount REAL
        )""")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY,
            sale_id INTEGER,
            product_id INTEGER,
            quantity_sold INTEGER,
            price_per_unit REAL
        )""")
        conn.commit()
        conn.close()

def backup_new_data():
    init_backup()
    mysql_conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    mysql_cursor = mysql_conn.cursor(dictionary=True)

    sqlite_conn = sqlite3.connect(BACKUP_FILE)
    sqlite_cursor = sqlite_conn.cursor()

    sqlite_cursor.execute("SELECT MAX(id) FROM sales")
    last_backup_id = sqlite_cursor.fetchone()[0] or 0

    mysql_cursor.execute("SELECT * FROM sales WHERE id > %s", (last_backup_id,))
    new_sales = mysql_cursor.fetchall()

    for sale in new_sales:
        sqlite_cursor.execute("INSERT INTO sales (id, sale_date, total_amount) VALUES (?, ?, ?)",
                              (sale['id'], str(sale['sale_date']), float(sale['total_amount'])))
        mysql_cursor.execute("SELECT * FROM sale_items WHERE sale_id = %s", (sale['id'],))
        items = mysql_cursor.fetchall()
        for item in items:
            sqlite_cursor.execute("""INSERT INTO sale_items 
                                     (id, sale_id, product_id, quantity_sold, price_per_unit)
                                     VALUES (?, ?, ?, ?, ?)""",
                                  (item['id'], item['sale_id'], item['product_id'],
                                   item['quantity_sold'], float(item['price_per_unit'])))

    sqlite_conn.commit()
    sqlite_conn.close()
    mysql_cursor.close()
    mysql_conn.close()
