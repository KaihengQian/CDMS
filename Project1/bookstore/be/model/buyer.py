import re
import jieba
from pymongo.errors import ConnectionFailure, OperationFailure
import uuid
import json
import logging
from be.model import db_conn
from be.model import error
from datetime import datetime


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

            book_info_list = []  # 储存历史订单中的书籍购买信息

            store_col = self.db.get_collection("store")
            for book_id, count in id_and_count:
                book_info = store_col.find_one({"store_id": store_id, "book_id": book_id})
                if book_info is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = book_info["stock_level"]
                book_info = json.loads(book_info["book_info"])
                price = book_info["price"]

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
                "order_id": uid,
                "store_id": store_id,
                "user_id": user_id
            })

            # 加入历史订单
            history_order_col = self.db.get_collection("history_order")
            history_order_col.insert_one({
                "order_id": uid,
                "store_id": store_id,
                "user_id": user_id,
                "book_info": book_info_list,
                "is_cancelled": False,
                "is_paid": False,
                "is_delivered": False,
                "is_received": False
            })

            order_id = uid

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

    # 收货
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

            # 更新历史订单状态为已收货
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

    # 买家主动取消订单
    def buyer_cancel_order(self, user_id: str, order_id: str):
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
            # 订单状态为已支付时无法取消订单
            is_paid = order.get("is_paid")
            if is_paid:
                return error.error_order_cancellation_fail(order_id)

            self.cancel_order(history_order_col, order, order_id)

        except ConnectionFailure as cf:
            logging.info(f"528 Connection failed: {str(cf)}")
            return 528, f"{str(cf)}", ""
        except OperationFailure as of:
            logging.info(f"528 Operation failed: {str(of)}")
            return 528, f"{str(of)}", ""
        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok, order cancelled"

    # 超时自动取消订单
    def overtime_cancel_order(self):
        try:
            living_time = 15 * 60  # 未支付订单最长保留时间

            # 检查所有历史订单
            history_order_col = self.db.get_collection("history_order")
            orders = history_order_col.find({})
            num_orders = sum(1 for _ in orders)
            if num_orders == 0:
                return 200, "ok"

            num_cancelled = 0  # 记录取消订单数量

            for order in orders:
                order_id = order.get("order_id")
                is_cancelled = order.get("is_cancelled")
                is_paid = order.get("is_paid")
                if is_cancelled or is_paid:
                    continue

                # 获取 UUID 时间戳
                parts = order_id.split("_")
                uid_time = parts[2]
                # 转换 UUID 时间戳为可读的时间格式
                uuid_time = datetime.fromtimestamp(uuid.UUID(uid_time).time / 1e7 - 12219292800)
                # 计算时间差
                current_time = datetime.now()
                time_passed = (current_time - uuid_time).total_seconds()
                if time_passed > living_time:
                    self.cancel_order(history_order_col, order, order_id)
                    num_cancelled += 1

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

        return 200, "ok, {} orders cancelled".format(num_cancelled)

    def cancel_order(self, history_order_col, order, order_id):
        # 更新历史订单状态为已取消
        condition = {'order_id': order_id}
        update_data = {'$set': {'is_cancelled': True}}
        history_order_col.update_one(condition, update_data)

        # 还原书籍库存
        store_col = self.db.get_collection("store")
        store_id = order.get("store_id")
        book_info_list = order.get("book_info")
        for book_info in book_info_list:
            book_id = book_info.get("book_id")
            count = book_info.get("count")
            store_col.update_one(
                {"store_id": store_id, "book_id": book_id},
                {"$inc": {"stock_level": count}}
            )

        # 删除new_order和new_order_detail中的相关文档
        new_order_col = self.db.get_collection("new_order")
        order_del_res = new_order_col.delete_one({"order_id": order_id})

        if order_del_res.deleted_count == 0:
            return error.error_invalid_order_id(order_id)

        new_order_detail_col = self.db.get_collection("new_order_detail")
        order_detail_del_res = new_order_detail_col.delete_many({"order_id": order_id})

        if order_detail_del_res.deleted_count == 0:
            return error.error_invalid_order_id(order_id)

    # 搜索历史订单
    def search_history_order(self, user_id, order_id, page, per_page):
        try:
            user_col = self.db.get_collection("user")
            user = user_col.find_one({"user_id": user_id})

            if user is None:
                return error.error_authorization_fail()

            order_col = self.db.get_collection("history_order")
            if order_id == "":
                order = order_col.find({"user_id": user_id}, {"_id": 0})

                num_col = sum(1 for _ in order)
                if num_col == 0:
                    return error.error_non_history_order(user_id)

                res = self.paging(order, page, per_page, num_col)

            else:
                order = order_col.find_one({"order_id": order_id, "user_id": user_id}, {"_id": 0})

                if order is None:
                    return error.error_non_history_order(user_id)

                res = order

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}"

        print(1)
        return 200, f"{str(res)}"

    # 搜索书籍
    def search_book(self, store_id, title, author, intro, content, tags, page, per_page):
        try:
            book_detail_col = self.db.get_collection("book_detail")
            find_condition = {}  # 搜索条件

            # 当前店铺搜索
            if store_id != "":
                # 符合条件的书籍的book_id需要在当前店铺的所有书籍中存在，进行第一步筛选
                store_col = self.db.get_collection("store")
                book_ids = store_col.find({"store_id": store_id})
                num_book_ids = sum(1 for _ in book_ids)
                if num_book_ids == 0:
                    return error.error_non_exist_store_id(store_id)
                book_id_store = []
                book_ids.rewind()
                for book in book_ids:
                    book_id_store.append(book["book_id"])
                find_condition["book_id"] = {"$in": book_id_store}
                print(book_id_store)

                # 根据作者和标签信息进行第二步筛选
                if author != "":
                    find_condition["author"] = author
                if tags:
                    find_condition["tags"] = {"$in": tags}
                print(find_condition)
                book1 = book_detail_col.find(find_condition, {"_id": 0, "description": 0})
                book_id = []
                for book in book1:
                    book_id.append(book["book_id"])
                print(book_id)

                # 根据文本信息（标题、内容、目录）进行第三步筛选
                search_des = ""
                if title != "":
                    search_des += title
                if content != "":
                    search_des += content
                if intro != "":
                    search_des += intro

                if search_des != "":
                    des_words = self.split_words(search_des)
                    res_id = []
                    for word in des_words:
                        books = book_detail_col.find({"book_id": {"$in": book_id}, "$text": {"$search": word}},
                                                     {"_id": 0, "book_id": 1})
                        if books is not None:
                            for book in books:
                                res_id.append(book["book_id"])

                    res_id = list(set(res_id))
                    if len(res_id) != 0:
                        book_info = book_detail_col.find({"book_id": {"$in": res_id}}, {"_id": 0, "description": 0})
                    else:
                        return error.error_non_search_result()

                    num_col = sum(1 for _ in book_info)
                    if num_col == 0:
                        return error.error_non_search_result()

                    res = self.paging(book_info, page, per_page, num_col)

                else:
                    book1.rewind()
                    num_col = sum(1 for _ in book1)
                    if num_col == 0:
                        return error.error_non_search_result()

                    res = self.paging(book1, page, per_page, num_col)

                return 200, f"{str(res)}"
            # 全站搜索
            else:
                # 根据作者和标签信息进行第一步筛选
                if author != "":
                    find_condition["author"] = author
                if tags:
                    find_condition["tags"] = {"$in": tags}
                book1 = book_detail_col.find(find_condition, {"_id": 0, "description": 0})
                book_id = []
                for book in book1:
                    book_id.append(book["book_id"])

                # 根据文本信息（标题、内容、目录）进行第二步筛选
                search_des = ""
                if title != "":
                    search_des += title
                if content != "":
                    search_des += content
                if intro != "":
                    search_des += intro

                if search_des != "":
                    des_words = self.split_words(search_des)
                    res_id = []
                    for word in des_words:
                        books = book_detail_col.find({"book_id": {"$in": book_id}, "$text": {"$search": word}},
                                                     {"_id": 0, "book_id": 1})
                        if books is not None:
                            for book in books:
                                res_id.append(book["book_id"])

                    res_id = list(set(res_id))
                    if len(res_id) != 0:
                        book_info = book_detail_col.find({"book_id": {"$in": res_id}}, {"_id": 0, "description": 0})
                    else:
                        return error.error_non_search_result()

                    num_col = sum(1 for _ in book_info)
                    if num_col == 0:
                        return error.error_non_search_result()

                    res = self.paging(book_info, page, per_page, num_col)

                else:
                    book1.rewind()
                    num_col = sum(1 for _ in book1)
                    if num_col == 0:
                        return error.error_non_search_result()

                    res = self.paging(book1, page, per_page, num_col)

                return 200, f"{str(res)}"

        except Exception as e:
            logging.info(f"530, {str(e)}")
            return 530, f"{str(e)}", ""

    # 分词
    def split_words(self, text):
        words = re.sub(r'[^\w\s\n]', '', text)
        words = re.sub(r'\n', '', words)
        res = jieba.cut(words, cut_all=False)
        res_list = []
        for word in res:
            res_list.append(word)
        res_list = list(set(res_list))
        return res_list

    # 分页
    def paging(self, cursor, page, per_page, num_col):
        cursor.rewind()
        res = list(cursor)
        if num_col > per_page:
            start = (page - 1) * per_page
            end = start + per_page
            if end > num_col:
                res = res[-per_page:]
            else:
                res = res[start:end]

        return res
