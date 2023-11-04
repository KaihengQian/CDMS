import jwt
import time
import logging
import pymongo
import pymongo.errors
from be.model import error
from be.model import db_conn


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded.encode("utf-8").decode("utf-8")


def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        super().__init__()

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str):
        try:
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            user_col = self.db.get_collection("user")
            user_info = {
                "user_id": user_id,
                "password": password,
                "balance": 0,
                "token": token,
                "terminal": terminal
            }
            user_col.insert_one(user_info)
        except pymongo.errors.PyMongoError:
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        user_col = self.db.get_collection("user")
        row = user_col.find_one({'user_id': user_id})
        if row is None:
            return error.error_authorization_fail()
        db_token = row.get("token", "")
        if not self.__check_token(user_id, db_token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        user_col = self.db.get_collection("user")
        row = user_col.find_one({'user_id': user_id})
        if row is None:
            return error.error_authorization_fail()

        if password != row.get("password", ""):
            return error.error_authorization_fail()

        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            user_col = self.db.get_collection("user")
            condition = {'user_id': user_id}
            update_data = {'$set': {'token': token, 'terminal': terminal}}
            user_col.update_one(condition, update_data)

        except Exception as e:
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)

            user_col = self.db.get_collection("user")
            condition = {'user_id': user_id}
            update_data = {'$set': {'token': dummy_token, 'terminal': terminal}}
            user_col.update_one(condition, update_data)

        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            user_col = self.db.get_collection("user")
            # cursor = user_col.find({'user_id': user_id})
            num = user_col.count_documents({'user_id': user_id})
            if num == 1:
                user_col.delete_one({'user_id': user_id})
                return 200, "ok"
            else:
                return error.error_authorization_fail()

        except Exception as e:
            return 530, "{}".format(str(e))

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            user_col = self.db.get_collection("user")
            condition = {'user_id': user_id}
            update_data = {'$set': {'password': new_password, 'token': token, 'terminal': terminal}}
            user_col.update_one(condition, update_data)

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
