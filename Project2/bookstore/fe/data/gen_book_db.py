import sqlite3


# 连接到本地sqlite数据库
sqlite_connection1 = sqlite3.connect('book.db')
sqlite_cursor1 = sqlite_connection1.cursor()
sqlite_connection2 = sqlite3.connect('book_lx.db')
sqlite_cursor2 = sqlite_connection2.cursor()

sqlite_cursor2.execute("SELECT * FROM book LIMIT 100")
rows_to_insert = sqlite_cursor2.fetchall()

for row in rows_to_insert:
    insert_sql = "INSERT INTO book VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    sqlite_cursor1.execute(insert_sql, row)

sqlite_connection1.commit()
sqlite_connection1.close()
sqlite_connection2.close()
