import logging
import pymongo
import pymongo.errors


class Store:
    database: str

    def __init__(self):
        self.client = pymongo.MongoClient("mongodb://localhost:27017/")
        self.database = "be"
        self.db = self.client.get_database(self.database)
        self.user_col = None
        self.user_store_col = None
        self.store_col = None
        self.new_order_col = None
        self.new_order_detail_col = None
        self.init_collections()

    def init_collections(self):
        try:
            self.user_col = self.db.create_collection("user")
            self.user_col.create_index([("user_id", 1)], unique=True)

            self.user_store_col = self.db.create_collection("user_store")
            self.user_col.create_index([("user_id", 1), ("store_id", 1)], unique=True)

            self.store_col = self.db.create_collection("store")
            self.user_col.create_index([("store_id", 1), ("book_id", 1)], unique=True)

            self.new_order_col = self.db.create_collection("new_order")
            self.user_col.create_index([("order_id", 1)], unique=True)

            self.new_order_detail_col = self.db.create_collection("new_order_detail")
            self.user_col.create_index([("order_id", 1), ("book_id", 1)], unique=True)

        except Exception as e:
            logging.error(e)

    def get_db_conn(self):
        return self.db


database_instance: Store = None


def init_database():
    global database_instance
    database_instance = Store()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
