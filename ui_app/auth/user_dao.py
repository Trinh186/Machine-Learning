"""Đọc/ghi tài khoản bằng kết nối và DatabaseError dùng chung."""
import mysql.connector

from dao.database import get_connection, DatabaseError


class UserDAO:
    def find_by_username(self, username: str):
        sql = """
            SELECT user_id, username, password_hash, full_name, role, is_active,
                   created_at, updated_at
            FROM users WHERE username = %s LIMIT 1
        """
        return self._one(sql, (username,))

    def find_by_id(self, user_id: int):
        sql = """
            SELECT user_id, username, password_hash, full_name, role, is_active,
                   created_at, updated_at
            FROM users WHERE user_id = %s LIMIT 1
        """
        return self._one(sql, (user_id,))

    def _one(self, sql, params):
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute(sql, params)
                return cur.fetchone()
            finally:
                cur.close()
        except mysql.connector.Error as exc:
            raise DatabaseError("Lỗi truy vấn bảng users.") from exc
        finally:
            conn.close()

    def list_users(self):
        sql = """
            SELECT user_id, username, full_name, role, is_active, created_at
            FROM users ORDER BY user_id DESC
        """
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute(sql)
                return cur.fetchall()
            finally:
                cur.close()
        except mysql.connector.Error as exc:
            raise DatabaseError("Không đọc được danh sách tài khoản.") from exc
        finally:
            conn.close()

    def create_user(self, username, full_name, password_hash, role="user"):
        sql = """
            INSERT INTO users (username, password_hash, full_name, role, is_active)
            VALUES (%s, %s, %s, %s, 1)
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            try:
                cur.execute(sql, (username, password_hash, full_name, role))
                new_id = cur.lastrowid
                conn.commit()
                return new_id
            except mysql.connector.IntegrityError as exc:
                conn.rollback()
                raise ValueError("Tên đăng nhập đã tồn tại.") from exc
            finally:
                cur.close()
        except mysql.connector.Error as exc:
            conn.rollback()
            raise DatabaseError("Không thể thêm tài khoản vào MySQL.") from exc
        finally:
            conn.close()

    def set_active(self, user_id: int, is_active: bool, actor_id: int):
        """Khóa/mở khóa; chặn tự khóa và chặn khóa Admin hoạt động cuối cùng."""
        conn = get_connection()
        try:
            conn.start_transaction()
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute(
                    "SELECT user_id, role, is_active FROM users WHERE user_id = %s FOR UPDATE",
                    (user_id,),
                )
                target = cur.fetchone()
                if target is None:
                    raise ValueError("Không tìm thấy tài khoản đã chọn.")
                if not is_active and user_id == actor_id:
                    raise ValueError("Không thể tự khóa tài khoản đang đăng nhập.")
                if (not is_active and target["role"] == "admin"
                        and bool(target["is_active"])):
                    cur.execute(
                        "SELECT user_id FROM users "
                        "WHERE role = 'admin' AND is_active = 1 FOR UPDATE"
                    )
                    if len(cur.fetchall()) <= 1:
                        raise ValueError("Không thể khóa Admin hoạt động cuối cùng.")
                cur.execute(
                    "UPDATE users SET is_active = %s WHERE user_id = %s",
                    (1 if is_active else 0, user_id),
                )
                conn.commit()
            finally:
                cur.close()
        except ValueError:
            conn.rollback()
            raise
        except mysql.connector.Error as exc:
            conn.rollback()
            raise DatabaseError("Không thể cập nhật trạng thái tài khoản.") from exc
        finally:
            conn.close()
