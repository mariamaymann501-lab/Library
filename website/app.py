from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import bcrypt
import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from werkzeug.exceptions import RequestEntityTooLarge

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path, override=True)

print("ENV PATH:", env_path)
print("ENV EXISTS:", env_path.is_file())
print("DB USER:", os.getenv("DB_USER"))
print("PASSWORD LOADED:", bool(os.getenv("DB_PASSWORD")))

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY") or os.urandom(24).hex()

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "library")
    )


UPLOAD_ROOT = Path(__file__).resolve().parent / "static" / "uploads"
UPLOAD_FOLDERS = {"books": UPLOAD_ROOT / "books", "authors": UPLOAD_ROOT / "authors"}
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  

for _folder in UPLOAD_FOLDERS.values():
    _folder.mkdir(parents=True, exist_ok=True)


def ensure_image_columns():
    """Add the image_filename column to BOOK and AUTHOR if it is missing.

    This keeps problem2_DDL.sql unchanged: after you run the DDL + DML, the
    website adds the new column by itself (same as problem2_bonus_images.sql).
    """
    db = get_db()
    cur = db.cursor()
    try:
        for table in ("BOOK", "AUTHOR"):
            cur.execute(f"SHOW COLUMNS FROM {table} LIKE 'image_filename'")
            if not cur.fetchall():
                cur.execute(f"ALTER TABLE {table} ADD COLUMN image_filename VARCHAR(255) NULL")
        db.commit()
    finally:
        cur.close()
        db.close()


