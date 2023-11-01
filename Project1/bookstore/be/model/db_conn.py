from be.model import store


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        user_col = self.conn["user"]
        row = user_col.find_one({'user_id': user_id}, {'_id': 0, 'user_id': 1})
        if row is None:
            return False
        else:
            return True

    def book_id_exist(self, store_id, book_id):
        store_col = self.conn["store"]
        row = store_col.find_one({'store_id': store_id, 'book_id': book_id}, {'_id': 0, 'book_id': 1})
        if row is None:
            return False
        else:
            return True

    def store_id_exist(self, store_id):
        user_store_col = self.conn["user_store"]
        row = user_store_col.find_one({'store_id': store_id}, {'_id': 0, 'store_id': 1})
        if row is None:
            return False
        else:
            return True
