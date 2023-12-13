import uuid
import json
import logging
from sqlalchemy import and_, or_
from be.model import db_conn
from be.model import error
from be.model import store


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

            for book_id, count in id_and_count:
                row = self.conn.query(store.StoreTable).filter_by(store_id=store_id, book_id=book_id).first()
                if row is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = row.stock_level
                book_info = row.book_info
                book_info_json = json.loads(book_info)
                price = book_info_json.get("price")

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                row = self.conn.query(store.StoreTable).filter(
                    and_(store.StoreTable.store_id == store_id, store.StoreTable.book_id == book_id,
                         store.StoreTable.stock_level >= count)).first()
                if row:
                    row.stock_level -= count
                    self.conn.add(row)
                else:
                    return error.error_stock_level_low(book_id) + (order_id,)

                new_order_detail = store.NewOrderDetail(order_id=uid, book_id=book_id, count=count, price=price)
                self.conn.add(new_order_detail)

            new_order = store.NewOrder(order_id=uid, store_id=store_id, user_id=user_id)
            self.conn.add(new_order)

            self.conn.commit()
            order_id = uid

        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        try:
            row = self.conn.query(store.NewOrder).filter_by(order_id=order_id).first()
            if row is None:
                return error.error_invalid_order_id(order_id)

            order_id = row.order_id
            buyer_id = row.user_id
            store_id = row.store_id

            if buyer_id != user_id:
                return error.error_authorization_fail()

            row = self.conn.query(store.User).filter_by(user_id=buyer_id).first()
            if row is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = row.balance
            if password != row.password:
                return error.error_authorization_fail()

            row = self.conn.query(store.UserStore).filter_by(store_id=store_id).first()
            if row is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = row.user_id

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            rows = self.conn.query(store.NewOrderDetail).filter_by(order_id=order_id).all()
            total_price = 0
            for row in rows:
                count = row.count
                price = row.price
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            row = self.conn.query(store.User).filter(
                and_(store.User.user_id == buyer_id, store.User.balance >= total_price)).first()
            if row:
                row.balance -= total_price
                self.conn.add(row)
            else:
                return error.error_not_sufficient_funds(order_id)

            rowcount = self.conn.query(store.User).filter_by(user_id=seller_id).update({'balance': store.User.balance + total_price})
            if rowcount == 0:
                return error.error_non_exist_user_id(seller_id)

            rowcount = self.conn.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
            if rowcount == 0:
                return error.error_invalid_order_id(order_id)

            rowcount = self.conn.query(store.NewOrder).filter_by(order_id=order_id).delete()
            if rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.conn.commit()

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            row = self.conn.query(store.User).filter_by(user_id=user_id).first()
            if row is None:
                return error.error_authorization_fail()

            if row.password != password:
                return error.error_authorization_fail()

            rowcount = self.conn.query(store.User).filter_by(user_id=user_id).update({'balance': store.User.balance + add_value})
            if rowcount == 0:
                return error.error_non_exist_user_id(user_id)

            self.conn.commit()

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"
