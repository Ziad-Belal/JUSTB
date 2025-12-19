import mysql.connector
from utils.security import hash_password
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
cursor = conn.cursor()

# Remove old invalid admin (if exists)
cursor.execute("DELETE FROM users WHERE username='admin'")

# Create a proper hashed password
password = "admin123"
hashed_password = hash_password(password)

cursor.execute(
    "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
    ("admin", hashed_password, "Admin")
)
conn.commit()
cursor.close()
conn.close()

print("Fresh default admin created!")
print("Username: admin")
print("Password: admin123")
