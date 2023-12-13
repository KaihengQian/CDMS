import pytest

from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
import uuid


class TestSearchBook:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.seller_id = "test_search_book_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_search_book_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_search_book_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.password)
        gen_book = GenBook(self.seller_id, self.store_id)
        ok, buy_book_id_list = gen_book.gen(
            non_exist_book_id=False, low_stock_level=False, max_book_count=5
        )
        self.buy_book_info_list = gen_book.buy_book_info_list
        assert ok
        yield

    def test_ok(self):
        code = self.buyer.search_book(store_id=self.store_id, title="", author="", book_intro="", content="", tags=[])
        assert code == 200

    def test_non_search_result(self):
        code = self.buyer.search_book(store_id="", title="", author="三毛_x", book_intro="", content="", tags=[])
        assert code != 200

    def test_non_exist_store_id(self):
        code = self.buyer.search_book(store_id=self.store_id + "_x", title="", author="三毛", book_intro="", content="", tags=[])
        assert code != 200
