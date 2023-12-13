import logging
from sqlalchemy import Column, String, create_engine, Integer, ForeignKey
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
