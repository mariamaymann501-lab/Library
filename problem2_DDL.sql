-- Lab 4 - Problem 2: Library (Books, Authors, Publishers, Categories, Members, Loans)
-- Run with:  mysql -u root -p < problem2_DDL.sql
-- It can be re-run at any time: it deletes and re-creates the database.

DROP DATABASE IF EXISTS library;
CREATE DATABASE library;
USE library;

CREATE TABLE AUTHOR (
    author_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL
);

CREATE TABLE PUBLISHER (
    publisher_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50) NOT NULL
);

CREATE TABLE CATEGORY (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE BOOK (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    publish_year INT NOT NULL,
    author_id INT NOT NULL,
    publisher_id INT NOT NULL,
    category_id INT NOT NULL,
    FOREIGN KEY (author_id) REFERENCES AUTHOR(author_id)
        ON DELETE CASCADE,
    FOREIGN KEY (publisher_id) REFERENCES PUBLISHER(publisher_id),
    FOREIGN KEY (category_id) REFERENCES CATEGORY(category_id)
);

CREATE TABLE MEMBER (
    member_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    join_date DATE NOT NULL
);

-- return_date is NULL while the book is still borrowed.
CREATE TABLE LOAN (
    loan_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    member_id INT NOT NULL,
    loan_date DATE NOT NULL,
    return_date DATE NULL,
    FOREIGN KEY (book_id) REFERENCES BOOK(book_id)
        ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES MEMBER(member_id)
);
