# Project's name: BOOK SALE (2019).
### Purpose: Create an online platform for book transactions between real users.
### Video link: https://www.youtube.com/watch?v=pKhviKseGfk&ab_channel=8899_L%C6%B0%C6%A1ngAnKhang

### Tools:
1. Flask
2. SQLite
   
### Features:
- Database used: booksale database:
1. users TABLE (id, username, hash, cash): Used to store login details and basic info (cash) of users.
2. history TABLE (OwnerID, BookName, Amount, SellBuy, Date): Used to store details of past transactions for each users.
3. book TABLE (OwnerID, OwnerName, Date, ForSale, BookName, Price, Description): A general database, used to store the details of books owned/ offered for sale of users.

### Webpages:
1. Index: Show a table/ list of books owned/ offered for sale of users.
2. Quote: Used to search for a desired book.
3. Buy: Used to buy books from other users.
4. Sell: Used to offer books for sale.
5. Add: Used to add books owned to account.
6. History: Used to view history transaction, and keep tracks when the books offered for sale is bought/ sold.

### Resources:
- Make use of CS50 IDE and the distributed code for Finance.
