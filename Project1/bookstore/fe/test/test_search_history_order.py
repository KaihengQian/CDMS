import pytest

from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
import uuid


class TestSearchHistoryOrder:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.buyer_id = "test_search_history_order_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.password)
        yield

    def test_ok(self):
        for _ in range(3):
            self.seller_id = "test_search_history_order_seller_id_{}".format(str(uuid.uuid1()))
            self.store_id = "test_search_history_order_store_id_{}".format(str(uuid.uuid1()))
            gen_book = GenBook(self.seller_id, self.store_id)
            ok, buy_book_id_list = gen_book.gen(
                non_exist_book_id=False, low_stock_level=False, max_book_count=5
            )
            self.buy_book_info_list = gen_book.buy_book_info_list
            assert ok
            code, _ = self.buyer.new_order(self.store_id, buy_book_id_list)
            assert code == 200

        code, _ = self.buyer.search_history_order(order_id="")
        assert code == 200

    def test_non_history_order(self):
        code, _ = self.buyer.search_history_order(order_id="")
        assert code != 200

    def test_non_exist_user_id(self):
        for _ in range(3):
            self.seller_id = "test_search_history_order_seller_id_{}".format(str(uuid.uuid1()))
            self.store_id = "test_search_history_order_store_id_{}".format(str(uuid.uuid1()))
            gen_book = GenBook(self.seller_id, self.store_id)
            ok, buy_book_id_list = gen_book.gen(
                non_exist_book_id=False, low_stock_level=False, max_book_count=5
            )
            self.buy_book_info_list = gen_book.buy_book_info_list
            assert ok
            code, _ = self.buyer.new_order(self.store_id, buy_book_id_list)
            assert code == 200

        self.buyer.user_id = self.buyer.user_id + "_x"
        code, _ = self.buyer.search_history_order(order_id="")
        assert code != 200
