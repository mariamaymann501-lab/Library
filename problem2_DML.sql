-- Lab 4 - Problem 2: seed data for the six tables
-- Run with:  mysql -u root -p < problem2_DML.sql   (after problem2_DDL.sql)
--
-- What the data contains (required by the assignment):
--   * two authors from the same country ....... Agatha Christie and George Orwell (United Kingdom)
--   * an author with no books ................. Taha Hussein
--   * an author who wrote at least 2 books .... Naguib Mahfouz (3), Agatha Christie (3)
--   * an author and a publisher, same country . Mahfouz / Dar El Shorouk (Egypt); Christie, Orwell / Penguin Books (United Kingdom)
--   * a book priced between 15 and 20 ......... Palace Walk (18.50), Miramar (16.75), ...
--   * a book that was never borrowed .......... books 7 to 10
--   * a member with no loans .................. Youssef Ali
--   * a loan that is not returned yet ......... loans 4, 7 and 10 (return_date is NULL)

USE library;

INSERT INTO AUTHOR (author_id, name, country) VALUES
(1, 'Naguib Mahfouz',  'Egypt'),
(2, 'Agatha Christie', 'United Kingdom'),
(3, 'George Orwell',   'United Kingdom'),
(4, 'Paulo Coelho',    'Brazil'),
(5, 'Taha Hussein',    'Egypt');

INSERT INTO PUBLISHER (publisher_id, name, country) VALUES
(1, 'Dar El Shorouk', 'Egypt'),
(2, 'Penguin Books',  'United Kingdom'),
(3, 'HarperCollins',  'United States');

INSERT INTO CATEGORY (category_id, name) VALUES
(1, 'Fiction'),
(2, 'Mystery'),
(3, 'Classics');

INSERT INTO BOOK (book_id, title, price, publish_year, author_id, publisher_id, category_id) VALUES
(1,  'Palace Walk',                   18.50, 1956, 1, 1, 1),
(2,  'The Thief and the Dogs',        14.00, 1961, 1, 1, 1),
(3,  'Miramar',                       16.75, 1967, 1, 1, 1),
(4,  'Murder on the Orient Express',  21.00, 1934, 2, 2, 2),
(5,  'And Then There Were None',      17.99, 1939, 2, 2, 2),
(6,  'Death on the Nile',             24.50, 1937, 2, 3, 2),
(7,  'Animal Farm',                   12.99, 1945, 3, 2, 3),
(8,  'Nineteen Eighty-Four',          19.99, 1949, 3, 3, 3),
(9,  'The Alchemist',                 15.00, 1988, 4, 3, 1),
(10, 'Veronika Decides to Die',       22.00, 1998, 4, 3, 1);

INSERT INTO MEMBER (member_id, name, email, join_date) VALUES
(1, 'Ahmed Hassan',  'ahmed.hassan@example.com',  '2026-01-10'),
(2, 'Sara Mostafa',  'sara.mostafa@example.com',  '2026-02-03'),
(3, 'Omar Khaled',   'omar.khaled@example.com',   '2026-03-15'),
(4, 'Mariam Adel',   'mariam.adel@example.com',   '2026-05-21'),
(5, 'Youssef Ali',   'youssef.ali@example.com',   '2026-08-30');

INSERT INTO LOAN (loan_id, book_id, member_id, loan_date, return_date) VALUES
(1,  1, 1, '2026-09-01', '2026-09-10'),
(2,  1, 2, '2026-09-05', '2026-09-15'),
(3,  1, 3, '2026-09-20', '2026-10-01'),
(4,  1, 1, '2026-10-10', NULL),
(5,  2, 1, '2026-09-02', '2026-09-12'),
(6,  2, 2, '2026-09-18', '2026-09-28'),
(7,  2, 1, '2026-10-12', NULL),
(8,  3, 2, '2026-09-25', '2026-10-05'),
(9,  3, 1, '2026-10-15', '2026-10-25'),
(10, 4, 2, '2026-10-01', NULL),
(11, 5, 3, '2026-10-03', '2026-10-13'),
(12, 6, 4, '2026-10-20', '2026-10-30');
