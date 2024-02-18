import sqlite3

# Create or connect to the SQLite database
db_connection = sqlite3.connect("pokemon_db.sqlite")
db_cursor = db_connection.cursor()

# Create the Users table
db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        email VARCHAR(255) NOT NULL,
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        user_name VARCHAR(255) NOT NULL,
        password VARCHAR(255),
        usd_balance DOUBLE NOT NULL
    )
""")

# Create the Pokemon_cards table
db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS Pokemon_cards (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        card_name TEXT NOT NULL,
        card_type TEXT NOT NULL,
        rarity TEXT NOT NULL,
        count INTEGER,
        owner_id INTEGER,
        FOREIGN KEY (owner_id) REFERENCES Users (ID)
    )
""")

# Commit the changes and close the database connection
db_connection.commit()
db_connection.close()

