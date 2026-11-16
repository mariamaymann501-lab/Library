-- Lab 4 - Problem 2: the SQL of the website pages F2.1 - F2.6
-- Run with:  mysql -u root -p < problem2_Queries.sql   (after problem2_DDL.sql and problem2_DML.sql)
-- Every query is labelled with the page it belongs to.

USE library;

-- F2.1 Search books (WHERE): title keyword (LIKE), price range (BETWEEN) and a category, cheapest first.
-- (Example values; the website sends what the user typed through placeholders, see the bonus below.)
SELECT b.book_id, b.title, b.price, b.publish_year, c.name AS category
FROM BOOK b
JOIN CATEGORY c ON b.category_id = c.category_id
WHERE b.title LIKE '%a%'
  AND b.price BETWEEN 15 AND 20
  AND b.category_id = 1
ORDER BY b.price ASC, b.title ASC;

-- F2.1 (Bonus) The same search as a PREPARED STATEMENT: the user's values are never part of the SQL text.
PREPARE search_books FROM
    'SELECT b.book_id, b.title, b.price, b.publish_year, c.name AS category
     FROM BOOK b
     JOIN CATEGORY c ON b.category_id = c.category_id
     WHERE b.title LIKE ? AND b.price BETWEEN ? AND ? AND b.category_id = ?
     ORDER BY b.price ASC, b.title ASC';
SET @keyword = '%a%', @min_price = 15, @max_price = 20, @category = 1;
EXECUTE search_books USING @keyword, @min_price, @max_price, @category;
DEALLOCATE PREPARE search_books;

-- F2.2 Catalogue (JOIN): author, publisher and category names instead of the ids.
SELECT b.book_id, b.title, b.price, b.publish_year, a.name AS author, p.name AS publisher, c.name AS category
FROM BOOK b
JOIN AUTHOR a ON b.author_id = a.author_id
JOIN PUBLISHER p ON b.publisher_id = p.publisher_id
JOIN CATEGORY c ON b.category_id = c.category_id
ORDER BY b.book_id;

-- F2.3 (a) Reports: the number of books and the average price of each category.
SELECT c.name AS category, COUNT(b.book_id) AS books, ROUND(AVG(b.price), 2) AS average_price
FROM CATEGORY c
LEFT JOIN BOOK b ON b.category_id = c.category_id
GROUP BY c.category_id, c.name
ORDER BY c.name;

-- F2.3 (b) Reports: the authors who wrote at least 2 books.
SELECT a.author_id, a.name, COUNT(*) AS books
FROM AUTHOR a
JOIN BOOK b ON b.author_id = a.author_id
GROUP BY a.author_id, a.name
HAVING COUNT(*) >= 2
ORDER BY books DESC, a.name;

-- F2.3 (c) Reports: the total, smallest and largest price of the whole library.
SELECT SUM(price) AS total_price, MIN(price) AS smallest_price, MAX(price) AS largest_price
FROM BOOK;

-- F2.4 (a) Loans: the loans not returned yet, with the book title and the member name.
SELECT l.loan_id, b.title AS book, m.name AS member, l.loan_date
FROM LOAN l
JOIN BOOK b ON l.book_id = b.book_id
JOIN MEMBER m ON l.member_id = m.member_id
WHERE l.return_date IS NULL
ORDER BY l.loan_date, l.loan_id;

-- F2.4 (b) Loans: the members who never borrowed a book.
SELECT m.member_id, m.name, m.email
FROM MEMBER m
LEFT JOIN LOAN l ON l.member_id = m.member_id
WHERE l.loan_id IS NULL
ORDER BY m.name;

-- F2.4 (c) Loans: the books that were never borrowed.
SELECT b.book_id, b.title
FROM BOOK b
LEFT JOIN LOAN l ON l.book_id = b.book_id
WHERE l.loan_id IS NULL
ORDER BY b.title;

-- F2.5 (a) Most borrowed: the 3 books with the most loans.
SELECT b.book_id, b.title, COUNT(*) AS loans
FROM BOOK b
JOIN LOAN l ON l.book_id = b.book_id
GROUP BY b.book_id, b.title
ORDER BY loans DESC, b.title
LIMIT 3;

-- F2.5 (b) Most borrowed: the member with the most loans.
SELECT m.member_id, m.name, COUNT(*) AS loans
FROM MEMBER m
JOIN LOAN l ON l.member_id = m.member_id
GROUP BY m.member_id, m.name
ORDER BY loans DESC, m.name
LIMIT 1;

-- F2.6 (a) Authors and books: every author with the number of books, including the authors who wrote 0.
SELECT a.author_id, a.name, COUNT(b.book_id) AS books
FROM AUTHOR a
LEFT JOIN BOOK b ON b.author_id = a.author_id
GROUP BY a.author_id, a.name
ORDER BY books DESC, a.name;

-- F2.6 (b) Authors and books: the books whose author and publisher come from the same country.
SELECT b.book_id, b.title, a.name AS author, p.name AS publisher, a.country
FROM BOOK b
JOIN AUTHOR a ON b.author_id = a.author_id
JOIN PUBLISHER p ON b.publisher_id = p.publisher_id
WHERE a.country = p.country
ORDER BY b.title;
