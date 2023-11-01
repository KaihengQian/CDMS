import logging
import pymongo
import pymongo.errors


class Store:
    database: str

    def __init__(self):
        self.database = "be"
        self.user_col = None
        self.user_store_col = None
        self.store_col = None
        self.new_order_col = None
        self.new_order_detail_col = None
        self.init_collections()

    def init_collections(self):
        try:
            conn = self.get_db_conn()
            self.user_col = conn["user"]
            self.user_col.create_index([("user_id", pymongo.TEXT)], unique=True)
            self.user_store_col = conn["user_store"]
            self.store_col = conn["store"]
            self.new_order_col = conn["new_order"]
            self.new_order_detail_col = conn["new_order_detail"]
        except pymongo.errors.PyMongoError as e:
            logging.error(e)

    def get_db_conn(self):
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        return client[self.database]


database_instance: Store = None


def init_database():
    global database_instance
    database_instance = Store()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
