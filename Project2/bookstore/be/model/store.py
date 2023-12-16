import logging
from sqlalchemy import Column, String, create_engine, Integer, ForeignKey, Boolean, JSON, ARRAY, TIMESTAMP
from sqlalchemy.orm import sessionmaker, declarative_base


Base = declarative_base()


# 定义User对象
class User(Base):
    __tablename__ = 'user'
    user_id = Column(String, primary_key=True, unique=True, nullable=False)
    password = Column(String, nullable=False)
    balance = Column(Integer, nullable=False)
    token = Column(String)
    terminal = Column(String)


# 定义Store对象
class StoreTable(Base):
    __tablename__ = 'store'
    store_id = Column(String, primary_key=True, nullable=False)
    book_id = Column(String, primary_key=True, nullable=False)
    book_info = Column(String)
    stock_level = Column(Integer)


# 定义UserStore对象
class UserStore(Base):
    __tablename__ = 'user_store'
    user_id = Column(String, ForeignKey('user.user_id'), primary_key=True, nullable=False)
    store_id = Column(String, primary_key=True, nullable=False)


# 定义NewOrder对象
class NewOrder(Base):
    __tablename__ = 'new_order'
    order_id = Column(String, primary_key=True, unique=True, nullable=False)
    user_id = Column(String, ForeignKey('user.user_id'))
    store_id = Column(String)


# 定义NewOrderDetail对象
class NewOrderDetail(Base):
    __tablename__ = 'new_order_detail'
    order_id = Column(String, primary_key=True, nullable=False)
    book_id = Column(String, primary_key=True, nullable=False)
    count = Column(Integer)
    price = Column(Integer)


# 定义HistoryOrder对象
class HistoryOrder(Base):
    __tablename__ = 'history_order'
    order_id = Column(String, primary_key=True, unique=True, nullable=False)
    user_id = Column(String, primary_key=True, nullable=False)
    store_id = Column(String)
    create_time = Column(TIMESTAMP)
    book_info = Column(ARRAY(JSON))
    is_cancelled = Column(Boolean)
    is_paid = Column(Boolean)
    is_delivered = Column(Boolean)
    is_received = Column(Boolean)


# 定义BookDetail对象
class BookDetail(Base):
    __tablename__ = 'book_detail'
    book_id = Column(String, primary_key=True, unique=True, nullable=False)
    title = Column(String)
    author = Column(String)
    book_intro = Column(String)
    content = Column(String)
    tags = Column(String)


class Store:
    database: str

    def __init__(self):
        self.engine = create_engine('postgresql://postgres:qkh123456@localhost:5432/postgres', echo=True, pool_size=8,
                                    pool_recycle=60*30)
        self.init_tables()

    def init_tables(self):
        try:
            Base.metadata.create_all(self.engine)
        except Exception as e:
            logging.error(e)

    def get_db_conn(self):
        DbSession = sessionmaker(bind=self.engine)
        session = DbSession()
        return session


database_instance: Store = None


def init_database():
    global database_instance
    database_instance = Store()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
