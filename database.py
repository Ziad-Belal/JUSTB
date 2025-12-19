# retail_store_management/database.py

import mysql.connector
from mysql.connector import Error
from config import Config
import time


class Database:
    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.connection = None
            cls._instance.connect()
        return cls._instance

    def connect(self):
        """Establishes a connection to the MySQL database."""
        if self.connection and self.connection.is_connected():
            return self.connection

        retries = 5
        for i in range(retries):
            try:
                self.connection = mysql.connector.connect(
                    host=Config.DB_HOST,
                    database=Config.DB_NAME,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD
                )
                if self.connection.is_connected():
                    print(f"Successfully connected to MySQL database: {Config.DB_NAME}")
                    return self.connection
            except Error as e:
                print(f"Error connecting to MySQL database: {e}")
                if i < retries - 1:
                    print(f"Retrying connection in 5 seconds... ({i + 1}/{retries})")
                    time.sleep(5)
                else:
                    print("Failed to connect to the database after several retries.")
                    raise ConnectionError("Could not connect to the database.") from e
        return None

    def close(self):
        """Closes the database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed.")

    def execute_query(self, query, params=None, fetch=False, commit=False):
        """
        Executes a SQL query.
        :param query: The SQL query string.
        :param params: A tuple of parameters for the query.
        :param fetch: Boolean, if True, fetches results (for SELECT queries).
        :param commit: Boolean, if True, commits the transaction (for INSERT, UPDATE, DELETE).
        :return: Fetched data if fetch is True, otherwise None.
        """
        if not self.connection or not self.connection.is_connected():
            self.connect()  # Attempt to reconnect if disconnected

        if not self.connection or not self.connection.is_connected():
            print("Cannot execute query: No active database connection.")
            return None

        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)  # dictionary=True for column names
            cursor.execute(query, params)
            if commit:
                self.connection.commit()
            if fetch:
                return cursor.fetchall()
            return cursor.rowcount if commit else None  # For INSERT/UPDATE/DELETE, return rows affected
        except Error as e:
            print(f"Error executing query: {e}")
            if commit and self.connection:
                self.connection.rollback()  # Rollback in case of error
            return None
        finally:
            if cursor:
                cursor.close()

    def create_tables(self):
        """Creates necessary tables in the database if they don't exist."""

        # SQL to create tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('admin', 'worker') NOT NULL DEFAULT 'worker',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                stock_quantity INT NOT NULL DEFAULT 0,
                qr_code_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS promotions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(50) NOT NULL UNIQUE,
                discount_percentage DECIMAL(5, 2) NOT NULL, -- e.g., 10.00 for 10%
                start_date DATETIME NOT NULL,
                end_date DATETIME NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                total_amount DECIMAL(10, 2) NOT NULL,
                discount_amount DECIMAL(10, 2) DEFAULT 0.00,
                final_amount DECIMAL(10, 2) NOT NULL,
                promotion_id INT, -- NULL if no promotion applied
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (promotion_id) REFERENCES promotions(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sale_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sale_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                price_at_sale DECIMAL(10, 2) NOT NULL, -- Price of product at the time of sale
                FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
            """
        ]

        print("Creating tables if they don't exist...")
        for table_sql in tables:
            try:
                self.execute_query(table_sql, commit=True)
                # print(f"Executed: {table_sql.splitlines()[0].strip()}...")
            except Error as e:
                print(f"Error creating table: {e}")

        # Optional: Add a default admin user if no users exist
        if not self.execute_query("SELECT id FROM users WHERE role = 'admin'", fetch=True):
            print("No admin user found. Creating a default admin user (admin/adminpass)...")
            from utils.security import hash_password  # Import here to avoid circular dependency

            # Hash a default password for the admin
            default_admin_password = "adminpass"
            hashed_password = hash_password(default_admin_password)

            self.execute_query(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                ("admin", hashed_password, "admin"),
                commit=True
            )
            print("Default admin user created: username 'admin', password 'adminpass'")


# Global instance for easy access
db = Database()