def ensure_schema():
    """Make sure the extra tables/columns the website needs exist.

    problem2_DDL.sql drops and re-creates the whole database, which also removes
    the `users` table (login) and the image columns. Instead of making you run
    problem2_users.sql every time, the website re-creates them by itself.
    """
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   user_id INT NOT NULL AUTO_INCREMENT,
                   email VARCHAR(255) NOT NULL,
                   name VARCHAR(100) NOT NULL,
                   password_hash VARCHAR(255) NOT NULL,
                   registration_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   PRIMARY KEY (user_id),
                   UNIQUE (email)
               )"""
        )
        db.commit()
    finally:
        cur.close()
        db.close()
    ensure_image_columns()


try:
    ensure_schema()
except Exception as error: 
    print("Could not check the database tables:", error)


def looks_like_image(header):
    """Check the first bytes of the file, not only its extension."""
    return (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith(b"\xff\xd8\xff")
        or header.startswith(b"GIF87a")
        or header.startswith(b"GIF89a")
        or (header[:4] == b"RIFF" and header[8:12] == b"WEBP")
    )


def save_image(upload, kind):
    """Save an uploaded image. Returns (file_name, error_message)."""
    extension = os.path.splitext(upload.filename)[1].lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        return None, "Image must be a PNG, JPG, GIF or WEBP file."
    if not looks_like_image(upload.stream.read(16)):
        return None, "That file is not a valid image."
    upload.stream.seek(0)
    file_name = uuid.uuid4().hex + "." + extension
    try:
        ensure_image_columns()  
    except Exception:
        pass
    upload.save(UPLOAD_FOLDERS[kind] / file_name)
    return file_name, None


def delete_image_file(file_name, kind):
    """Remove an image file from disk (does nothing if it does not exist)."""
    if file_name:
        try:
            (UPLOAD_FOLDERS[kind] / file_name).unlink()
        except OSError:
            pass


def image_names(cur, query, params):
    """Read image file names; returns [] if the image column does not exist."""
    try:
        cur.execute(query, params)
        return [row["image_filename"] for row in cur.fetchall() if row["image_filename"]]
    except mysql.connector.Error:
        return []


@app.errorhandler(RequestEntityTooLarge)
def image_too_large(error):
    flash("The image is too large. The maximum size is 5 MB.")
    return redirect(request.referrer or url_for("home"))

PUBLIC_PAGES = {"login", "register", "static"}


@app.before_request
def require_login():
    """Runs before every request: logged-out users are sent to the login page.

    This is the same check as `if "user_id" not in session` from the To-Do
    assignment, written once here instead of inside every route.
    """
    if request.endpoint != "static":
        try:
            ensure_schema()  # in case problem2_DDL.sql was re-run while the site was open
        except Exception:
            pass
    if request.endpoint in PUBLIC_PAGES:
        return None
    if "user_id" not in session:
        return redirect(url_for("login"))
    return None


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))

    errors = {}
    form = {"name": "", "email": ""}

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        form = {"name": name, "email": email}

        if not name:
            errors["name"] = "Name is required"
        elif len(name) > 100:
            errors["name"] = "Name is too long"

        if not email:
            errors["email"] = "Email is required"
        elif "@" not in email or len(email) > 255:
            errors["email"] = "Enter a valid email address"

        if not password:
            errors["password"] = "Password is required"
        elif len(password) < 8:
            errors["password"] = "Password must be at least 8 characters"

        if not confirm_password:
            errors["confirm_password"] = "Confirm password is required"
        elif password != confirm_password:
            errors["confirm_password"] = "Passwords do not match"

        if errors:
            return render_template("register.html", errors=errors, form=form)

        db = get_db()
        cur = db.cursor(dictionary=True)
        try:
            cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                errors["email"] = "Email already exists"
                return render_template("register.html", errors=errors, form=form)

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            cur.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                (email, name, password_hash),
            )
            db.commit()

            session.clear()
            session["user_id"] = cur.lastrowid
            session["name"] = name
        finally:
            cur.close()
            db.close()

        flash(f"Welcome to the library, {name}!")
        return redirect(url_for("home"))

    return render_template("register.html", errors=errors, form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    errors = {}
    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email:
            errors["email"] = "Email is required"
        if not password:
            errors["password"] = "Password is required"

        if errors:
            return render_template("login.html", errors=errors, email=email)

        db = get_db()
        cur = db.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
        finally:
            cur.close()
            db.close()

        if user and bcrypt.checkpw(
            password.encode("utf-8"), user["password_hash"].encode("utf-8")
        ):
            session.clear()
            session["user_id"] = user["user_id"]
            session["name"] = user["name"]
            flash(f"Welcome back, {user['name']}!")
            return redirect(url_for("home"))

        # Same message for wrong email and wrong password, so nobody can
        # find out which emails are registered.
        errors["general"] = "Invalid email or password"

    return render_template("login.html", errors=errors, email=email)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


# =====================================================================
# Library pages (Lab 3: add, edit and delete books and authors)
# =====================================================================

@app.route("/")
def home():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM BOOK ORDER BY book_id DESC")
    books = cur.fetchall()
    cur.execute("SELECT * FROM AUTHOR ORDER BY author_id DESC")
    authors = cur.fetchall()
    cur.execute("SELECT * FROM PUBLISHER ORDER BY name")
    publishers = cur.fetchall()
    cur.execute("SELECT * FROM CATEGORY ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    db.close()
    return render_template("index.html", books=books, authors=authors,
                           publishers=publishers, categories=categories)

@app.route("/authors/add", methods=["POST"])
def add_author():
    name = request.form.get("name", "").strip()
    country = request.form.get("country", "").strip()
    if not name or not country:
        flash("Please enter the author name and country.")
        return redirect(url_for("home"))
    photo = None
    upload = request.files.get("image")
    if upload and upload.filename:
        photo, error = save_image(upload, "authors")
        if error:
            flash(error)
            return redirect(url_for("home"))
    db = get_db()
    cur = db.cursor()
    if photo:
        cur.execute("INSERT INTO AUTHOR (name, country, image_filename) VALUES (%s, %s, %s)",
                    (name, country, photo))
    else:
        cur.execute("INSERT INTO AUTHOR (name, country) VALUES (%s, %s)", (name, country))
    db.commit()
    cur.close()
    db.close()
    flash("Author added.")
    return redirect(url_for("home"))

@app.route("/authors/edit/<int:author_id>", methods=["GET", "POST"])
def edit_author(author_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        if not name or not country:
            flash("Name and country are required.")
            cur.execute("SELECT * FROM AUTHOR WHERE author_id = %s", (author_id,))
            author = cur.fetchone()
            cur.close()
            db.close()
            return render_template("edit_author.html", author=author)
        photo = None
        upload = request.files.get("image")
        if upload and upload.filename:
            photo, error = save_image(upload, "authors")
            if error:
                flash(error)
                cur.execute("SELECT * FROM AUTHOR WHERE author_id = %s", (author_id,))
                author = cur.fetchone()
                cur.close()
                db.close()
                return render_template("edit_author.html", author=author)
        old_photos = []
        if photo or request.form.get("remove_image"):
            old_photos = image_names(cur, "SELECT image_filename FROM AUTHOR WHERE author_id = %s",
                                     (author_id,))
        cur.execute("UPDATE AUTHOR SET name=%s, country=%s WHERE author_id=%s",
                    (name, country, author_id))
        if photo:
            cur.execute("UPDATE AUTHOR SET image_filename=%s WHERE author_id=%s", (photo, author_id))
        elif request.form.get("remove_image") and old_photos:
            cur.execute("UPDATE AUTHOR SET image_filename=NULL WHERE author_id=%s", (author_id,))
        db.commit()
        if photo or request.form.get("remove_image"):
            for old in old_photos:
                if old != photo:
                    delete_image_file(old, "authors")
        cur.close()
        db.close()
        return redirect(url_for("home"))
    cur.execute("SELECT * FROM AUTHOR WHERE author_id = %s", (author_id,))
    author = cur.fetchone()
    cur.close()
    db.close()
    if not author:
        return "Author not found", 404
    return render_template("edit_author.html", author=author)

@app.route("/authors/delete/<int:author_id>", methods=["POST"])
def delete_author(author_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    author_photos = image_names(cur, "SELECT image_filename FROM AUTHOR WHERE author_id = %s",
                                (author_id,))
    book_covers = image_names(cur, "SELECT image_filename FROM BOOK WHERE author_id = %s",
                              (author_id,))
    cur.execute("DELETE FROM AUTHOR WHERE author_id = %s", (author_id,))
    db.commit()
    for name in author_photos:
        delete_image_file(name, "authors")
    for name in book_covers:
        delete_image_file(name, "books")
    cur.close()
    db.close()
    flash("Author deleted. Their books are deleted automatically.")
    return redirect(url_for("home"))

@app.route("/books/add", methods=["POST"])
def add_book():
    title = request.form.get("title", "").strip()
    price = request.form.get("price", "").strip()
    author_id = request.form.get("author_id", "").strip()
    publisher_id = request.form.get("publisher_id", "").strip()
    category_id = request.form.get("category_id", "").strip()
    publish_year = request.form.get("publish_year", "").strip()
    if not title or not price or not author_id or not publisher_id or not category_id or not publish_year:
        flash("Please fill in all book fields.")
        return redirect(url_for("home"))
    try:
        price = float(price)
        if price < 0:
            raise ValueError
        author_id = int(author_id)
        publisher_id = int(publisher_id)
        category_id = int(category_id)
        publish_year = int(publish_year)
        if not 1000 <= publish_year <= 2100:
            raise ValueError
    except ValueError:
        flash("Enter a valid non-negative price, a year (1000-2100), author, publisher and category.")
        return redirect(url_for("home"))
    cover = None
    upload = request.files.get("image")
    if upload and upload.filename:
        cover, error = save_image(upload, "books")
        if error:
            flash(error)
            return redirect(url_for("home"))
    db = get_db()
    cur = db.cursor()
    if cover:
        cur.execute("INSERT INTO BOOK (title, price, publish_year, author_id, publisher_id, category_id, image_filename) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (title, price, publish_year, author_id, publisher_id, category_id, cover))
    else:
        cur.execute("INSERT INTO BOOK (title, price, publish_year, author_id, publisher_id, category_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (title, price, publish_year, author_id, publisher_id, category_id))
    db.commit()
    cur.close()
    db.close()
    flash("Book added.")
    return redirect(url_for("home"))

def render_edit_book(db, cur, book_id):
    """Load the book, the authors, the publishers and the categories and show the edit page."""
    cur.execute("SELECT * FROM BOOK WHERE book_id=%s", (book_id,))
    book = cur.fetchone()
    cur.execute("SELECT * FROM AUTHOR ORDER BY name")
    authors = cur.fetchall()
    cur.execute("SELECT * FROM PUBLISHER ORDER BY name")
    publishers = cur.fetchall()
    cur.execute("SELECT * FROM CATEGORY ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    db.close()
    if not book:
        return "Book not found", 404
    return render_template("edit_book.html", book=book, authors=authors,
                           publishers=publishers, categories=categories)

@app.route("/books/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        price = request.form.get("price", "").strip()
        author_id = request.form.get("author_id", "").strip()
        publisher_id = request.form.get("publisher_id", "").strip()
        category_id = request.form.get("category_id", "").strip()
        publish_year = request.form.get("publish_year", "").strip()
        try:
            price = float(price)
            author_id = int(author_id)
            publisher_id = int(publisher_id)
            category_id = int(category_id)
            publish_year = int(publish_year)
            if not title or price < 0 or not 1000 <= publish_year <= 2100:
                raise ValueError
        except ValueError:
            flash("Enter a title, valid price, year (1000-2100), author, publisher and category.")
            return render_edit_book(db, cur, book_id)
        cover = None
        upload = request.files.get("image")
        if upload and upload.filename:
            cover, error = save_image(upload, "books")
            if error:
                flash(error)
                return render_edit_book(db, cur, book_id)
        old_covers = []
        if cover or request.form.get("remove_image"):
            old_covers = image_names(cur, "SELECT image_filename FROM BOOK WHERE book_id=%s",
                                     (book_id,))
        cur.execute("UPDATE BOOK SET title=%s, price=%s, publish_year=%s, author_id=%s, "
                    "publisher_id=%s, category_id=%s WHERE book_id=%s",
                    (title, price, publish_year, author_id, publisher_id, category_id, book_id))
        if cover:
            cur.execute("UPDATE BOOK SET image_filename=%s WHERE book_id=%s", (cover, book_id))
        elif request.form.get("remove_image") and old_covers:
            cur.execute("UPDATE BOOK SET image_filename=NULL WHERE book_id=%s", (book_id,))
        db.commit()
        if cover or request.form.get("remove_image"):
            for old in old_covers:
                if old != cover:
                    delete_image_file(old, "books")
        cur.close()
        db.close()
        return redirect(url_for("home"))
    return render_edit_book(db, cur, book_id)

@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    covers = image_names(cur, "SELECT image_filename FROM BOOK WHERE book_id=%s", (book_id,))
    cur.execute("DELETE FROM BOOK WHERE book_id=%s", (book_id,))
    db.commit() 
    for name in covers:
        delete_image_file(name, "books")
    cur.close()
    db.close()
    flash("Book deleted.")
    return redirect(url_for("home"))

# F2.1  Search books (WHERE: LIKE + BETWEEN + category), cheapest first.

SEARCH_BOOKS_SQL = """
SELECT b.book_id, b.title, b.price, b.publish_year, c.name AS category
FROM BOOK b
JOIN CATEGORY c ON b.category_id = c.category_id
WHERE b.title LIKE %s
  AND b.price BETWEEN %s AND %s
  AND (%s IS NULL OR b.category_id = %s)
