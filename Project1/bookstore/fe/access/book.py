import pymongo
import random
import base64
import simplejson as json


class Book:
    id: str
    title: str
    author: str
    publisher: str
    original_title: str
    translator: str
    pub_year: str
    pages: int
    price: int
    binding: str
    isbn: str
    author_intro: str
    book_intro: str
    content: str
    tags: [str]
    pictures: [bytes]

    def __init__(self):
        self.tags = []
        self.pictures = []


class BookDB:
    def __init__(self, large: bool = True):
        self.db_s = "book"
        self.db_l = "book_lx"
        if large:
            self.book_db = self.db_l
        else:
            self.book_db = self.db_s

    def get_book_count(self):
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        conn = client[self.book_db]
        book_col = conn["book"]
        row = book_col.count_documents({"id": {"$exists": True}})
        return row

    def get_book_info(self, start, size) -> [Book]:
        books = []
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        conn = client[self.book_db]
        rows = conn.find().sort([("id", 1)]).limit(size).skip(start)
        for row in rows:
            book = Book()
            book.id = row.get("id")
            book.title = row.get("title")
            book.author = row.get("author")
            book.publisher = row.get("publisher")
            book.original_title = row.get("original_title")
            book.translator = row.get("translator")
            book.pub_year = row.get("pub_year")
            book.pages = row.get("pages")
            book.price = row.get("price")

            book.currency_unit = row.get("currency_unit")
            book.binding = row.get("binding")
            book.isbn = row.get("isbn")
            book.author_intro = row.get("author_intro")
            book.book_intro = row.get("book_intro")
            book.content = row.get("content")
            tags = row.get("tags")

            picture = row.get("picture")

            for tag in tags.split("\n"):
                if tag.strip() != "":
                    book.tags.append(tag)
            for i in range(0, random.randint(0, 9)):
                if picture is not None:
                    encode_str = base64.b64encode(picture).decode("utf-8")
                    book.pictures.append(encode_str)
            books.append(book)
            # print(tags.decode('utf-8'))

            # print(book.tags, len(book.picture))
            # print(book)
            # print(tags)

        return books
