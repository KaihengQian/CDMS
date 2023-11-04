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
            for book_id, count in id_and_count:
                store_data = store_col.find_one({"store_id": store_id, "book_id": book_id})
                if store_data is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = store_data["stock_level"]
                book_info = json.loads(store_data["book_info"])
                price = book_info["price"]

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                store_col.update_one(
                    {"store_id": store_id, "book_id": book_id, "stock_level": {"$gte": count}},
                    {"$inc": {"stock_level": -count}}
                )

                new_order_detail_col = self.db.get_collection("new_order_detail")
                new_order_detail_col.insert_one({
                    "order_id": uid,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                })

            new_order_col = self.db.get_collection("new_order")
            new_order_col.insert_one({
                "order_id": uid,
                "store_id": store_id,
                "user_id": user_id
            })

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

            buyer_id = order.get("user_id")
            store_id = order.get("store_id")

            if buyer_id != user_id:
                return error.error_authorization_fail()

            user_col = self.db.get_collection("user")
            buyer = user_col.find_one({"user_id": buyer_id})
            if buyer is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = buyer.get("balance")

            if password != buyer["password"]:
                return error.error_authorization_fail()

            user_store_col = self.db.get_collection("user_store")
            store_data = user_store_col.find_one({"store_id": store_id})
            if store_data is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = store_data.get("user_id")

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            total_price = 0
            new_order_detail_col = self.db.get_collection("new_order_detail")
            order_details = new_order_detail_col.find({"order_id": order_id})

            for detail in order_details:
                count = detail["count"]
                price = detail["price"]
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

            new_order_col.delete_one({"order_id": order_id})

            new_order_detail_col.delete_many({"order_id": order_id})

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

            user_col.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": add_value}}
            )

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok"
