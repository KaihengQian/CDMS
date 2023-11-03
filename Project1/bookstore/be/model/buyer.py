import pymongo
from flask import jsonify
from pymongo.errors import ConnectionFailure, OperationFailure
import uuid
import json
import logging
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        super().__init__()

    def new_order(
        self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            order_id = uid

            store_col = self.db.get_collection("store")
            book_info_list = []
            for book_id, count in id_and_count:
                book_info = store_col.find_one({"store_id": store_id, "book_id": book_id})
                if book_info is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = book_info.get("stock_level")
                price = book_info.get("book_info").get("price")

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                result = store_col.update_one(
                    {"store_id": store_id, "book_id": book_id, "stock_level": {"$gte": count}},
                    {"$inc": {"stock_level": -count}}
                )

                if result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                new_order_detail_col = self.db.get_collection("new_order_detail")
                new_order_detail_col.insert_one({
                    "order_id": uid,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                })

                entry = {
                    "book_id": book_id,
                    "count": count,
                    "price": price
                }
                book_info_list.append(entry)

            new_order_col = self.db.get_collection("new_order")
            new_order_col.insert_one({
                "order_id": order_id,
                "store_id": store_id,
                "user_id": user_id
            })

            # 加入历史订单
            history_order_col = self.db.get_collection("history_order")
            history_order_col.insert_one({
                "order_id": order_id,
                "store_id": store_id,
                "user_id": user_id,
                "book_info": book_info_list,
                "is_cancelled": 0,
                "is_paid": 0,
                "is_delivered": 0,
                "is_received": 0
            })

        except ConnectionFailure as cf:
            logging.info(f"528 Connection failed: {str(cf)}")
            return 528, f"{str(cf)}", ""
        except OperationFailure as of:
            logging.info(f"528 Operation failed: {str(of)}")
            return 528, f"{str(of)}", ""

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            new_order_col = self.db.get_collection("new_order")
            order = new_order_col.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)

            order_id = order.get("order_id")
            buyer_id = order.get("user_id")
            store_id = order.get("store_id")

            if buyer_id != user_id:
                return error.error_authorization_fail()

            user_col = self.db.get_collection("user")
            buyer = user_col.find_one({"user_id": buyer_id})
            if buyer is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = buyer.get("balance")

            if password != buyer.get("password"):
                return error.error_authorization_fail()

            user_store_col = self.db.get_collection("user_store")
            store = user_store_col.find_one({"store_id": store_id})
            if store is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = store.get("user_id")

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            new_order_detail_col = self.db.get_collection("new_order_detail")
            order_details = new_order_detail_col.find({"order_id": order_id})
            total_price = 0

            for detail in order_details:
                count = detail.get("count")
                price = detail.get("price")
                total_price += (price * count)

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            buyer_update_res = user_col.update_one(
                {"user_id": buyer_id, "balance": {"$gte": total_price}},
                {"$inc": {"balance": -total_price}}
            )

            if buyer_update_res.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            buyer_update_res1 = user_col.update_one(
                {"user_id": buyer_id},
                {"$inc": {"balance": total_price}}
            )

            if buyer_update_res1.modified_count == 0:
                return error.error_non_exist_user_id(buyer_id)

            # 更新历史订单状态为已支付
            history_order_col = self.db.get_collection("history_order")
            order_now = history_order_col.find_one({"order_id": order_id})
            if order_now is None:
                return error.error_invalid_order_id(order_id)
            history_order_col.update_one(
                {"order_id": order_id, "user_id": user_id},
                {"$set": {"is_paid": True}}
            )

            order_del_res = new_order_col.delete_one({"order_id": order_id})

            if order_del_res.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            order_detail_del_res = new_order_detail_col.delete_one({"order_id": order_id})

            if order_detail_del_res.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

        except ConnectionFailure as cf:
            logging.info(f"528 Connection failed: {str(cf)}")
            return 528, f"{str(cf)}", ""
        except OperationFailure as of:
            logging.info(f"528 Operation failed: {str(of)}")
            return 528, f"{str(of)}", ""

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user_col = self.db.get_collection("user")
            user = user_col.find_one({"user_id": user_id})

            if user is None:
                return error.error_authorization_fail()

            if user.get("password") != password:
                return error.error_authorization_fail()

            user_update_res = user_col.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": add_value}}
            )

            if user_update_res.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

        except ConnectionFailure as cf:
            logging.info(f"528 Connection failed: {str(cf)}")
            return 528, f"{str(cf)}", ""
        except OperationFailure as of:
            logging.info(f"528 Operation failed: {str(of)}")
            return 528, f"{str(of)}", ""
        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok"

    def receive_book(self, user_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            history_order_col = self.db.get_collection("history_order")
            order = history_order_col.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)
            is_cancelled = order.get("is_cancelled")
            if is_cancelled:
                return error.error_order_cancelled(order_id)
            is_delivered = order.get("is_delivered")
            if not is_delivered:
                return error.error_order_not_delivered(order_id)

            condition = {'order_id': order_id}
            update_data = {'$set': {'is_received': True}}
            history_order_col.update_one(condition, update_data)

        except ConnectionFailure as cf:
            logging.info(f"528 Connection failed: {str(cf)}")
            return 528, f"{str(cf)}", ""
        except OperationFailure as of:
            logging.info(f"528 Operation failed: {str(of)}")
            return 528, f"{str(of)}", ""
        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok"

    def cancel_order(self, user_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            history_order_col = self.db.get_collection("history_order")
            order = history_order_col.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)
            is_cancelled = order.get("is_cancelled")
            if is_cancelled:
                return error.error_order_cancelled(order_id)
            is_paid = order.get("is_delivered")
            if is_paid:
                return error.error_order_cancellation_fail(order_id)

            condition = {'order_id': order_id}
            update_data = {'$set': {'is_cancelled': True}}
            history_order_col.update_one(condition, update_data)

        except ConnectionFailure as cf:
            logging.info(f"528 Connection failed: {str(cf)}")
            return 528, f"{str(cf)}", ""
        except OperationFailure as of:
            logging.info(f"528 Operation failed: {str(of)}")
            return 528, f"{str(of)}", ""
        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok"

    def search_history_order(self, user_id, password, order_id, page, per_page):
        try:
            user_col = self.db.get_collection("user")
            user = user_col.find_one({"user_id": user_id})

            if user is None:
                return error.error_authorization_fail()

            if user.get("password") != password:
                return error.error_authorization_fail()

            order_col = self.db.get_collection("history_order")
            if order_id is None:
                order = order_col.find({"user_id": user_id})
            else:
                order = order_col.find_one({"order_id": order_id, "user_id": user_id})

            if order is None:
                return error.error_non_history_order(user_id)

            res = None
            if len(order) < per_page:
                res = order
            else:
                start = (page - 1) * per_page
                end = start + per_page
                if start > len(order) - 1 or end > len(order) - 1:
                    res = order[-per_page:]

            return 200, jsonify({"results": res})

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

    def search_book(self, store_id, title, author, content, tags):
        try:
            store_col = self.db.get_collection("store")
            if store_id is not None:
                store_col = store_col.find({"store_id": store_id})
            find_condition = {}
            book_info = store_col.find(find_condition)

            if book_info is None:
                return error.error_non_search_result()

        except ConnectionFailure as cf:
            logging.info(f"528 Connection failed: {str(cf)}")
            return 528, f"{str(cf)}", ""
        except OperationFailure as of:
            logging.info(f"528 Operation failed: {str(of)}")
            return 528, f"{str(of)}", ""
        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok"
