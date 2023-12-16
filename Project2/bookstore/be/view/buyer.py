from flask import Blueprint
from flask import request
from flask import jsonify
from be.model.buyer import Buyer

bp_buyer = Blueprint("buyer", __name__, url_prefix="/buyer")


@bp_buyer.route("/new_order", methods=["POST"])
def new_order():
    user_id: str = request.json.get("user_id")
    store_id: str = request.json.get("store_id")
    books: [] = request.json.get("books")
    id_and_count = []
    for book in books:
        book_id = book.get("id")
        count = book.get("count")
        id_and_count.append((book_id, count))

    b = Buyer()
    code, message, order_id = b.new_order(user_id, store_id, id_and_count)
    return jsonify({"message": message, "order_id": order_id}), code


@bp_buyer.route("/payment", methods=["POST"])
def payment():
    user_id: str = request.json.get("user_id")
    order_id: str = request.json.get("order_id")
    password: str = request.json.get("password")
    b = Buyer()
    code, message = b.payment(user_id, password, order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/add_funds", methods=["POST"])
def add_funds():
    user_id = request.json.get("user_id")
    password = request.json.get("password")
    add_value = request.json.get("add_value")
    b = Buyer()
    code, message = b.add_funds(user_id, password, add_value)
    return jsonify({"message": message}), code


@bp_buyer.route("/receive_book", methods=["POST"])
def receive_book():
    user_id = request.json.get("user_id")
    order_id = request.json.get("order_id")
    b = Buyer()
    code, message = b.receive_book(user_id, order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/buyer_cancel_order", methods=["POST"])
def cancel_order():
    user_id = request.json.get("user_id")
    order_id = request.json.get("order_id")
    b = Buyer()
    code, message = b.buyer_cancel_order(user_id, order_id)
    return jsonify({"message": message}), code


@bp_buyer.route("/overtime_cancel_order", methods=["POST"])
def overtime_cancel_order():
    b = Buyer()
    code, message = b.overtime_cancel_order()
    return jsonify({"message": message}), code


@bp_buyer.route("/search_book", methods=["POST"])
def search_book():
    store_id = request.json.get("store_id")
    title = request.json.get("title")
    author = request.json.get("author")
    book_intro = request.json.get("book_intro")
    content = request.json.get("content")
    tags = request.json.get("tags")

    # 分页参数
    page = int(request.args.get("page", 1))  # 当前选中页面数
    per_page = int(request.args.get("per_page", 3))  # 每页显示的条目数，默认为3

    b = Buyer()
    code, message = b.search_book(store_id, title, author, book_intro, content, tags, page, per_page)
    return jsonify({"message": message}), code


@bp_buyer.route("/search_history_order", methods=["POST"])
def search_history_order():
    user_id = request.json.get("user_id")
    order_id = request.json.get("order_id")

    # 分页参数
    page = int(request.args.get("page", 1))  # 当前选中页面数
    per_page = int(request.args.get("per_page", 3))  # 每页显示的条目数，默认为3

    b = Buyer()
    code, message = b.search_history_order(user_id, order_id, page, per_page)
    return jsonify({"message": message}), code
