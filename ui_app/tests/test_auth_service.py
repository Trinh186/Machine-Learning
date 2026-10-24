import unittest
import bcrypt

from auth.auth_service import AuthService, AuthenticationError, AuthorizationError


class FakeDAO:
    def __init__(self):
        self.records = {
            "admin": {
                "user_id": 1, "username": "admin", "full_name": "Quản trị",
                "role": "admin", "is_active": 1,
                "password_hash": bcrypt.hashpw(b"Admin1234!", bcrypt.gensalt(4)).decode(),
            },
            "user01": {
                "user_id": 2, "username": "user01", "full_name": "Nhân viên",
                "role": "user", "is_active": 1,
                "password_hash": bcrypt.hashpw(b"User12345!", bcrypt.gensalt(4)).decode(),
            },
        }

    def find_by_username(self, username):
        return self.records.get(username)

    def find_by_id(self, user_id):
        return next((v for v in self.records.values() if v["user_id"] == user_id), None)

    def list_users(self):
        return list(self.records.values())

    def create_user(self, username, full_name, password_hash, role):
        new_id = max(item["user_id"] for item in self.records.values()) + 1
        self.records[username] = {
            "user_id": new_id, "username": username, "full_name": full_name,
            "role": role, "is_active": 1, "password_hash": password_hash,
        }
        return new_id

    def set_active(self, user_id, is_active, actor_id):
        user = self.find_by_id(user_id)
        if user is None:
            raise ValueError("Không tìm thấy tài khoản.")
        if actor_id == user_id and not is_active:
            raise ValueError("Không thể tự khóa tài khoản.")
        user["is_active"] = int(is_active)


class TestAuthService(unittest.TestCase):
    def setUp(self):
        self.dao = FakeDAO()
        self.auth = AuthService(self.dao)

    def test_correct_admin_login(self):
        user = self.auth.login("admin", "Admin1234!")
        self.assertEqual(user["role"], "admin")
        self.assertNotIn("password_hash", user)

    def test_wrong_password(self):
        with self.assertRaises(AuthenticationError):
            self.auth.login("admin", "wrong")

    def test_locked_user(self):
        self.dao.records["user01"]["is_active"] = 0
        with self.assertRaises(AuthenticationError):
            self.auth.login("user01", "User12345!")

    def test_non_admin_cannot_manage_accounts(self):
        self.auth.login("user01", "User12345!")
        with self.assertRaises(AuthorizationError):
            self.auth.list_users()

    def test_admin_can_add_user_with_hashed_password(self):
        self.auth.login("admin", "Admin1234!")
        self.auth.add_user("tester", "Test User", "Test12345!", "user")
        record = self.dao.records["tester"]
        self.assertNotEqual(record["password_hash"], "Test12345!")
        self.assertTrue(bcrypt.checkpw(b"Test12345!", record["password_hash"].encode()))

    def test_logout_clears_session(self):
        self.auth.login("admin", "Admin1234!")
        self.auth.logout()
        self.assertIsNone(self.auth.current_user)
        with self.assertRaises(AuthorizationError):
            self.auth.list_users()

    def test_role_change_or_lock_invalidates_admin_permissions(self):
        self.auth.login("admin", "Admin1234!")
        self.dao.records["admin"]["is_active"] = 0
        with self.assertRaises(AuthorizationError):
            self.auth.list_users()


if __name__ == "__main__":
    unittest.main()
