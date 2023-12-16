import json
from be.model import error
from be.model import db_conn
from be.model import store


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

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

            new_book = store.StoreTable(store_id=store_id, book_id=book_id, book_info=book_json_str, stock_level=stock_level)
            self.conn.add(new_book)

            # 加入全站书籍名录
            row = self.conn.query(store.BookDetail).filter_by(book_id=book_id).first()
            if row is None:
                book_info = json.loads(book_json_str)
                new_book_detail = store.BookDetail(
                    book_id=book_info["id"], title=book_info["title"], author=book_info["author"],
                    book_intro=book_info["book_intro"], content=book_info["content"], tags=str(book_info["tags"]))
                self.conn.add(new_book_detail)

            self.conn.commit()

        except BaseException as e:
            return 530, "{}".format(str(e))

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

            self.conn.query(store.StoreTable).filter_by(store_id=store_id, book_id=book_id).update(
                {'stock_level': store.StoreTable.stock_level + add_stock_level})
            self.conn.commit()

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            new_store = store.UserStore(user_id=user_id, store_id=store_id)
            self.conn.add(new_store)
            self.conn.commit()

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    # 发货
    def deliver_book(self, user_id: str, store_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            row = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).first()
            if row is None:
                return error.error_invalid_order_id(order_id)

            is_cancelled = row.is_cancelled
            if is_cancelled:
                return error.error_order_cancelled(order_id)
            is_paid = row.is_paid
            if not is_paid:
                return error.error_order_not_paid(order_id)

            # 更新历史订单状态为已发货
            rowcount = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).update({'is_delivered': True})
            if rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.conn.commit()

        except Exception as e:
            return 530, f"{str(e)}"
        return 200, "ok"
