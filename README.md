# Lab 4 - Problem 2: Library (Books, Authors, Publishers, Categories, Members, Loans)

A Flask + MySQL website for the `library` database. It continues the Lab 3 website (add, edit and delete books and authors, login, image upload) and adds the Lab 4 search pages **F2.1 - F2.6**.

## Project structure

```
lab4-<student-id>/
├── problem2_DDL.sql            # creates the database `library` and its 6 tables
├── problem2_DML.sql            # seed data for the 6 tables
├── problem2_Queries.sql        # the SQL of the pages F2.1 - F2.6 (one "-- F2.x" comment each)
├── problem2_users.sql          # optional: users table for the login (the website also creates it by itself)
├── problem2_bonus_images.sql   # optional: image columns from Lab 3 (the website also adds them by itself)
├── README.md
└── website/
    ├── app.py
    ├── requirements.txt
    ├── .env.example
    ├── templates/              # HTML pages
    └── static/                 # CSS files and uploaded images
```

## Requirements

- Python 3.9 or newer
- MySQL Server (and the `mysql` client or MySQL Workbench)

## 1. Create the database

Open a terminal in the project folder (the one that contains `problem2_DDL.sql`) and run:

```bash
mysql -u root -p < problem2_DDL.sql
mysql -u root -p < problem2_DML.sql
```

(or open each file in MySQL Workbench and press Execute, in this order).

`problem2_DDL.sql` deletes and re-creates the `library` database, so it can be re-run at any time. The login table (`users`) is re-created by the website itself the next time it opens a page, so you do not have to run `problem2_users.sql` (you may, it is safe).

To try the queries of the pages by hand:

```bash
mysql -u root -p < problem2_Queries.sql
```

## 2. Set up the website

```bash
cd website
```

Create and activate a virtual environment.

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

If PowerShell blocks the activation, run `Set-ExecutionPolicy -Scope Process Bypass` first.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the packages:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` (`copy .env.example .env` on Windows, `cp .env.example .env` on macOS / Linux) and set `DB_USER`, `DB_PASSWORD` (your MySQL user and password) and `SECRET_KEY` (any long random text).

## 3. Run

From inside the `website` folder, with the virtual environment active:

```bash
python app.py
```

Open http://127.0.0.1:5000. Click **Register** to create an account, and you will see the library. Use the menu bar to open the pages.

## Pages

| Page | URL | What it shows | SQL features |
|---|---|---|---|
| Home (Lab 3) | `/` | Add, edit and delete books and authors, with cover and photo upload | INSERT, UPDATE, DELETE |
| **F2.1** Search books | `/search` | Form: title keyword, minimum and maximum price, category. Matching books, cheapest first | `WHERE`, `LIKE`, `BETWEEN`, `ORDER BY` |
| **F2.2** Catalogue | `/catalogue` | All books with the author, publisher and category **names** | `JOIN` (3 tables) |
| **F2.3** Reports | `/reports` | (a) books and average price per category, (b) authors with at least 2 books, (c) total, smallest and largest price | `GROUP BY`, `HAVING`, `SUM/MIN/MAX/AVG` |
| **F2.4** Loans | `/loans` | (a) loans not returned yet, (b) members who never borrowed, (c) books never borrowed | `JOIN`, `LEFT JOIN ... IS NULL` |
| **F2.5** Most borrowed | `/most-borrowed` | The 3 books with the most loans and the member with the most loans | `GROUP BY`, `ORDER BY`, `LIMIT` |
| **F2.6** Authors and books | `/authors-books` | (a) every author with the number of books (0 included), (b) books whose author and publisher are from the same country | `LEFT JOIN`, `JOIN` |

The SQL used by each page is also in `problem2_Queries.sql`, with the label `-- F2.x` before every query.

## Bonus: prepared statement in F2.1

The search form never puts what the user typed inside the SQL text. The SQL is fixed and has only placeholders:

```sql
WHERE b.title LIKE %s AND b.price BETWEEN %s AND %s AND (%s IS NULL OR b.category_id = %s)
```

The values (keyword, prices, category) are sent separately with a prepared cursor (`cursor(prepared=True)`), so text such as `'; DROP TABLE BOOK; --` is just a keyword that matches nothing. The same search is shown as a `PREPARE / EXECUTE` statement in `problem2_Queries.sql`.

## Lab 3 features (still included)

- Register, log in and log out (bcrypt password hashes; every page needs a login).
- Add, edit and delete books and authors. A book now also has a year, a publisher and a category.
- Deleting an author deletes their books, and deleting a book deletes its loans (`ON DELETE CASCADE`).
- Optional cover image for each book and photo for each author (PNG, JPG, GIF or WEBP, up to 5 MB), saved in `website/static/uploads/`.

## Troubleshooting

- **Access denied for user**: check `DB_USER` and `DB_PASSWORD` in `website/.env`.
- **Unknown database 'library'**: run `problem2_DDL.sql` and `problem2_DML.sql` first (step 1).
- **Port 5000 already in use**: stop the other `python app.py` with `Ctrl + C`.

Do not upload your real `.env` file or passwords to GitHub.
