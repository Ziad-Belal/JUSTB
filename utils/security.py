import bcrypt

def verify_password(hashed, plain):
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
