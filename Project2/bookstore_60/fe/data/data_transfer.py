import sqlite3
from sqlalchemy import Column, String, create_engine, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


# 连接到本地SQLite数据库
sqlite_connection1 = sqlite3.connect('book.db')
sqlite_cursor1 = sqlite_connection1.cursor()
sqlite_connection2 = sqlite3.connect('book_lx.db')
sqlite_cursor2 = sqlite_connection2.cursor()

# 连接到本地PostgreSQL数据库
engine = create_engine('postgresql://postgres:qkh123456@localhost:5432/postgres', echo=True, pool_size=8, pool_recycle=60*30)

# 创建session
DbSession = sessionmaker(bind=engine)
session = DbSession()

# 定义基类
Base = declarative_base()


# 定义Book对象
class Book(Base):
    __tablename__ = 'book'
    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    title = Column(String, nullable=False)
    author = Column(String)
    publisher = Column(String)
    original_title = Column(String)
    translator = Column(String)
    pub_year = Column(String)
    pages = Column(Integer)
    price = Column(Integer, nullable=False)
    currency_unit = Column(String)
    binding = Column(String)
    isbn = Column(String)
    author_intro = Column(String)
    book_intro = Column(String)
    content = Column(String)
    tags = Column(String)


# 定义Book对象
class Book_lx(Base):
    __tablename__ = 'book_lx'
    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    title = Column(String, nullable=False)
    author = Column(String)
    publisher = Column(String)
    original_title = Column(String)
    translator = Column(String)
    pub_year = Column(String)
    pages = Column(Integer)
    price = Column(Integer, nullable=False)
    currency_unit = Column(String)
    binding = Column(String)
    isbn = Column(String)
    author_intro = Column(String)
    book_intro = Column(String)
    content = Column(String)
    tags = Column(String)


# 在PostgreSQL中创建表（如果不存在）
Base.metadata.create_all(engine)

# 从SQLite数据库中获取数据
data1 = sqlite_cursor1.execute('SELECT * FROM book').fetchall()
data2 = sqlite_cursor2.execute('SELECT * FROM book').fetchall()

# 将数据插入到PostgreSQL数据库
count1 = 0
for row in data1:
    book_entry = Book(id=row[0], title=row[1], author=row[2], publisher=row[3], original_title=row[4], translator=row[5],
                      pub_year=row[6], pages=row[7], price=row[8], currency_unit=row[9], binding=row[10], isbn=row[11],
                      author_intro=row[12], book_intro=row[13], content=row[14], tags=row[15])
    session.add(book_entry)
    count1 += 1
print(f"Number of inserted data: {count1}")
count2 = 0
for row in data2:
    book_lx_entry = Book_lx(id=row[0], title=row[1], author=row[2], publisher=row[3], original_title=row[4],
                            translator=row[5], pub_year=row[6], pages=row[7], price=row[8], currency_unit=row[9],
                            binding=row[10], isbn=row[11], author_intro=row[12], book_intro=row[13], content=row[14],
                            tags=row[15])
    session.add(book_lx_entry)
    count2 += 1
print(f"Number of inserted data: {count2}")

session.commit()

sqlite_connection1.close()
sqlite_connection2.close()
