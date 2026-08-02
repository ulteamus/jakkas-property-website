from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from database import execute, query_one


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.full_name = row.get("full_name")
        self.phone = row.get("phone")
        self.role = row.get("role", "user")

    @property
    def is_admin(self):
        return self.role == "admin"

    @staticmethod
    def get_by_id(user_id):
        row = query_one("SELECT * FROM users WHERE id = %s", (user_id,))
        return User(row) if row else None

    @staticmethod
    def get_by_username(username):
        row = query_one("SELECT * FROM users WHERE username = %s", (username,))
        return User(row) if row else None

    @staticmethod
    def get_by_email(email):
        row = query_one("SELECT * FROM users WHERE email = %s", (email,))
        return User(row) if row else None

    @staticmethod
    def create(username, email, password, full_name=None, phone=None, role="user"):
        pw_hash = generate_password_hash(password)
        uid = execute(
            """INSERT INTO users (username, email, password_hash, full_name, phone, role)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (username, email, pw_hash, full_name, phone, role),
        )
        return User.get_by_id(uid)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
