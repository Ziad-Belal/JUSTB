"""
migrate_passwords.py
====================
Run ONCE from your project root to hash all plain-text passwords in users.json.

    python migrate_passwords.py

After running, every password in users.json will be a bcrypt hash.
The original passwords are NOT stored anywhere — make sure you know them before running.
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

USERS_FILE = r"C:\Users\Ziad\JUSTB\gui\data\users.json"   # ← adjust if needed

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt not installed.  Run:  pip install bcrypt")
    sys.exit(1)

def is_hashed(value):
    return isinstance(value, str) and value.startswith(("$2b$", "$2a$", "$2y$"))

def hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

if not os.path.exists(USERS_FILE):
    print(f"ERROR: users.json not found at:\n  {USERS_FILE}")
    print("Update the USERS_FILE path in this script and re-run.")
    sys.exit(1)

with open(USERS_FILE, "r", encoding="utf-8") as f:
    users = json.load(f)

migrated = 0
skipped  = 0

for user in users:
    pwd = user.get("password", "")
    if is_hashed(pwd):
        print(f"  [SKIP]     {user['username']!r:20s} — already hashed")
        skipped += 1
    else:
        user["password"] = hash_password(pwd)
        print(f"  [HASHED]   {user['username']!r:20s} — plain text → bcrypt")
        migrated += 1

with open(USERS_FILE, "w", encoding="utf-8") as f:
    json.dump(users, f, indent=4, ensure_ascii=False)

print(f"\nDone.  {migrated} password(s) hashed,  {skipped} already secure.")
print("The original plain-text passwords are now gone from the file.")