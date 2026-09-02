"""Password hashing."""

import bcrypt


#In this hashpw using the bytes for hasing the password nad also for decode use the hash
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


#check the password either passowrd is matching or not with the original password
def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
