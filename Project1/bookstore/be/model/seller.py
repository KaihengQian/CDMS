import json
import re
import jieba
import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure
from be.model import error
from be.model import db_conn


class Seller(db_conn.DBConn):
    def __init__(self):
        super().__init__()

    # 分词
    def split_words(self, text):
        words = re.sub(r'[^\w\s\n]', '', text)
        words = re.sub(r'\n', '', words)
        res = jieba.cut(words, cut_all=False)
        res_str = ' '.join(res)
        return res_str

    def add_book(
            self,
            user_id: str,
            store_id: str,
            book_id: str,
            book_json_str: str,
            stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            store_col = self.db.get_collection("store")
            store_col.insert_one({
                "store_id": store_id,
                "book_id": book_id,
                "book_info": book_json_str,
                "stock_level": stock_level
            })

            # 加入全站书籍名录
            book_detail_col = self.db.get_collection("book_detail")
            row = book_detail_col.find_one({'book_id': book_id})
            if row is None:
                book_info = json.loads(book_json_str)
                des_str = book_info["title"] + self.split_words(book_info["title"]) + " " + \
                          self.split_words(book_info["book_intro"]) + " " + self.split_words(book_info["content"])
                book_data = {
                    "book_id": book_info["id"],
                    "title": book_info["title"],
                    "author": book_info["author"],
                    "book_intro": book_info["book_intro"],
                    "content": book_info["content"],
                    "tags": book_info["tags"],
                    "description": des_str
                }
                book_detail_col.insert_one(book_data)

        except ConnectionFailure as cf:
            return 528, f"{str(cf)}"
        except OperationFailure as of:
            return 528, f"{str(of)}"

        except Exception as e:
            return 530, f"{str(e)}"

        return 200, "ok"

    def add_stock_level(
            self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            store_col = self.db.get_collection("store")
            store_col.update_one(
                {"store_id": store_id, "book_id": book_id},
                {"$inc": {"stock_level": add_stock_level}}
            )

        except ConnectionFailure as cf:
            return 528, f"{str(cf)}"
        except OperationFailure as of:
            return 528, f"{str(of)}"

        except Exception as e:
            return 530, f"{str(e)}"
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            user_store_col = self.db.get_collection("user_store")
            user_store_col.insert_one({"store_id": store_id, "user_id": user_id})

        except ConnectionFailure as cf:
            return 528, f"{str(cf)}"
        except OperationFailure as of:
            return 528, f"{str(of)}"

        except Exception as e:
            return 530, f"{str(e)}"
        return 200, "ok"

    # 发货
    def deliver_book(self, user_id: str, store_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            history_order_col = self.db.get_collection("history_order")
            order = history_order_col.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)
            is_cancelled = order.get("is_cancelled")
            if is_cancelled:
                return error.error_order_cancelled(order_id)
            is_paid = order.get("is_paid")
            if not is_paid:
                return error.error_order_not_paid(order_id)

            # 更新历史订单状态为已发货
            condition = {'order_id': order_id}
            update_data = {'$set': {'is_delivered': True}}
            history_order_col.update_one(condition, update_data)

        except ConnectionFailure as cf:
            return 528, f"{str(cf)}"
        except OperationFailure as of:
            return 528, f"{str(of)}"

        except Exception as e:
            return 530, f"{str(e)}"
        return 200, "ok"
