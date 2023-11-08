import pytest
from fe import conf
from fe.access import seller
from fe.access.seller import Seller
from fe.access.buyer import Buyer
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
from fe.access.book import Book
import uuid


class TestDeliverBook:
    seller_id: str
    store_id: str
    buyer_id: str
    password: str
    buy_book_info_list: [Book]
    total_price: int
    order_id: str
    seller: Seller
    buyer: Buyer

    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.seller_id = "test_deliver_book_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_deliver_book_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_deliver_book_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id
        gen_book = GenBook(self.seller_id, self.store_id)
        ok, buy_book_id_list = gen_book.gen(
            non_exist_book_id=False, low_stock_level=False, max_book_count=5
        )
        self.buy_book_info_list = gen_book.buy_book_info_list
        assert ok
        s = seller.Seller(conf.URL, self.seller_id, self.password)
        self.seller = s
        b = register_new_buyer(self.buyer_id, self.password)
        self.buyer = b
        code, self.order_id = b.new_order(self.store_id, buy_book_id_list)
        assert code == 200
        self.total_price = 0
        for item in self.buy_book_info_list:
            book: Book = item[0]
            num = item[1]
            if book.price is None:
                continue
            else:
                self.total_price = self.total_price + book.price * num
        yield

    def test_ok(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200

        code = self.seller.deliver_book(self.seller.seller_id, self.store_id, self.order_id)
        assert code == 200

    def test_error_non_exist_user_id(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200

        # non exist user id
        code = self.seller.deliver_book(self.seller.seller_id + "_x", self.store_id, self.order_id)
        assert code != 200

    def test_error_non_exist_store_id(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200

        # non exist store id
        code = self.seller.deliver_book(self.seller.seller_id, self.store_id + "x", self.order_id)
        assert code != 200

    def test_invalid_order_id(self):
        code = self.buyer.add_funds(self.total_price)
        assert code == 200
        code = self.buyer.payment(self.order_id)
        assert code == 200

        code = self.seller.deliver_book(self.seller.seller_id, self.store_id, self.order_id + "x")
        assert code != 200

    def test_cancelled_order(self):
        code = self.buyer.buyer_cancel_order(self.order_id)
        assert code == 200

        code = self.seller.deliver_book(self.seller.seller_id, self.store_id, self.order_id)
        assert code != 200

    def test_not_paid_order(self):
        code = self.seller.deliver_book(self.seller.seller_id, self.store_id, self.order_id)
        assert code != 200
