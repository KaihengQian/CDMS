import uuid
import json
import logging
from datetime import datetime
from sqlalchemy import and_
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

            book_info_list = []  # 储存历史订单中的书籍购买信息

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

                entry = {
                    "book_id": book_id,
                    "count": count,
                    "price": price
                }
                book_info_list.append(entry)

            new_order = store.NewOrder(order_id=uid, store_id=store_id, user_id=user_id)
            self.conn.add(new_order)

            # 加入历史订单
            new_history_order = store.HistoryOrder(
                order_id=uid, user_id=user_id, store_id=store_id, create_time=datetime.now(), book_info=book_info_list,
                is_cancelled=False, is_paid=False, is_delivered=False, is_received=False)
            self.conn.add(new_history_order)

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

            # 更新历史订单状态为已支付
            rowcount = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).update({'is_paid': True})
            if rowcount == 0:
                return error.error_invalid_order_id(order_id)

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

    # 收货
    def receive_book(self, user_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            row = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).first()
            if row is None:
                return error.error_invalid_order_id(order_id)

            is_cancelled = row.is_cancelled
            if is_cancelled:
                return error.error_order_cancelled(order_id)
            is_delivered = row.is_delivered
            if not is_delivered:
                return error.error_order_not_delivered(order_id)

            # 更新历史订单状态为已收货
            rowcount = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).update({'is_received': True})
            if rowcount == 0:
                return error.error_invalid_order_id(order_id)

            self.conn.commit()

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok"

    # 买家主动取消订单
    def buyer_cancel_order(self, user_id: str, order_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            row = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).first()
            if row is None:
                return error.error_invalid_order_id(order_id)

            is_cancelled = row.is_cancelled
            if is_cancelled:
                return error.error_order_cancelled(order_id)
            # 订单状态为已支付时无法取消订单
            is_paid = row.is_paid
            if is_paid:
                return error.error_order_cancellation_fail(order_id)

            self.cancel_order(order_id)
            self.conn.commit()

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok, order cancelled"

    # 超时自动取消订单
    def overtime_cancel_order(self):
        try:
            living_time = 15 * 60  # 未支付订单最长保留时间

            # 检查所有历史订单
            rows = self.conn.query(store.HistoryOrder).all()
            num_rows = len(rows)
            if num_rows == 0:
                return 200, "ok"

            num_cancelled = 0  # 记录取消订单数量

            for row in rows:
                order_id = row.order_id
                create_time = row.create_time
                is_cancelled = row.is_cancelled
                is_paid = row.is_paid
                if is_cancelled or is_paid:
                    continue

                # 计算时间差
                current_time = datetime.now()
                time_passed = (current_time - create_time).total_seconds()
                if time_passed > living_time:
                    self.cancel_order(order_id)
                    num_cancelled += 1

            self.conn.commit()

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok, {} orders cancelled".format(num_cancelled)

    def cancel_order(self, order_id):
        # 更新历史订单状态为已取消
        self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).update({'is_cancelled': True})

        # 还原书籍库存
        row = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id).first()
        store_id = row.store_id
        book_info_list = row.book_info
        for book_info in book_info_list:
            book_id = book_info.get("book_id")
            count = book_info.get("count")
            self.conn.query(store.StoreTable).filter_by(store_id=store_id, book_id=book_id).update(
                {'stock_level': store.StoreTable.stock_level + count})

        # 删除new_order和new_order_detail中的相关记录
        rowcount = self.conn.query(store.NewOrder).filter_by(order_id=order_id).delete()
        if rowcount == 0:
            return error.error_invalid_order_id(order_id)

        rowcount = self.conn.query(store.NewOrderDetail).filter_by(order_id=order_id).delete()
        if rowcount == 0:
            return error.error_invalid_order_id(order_id)

        self.conn.commit()

    # 搜索历史订单
    def search_history_order(self, user_id, order_id, page, per_page):
        try:
            row = self.conn.query(store.User).filter_by(user_id=user_id).first()
            if row is None:
                return error.error_authorization_fail()

            if order_id == "":
                rows = self.conn.query(store.HistoryOrder).filter_by(user_id=user_id).all()

                num_rows = len(rows)
                if num_rows == 0:
                    return error.error_non_history_order(user_id)

                results = self.paging(rows, page, per_page, num_rows)

                res = []
                for result in results:
                    res.append((
                        f"Order ID: {result.order_id}\n"
                        f"User ID: {result.user_id}\n"
                        f"Store ID: {result.store_id}\n"
                        f"Create Time: {result.create_time}\n"
                        f"Book Info: {result.book_info}\n"
                        f"Is Cancelled: {result.is_cancelled}\n"
                        f"Is Paid: {result.is_paid}\n"
                        f"Is Delivered: {result.is_delivered}\n"
                        f"Is Received: {result.is_received}\n"
                    ))

            else:
                row = self.conn.query(store.HistoryOrder).filter_by(order_id=order_id, user_id=user_id).first()
                if row is None:
                    return error.error_non_history_order(user_id)

                res = (
                    f"Order ID: {row.order_id}\n"
                    f"User ID: {row.user_id}\n"
                    f"Store ID: {row.store_id}\n"
                    f"Create Time: {row.create_time}\n"
                    f"Book Info: {row.book_info}\n"
                    f"Is Cancelled: {row.is_cancelled}\n"
                    f"Is Paid: {row.is_paid}\n"
                    f"Is Delivered: {row.is_delivered}\n"
                    f"Is Received: {row.is_received}\n"
                )

            self.conn.commit()

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}"

        return 200, f"{str(res)}"

    # 搜索书籍
    def search_book(self, store_id, title, author, intro, content, tags, page, per_page):
        try:
            query = self.conn.query(store.BookDetail)

            # 构建查询条件
            conditions = []
            if store_id:
                row = self.conn.query(store.UserStore).filter_by(store_id=store_id).first()
                if row is None:
                    return error.error_non_exist_store_id(store_id)
                # 当前店铺搜索，符合条件的书籍的book_id需要在当前店铺的所有书籍中存在
                conditions.append(store.StoreTable.store_id == store_id)
                conditions.append(store.BookDetail.book_id == store.StoreTable.book_id)
            if title:
                conditions.append(store.BookDetail.title.ilike(f"%{title}%"))
            if author:
                conditions.append(store.BookDetail.author.ilike(f"%{author}%"))
            if intro:
                conditions.append(store.BookDetail.book_intro.ilike(f"%{intro}%"))
            if content:
                conditions.append(store.BookDetail.content.ilike(f"%{content}%"))
            if tags:
                conditions.append(store.BookDetail.tags.ilike(f"%{tags}%"))

            # 应用查询条件
            if conditions:
                query = query.join(store.StoreTable, and_(*conditions))
            query = query.with_entities(store.BookDetail)
            results = query.all()
            num_results = len(results)
            if num_results == 0:
                return error.error_non_search_result()

            results = self.paging(results, page, per_page, num_results)

            res = []
            for result in results:
                res.append((
                    f"Book ID: {result.book_id}\n"
                    f"Title: {result.title}\n"
                    f"Author: {result.author}\n"
                    f"Book Intro: {result.book_intro}\n"
                    f"Content: {result.content}\n"
                    f"Tags: {result.tags}\n"
                ))

            self.conn.commit()

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, f"{str(res)}"

    # 分页
    def paging(self, results, page, per_page, num_results):
        if num_results > per_page:
            start = (page - 1) * per_page
            end = start + per_page
            if end > num_results:
                results = results[-per_page:]
            else:
                results = results[start:end]

        return results
