import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure
import uuid
import json
import logging
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

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

            store_col = self.conn["store"]
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

                new_order_detail_col = self.conn["new_order_detail"]
                new_order_detail_col.insert_one({
                    "order_id": uid,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                })

            new_order_col = self.conn["new_order"]
            new_order_col.insert_one({
                "order_id": order_id,
                "store_id": store_id,
                "user_id": user_id
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
            new_order_col = self.conn["new_order"]
            order = new_order_col.find_one({"order_id": order_id})
            if order is None:
                return error.error_invalid_order_id(order_id)

            order_id = order.get("order_id")
            buyer_id = order.get("user_id")
            store_id = order.get("store_id")

            if buyer_id != user_id:
                return error.error_authorization_fail()

            user_col = self.conn["user"]
            buyer = user_col.find_one({"user_id": buyer_id})
            if buyer is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = buyer.get("balance")

            if password != buyer.get("password"):
                return error.error_authorization_fail()

            user_store_col = self.conn["user_store"]
            store = user_store_col.find_one({"store_id": store_id})
            if store is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = store.get("user_id")

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            new_order_detail_col = self.conn["new_order_detail"]
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
            user_col = self.conn["user"]
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
