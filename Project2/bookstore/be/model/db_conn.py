from be.model import store


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        row = self.conn.query(store.User).filter(store.User.user_id == user_id).first()
        if row is None:
            return False
        else:
            return True

    def book_id_exist(self, store_id, book_id):
        row = self.conn.query(store.StoreTable).filter(store.StoreTable.store_id == store_id and
                                                       store.StoreTable.book_id == book_id).first()
        if row is None:
            return False
        else:
            return True

    def store_id_exist(self, store_id):
        row = self.conn.query(store.UserStore).filter(store.UserStore.store_id == store_id).first()
        if row is None:
            return False
        else:
            return True