ORDER BY b.price ASC, b.title ASC
"""

# F2.2  Catalogue (JOIN)
CATALOGUE_SQL = """
SELECT b.book_id, b.title, b.price, b.publish_year, a.name AS author, p.name AS publisher, c.name AS category
FROM BOOK b
JOIN AUTHOR a ON b.author_id = a.author_id
JOIN PUBLISHER p ON b.publisher_id = p.publisher_id
JOIN CATEGORY c ON b.category_id = c.category_id
ORDER BY b.book_id
"""

# F2.3  Reports (GROUP BY, HAVING)
CATEGORY_REPORT_SQL = """
SELECT c.name AS category, COUNT(b.book_id) AS books, ROUND(AVG(b.price), 2) AS average_price
FROM CATEGORY c
LEFT JOIN BOOK b ON b.category_id = c.category_id
GROUP BY c.category_id, c.name
ORDER BY c.name
"""
PROLIFIC_AUTHORS_SQL = """
SELECT a.author_id, a.name, COUNT(*) AS books
FROM AUTHOR a
JOIN BOOK b ON b.author_id = a.author_id
GROUP BY a.author_id, a.name
HAVING COUNT(*) >= 2
ORDER BY books DESC, a.name
"""
PRICE_SUMMARY_SQL = """
SELECT SUM(price) AS total_price, MIN(price) AS smallest_price, MAX(price) AS largest_price
FROM BOOK
"""

# F2.4  Loans (JOIN, LEFT JOIN)
OPEN_LOANS_SQL = """
SELECT l.loan_id, b.title AS book, m.name AS member, l.loan_date
FROM LOAN l
JOIN BOOK b ON l.book_id = b.book_id
JOIN MEMBER m ON l.member_id = m.member_id
WHERE l.return_date IS NULL
ORDER BY l.loan_date, l.loan_id
"""
MEMBERS_NO_LOANS_SQL = """
SELECT m.member_id, m.name, m.email
FROM MEMBER m
LEFT JOIN LOAN l ON l.member_id = m.member_id
WHERE l.loan_id IS NULL
ORDER BY m.name
"""
BOOKS_NEVER_BORROWED_SQL = """
SELECT b.book_id, b.title
FROM BOOK b
LEFT JOIN LOAN l ON l.book_id = b.book_id
WHERE l.loan_id IS NULL
ORDER BY b.title
"""

# F2.5  Most borrowed (GROUP BY, ORDER BY, LIMIT)
TOP_BOOKS_SQL = """
SELECT b.book_id, b.title, COUNT(*) AS loans
FROM BOOK b
JOIN LOAN l ON l.book_id = b.book_id
GROUP BY b.book_id, b.title
ORDER BY loans DESC, b.title
LIMIT 3
"""
TOP_MEMBER_SQL = """
SELECT m.member_id, m.name, COUNT(*) AS loans
FROM MEMBER m
JOIN LOAN l ON l.member_id = m.member_id
GROUP BY m.member_id, m.name
ORDER BY loans DESC, m.name
LIMIT 1
"""

# F2.6  Authors and books (LEFT JOIN, JOIN)
AUTHOR_BOOK_COUNT_SQL = """
SELECT a.author_id, a.name, COUNT(b.book_id) AS books
FROM AUTHOR a
LEFT JOIN BOOK b ON b.author_id = a.author_id
GROUP BY a.author_id, a.name
ORDER BY books DESC, a.name
"""
SAME_COUNTRY_BOOKS_SQL = """
SELECT b.book_id, b.title, a.name AS author, p.name AS publisher, a.country
FROM BOOK b
JOIN AUTHOR a ON b.author_id = a.author_id
JOIN PUBLISHER p ON b.publisher_id = p.publisher_id
WHERE a.country = p.country
ORDER BY b.title
"""

MAX_PRICE = 99999999.99  # the largest value of DECIMAL(10,2)


def run_query(sql):
    """Run a fixed SELECT (no user input inside) and return the rows as dictionaries."""
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute(sql)
        return cur.fetchall()
    finally:
        cur.close()
        db.close()


def run_prepared(sql, params):
    """Run a SELECT as a PREPARED STATEMENT: the SQL has placeholders, the values are sent apart."""
    db = get_db()
    cur = db.cursor(prepared=True)
    try:
        cur.execute(sql, params)
        columns = cur.column_names
        rows = []
        for row in cur.fetchall():
            # some connector versions return text columns as bytes
            values = [v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v for v in row]
            rows.append(dict(zip(columns, values)))
        return rows
    finally:
        cur.close()
        db.close()


@app.route("/search")
def search_books():
    """F2.1: title keyword (LIKE), price range (BETWEEN) and category, cheapest first."""
    categories = run_query("SELECT * FROM CATEGORY ORDER BY name")
    title = request.args.get("title", "").strip()
    min_text = request.args.get("min_price", "").strip()
    max_text = request.args.get("max_price", "").strip()
    category_text = request.args.get("category_id", "").strip()
    form = {"title": title, "min_price": min_text, "max_price": max_text, "category_id": category_text}

    error = None
    books = []
    try:
        min_price = float(min_text) if min_text else 0.0
        max_price = float(max_text) if max_text else MAX_PRICE
        category_id = int(category_text) if category_text else None
        if min_price < 0 or max_price < 0:
            error = "Prices cannot be negative."
        elif min_price > max_price:
            error = "The minimum price is bigger than the maximum price."
    except ValueError:
        error = "Enter valid numbers for the prices and the category."

    if not error:
        # the % signs are part of the VALUE sent to the placeholder, not of the SQL text
        books = run_prepared(SEARCH_BOOKS_SQL,
                             (f"%{title}%", min_price, max_price, category_id, category_id))
    return render_template("search.html", books=books, categories=categories, form=form, error=error)


@app.route("/catalogue")
def catalogue():
    """F2.2: all the books with the author, publisher and category names."""
    return render_template("catalogue.html", books=run_query(CATALOGUE_SQL))


@app.route("/reports")
def reports():
    """F2.3: books and average price per category, authors with 2+ books, price summary."""
    return render_template(
        "reports.html",
        categories=run_query(CATEGORY_REPORT_SQL),
        authors=run_query(PROLIFIC_AUTHORS_SQL),
        summary=run_query(PRICE_SUMMARY_SQL),
    )


@app.route("/loans")
def loans():
    """F2.4: loans not returned, members with no loans, books never borrowed."""
    return render_template(
        "loans.html",
        open_loans=run_query(OPEN_LOANS_SQL),
        idle_members=run_query(MEMBERS_NO_LOANS_SQL),
        unborrowed_books=run_query(BOOKS_NEVER_BORROWED_SQL),
    )


@app.route("/most-borrowed")
def most_borrowed():
    """F2.5: the 3 books with the most loans and the member with the most loans."""
    return render_template(
        "most_borrowed.html",
        top_books=run_query(TOP_BOOKS_SQL),
        top_members=run_query(TOP_MEMBER_SQL),
    )


@app.route("/authors-books")
def authors_books():
    """F2.6: number of books of every author, books whose author and publisher share a country."""
    return render_template(
        "authors_books.html",
        author_counts=run_query(AUTHOR_BOOK_COUNT_SQL),
        same_country=run_query(SAME_COUNTRY_BOOKS_SQL),
    )


if __name__ == "__main__":
    app.run(debug=True)
