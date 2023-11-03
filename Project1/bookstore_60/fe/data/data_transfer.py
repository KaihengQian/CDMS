import pymongo
import sqlite3
from pymongo import MongoClient


# 连接到本地sqlite数据库
sqlite_connection1 = sqlite3.connect('book.db')
sqlite_cursor1 = sqlite_connection1.cursor()
sqlite_connection2 = sqlite3.connect('book_lx.db')
sqlite_cursor2 = sqlite_connection2.cursor()

# 连接到本地MongoDB数据库
mongo_client = MongoClient('localhost', 27017)

mongo_db1 = mongo_client['book']
mongo_db2 = mongo_client['book_lx']

mongo_col1 = mongo_db1['book']
mongo_col2 = mongo_db2['book']

# 转存book.db
sqlite_cursor1.execute('SELECT * FROM book')
count1 = 0
for row in sqlite_cursor1.fetchall():
    book_data = {
        "id": row[0],
        "title": row[1],
        "author": row[2],
        "publisher": row[3],
        "original_title": row[4],
        "translator": row[5],
        "pub_year": row[6],
        "pages": row[7],
        "price": row[8],
        "currency_unit": row[9],
        "binding": row[10],
        "isbn": row[11],
        "author_intro": row[12],
        "book_intro": row[13],
        "content": row[14],
        "tags": row[15],
        "pictures": row[16]
    }
    res1 = mongo_col1.insert_one(book_data)
    if res1.inserted_id:
        count1 += 1

print(f"Number of inserted data: {count1}")
sqlite_connection1.close()

# 转存book_lx.db
sqlite_cursor2.execute('SELECT * FROM book')
count2 = 0
for row in sqlite_cursor2.fetchall():
    book_data = {
        "id": row[0],
        "title": row[1],
        "author": row[2],
        "publisher": row[3],
        "original_title": row[4],
        "translator": row[5],
        "pub_year": row[6],
        "pages": row[7],
        "price": row[8],
        "currency_unit": row[9],
        "binding": row[10],
        "isbn": row[11],
        "author_intro": row[12],
        "book_intro": row[13],
        "content": row[14],
        "tags": row[15],
        "pictures": row[16]
    }
    res2 = mongo_col2.insert_one(book_data)
    if res2.inserted_id:
        count2 += 1

print(f"Number of inserted data: {count2}")
sqlite_connection2.close()
