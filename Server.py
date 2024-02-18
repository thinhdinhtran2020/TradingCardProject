import socket
import sqlite3
import threading

active_connections = []

#This function will handle the client before the user log in
def handle_normal(client_socket, client_address, db_cursor):
    db_connection = sqlite3.connect("pokemon_db.sqlite")
    db_cursor = db_connection.cursor()
    print("Connected a normal user to database in thread:", threading.get_ident())
    while True:
        # Receive the client's command
        command = client_socket.recv(4096).decode('utf-8').strip()
        command = command.split()
        command[0] = command[0].upper()
        
        if not command:
            break
            
        if command[0] == "QUIT":
            # Terminate the client connection
            break
        
        if command[0] == "SHUTDOWN":
            db_connection.close()
            client_socket.close()
        
        if command[0] == "LOGIN":
            print("logging in")
            # Handle LOGIN command and user authentication
            user_info = client_socket.recv(4096).decode('utf-8').strip().split()
            user_info.pop(0)
            if len(user_info) == 2:
                username, password = user_info
                db_cursor.execute("SELECT * FROM Users WHERE user_name=? AND password=?", (username, password))
                user_data = db_cursor.fetchone()
                
                owner_id = user_data[0]
                if owner_id == 1:
                    client_socket.sendall(b'200 OK\nLogging in as root user\n')
                    active_connections.append((user_data[2],client_address[0]))
                    thread = threading.Thread(target=handle_root, args=(client_socket, client_address, db_cursor, owner_id))
                    thread.start()
                elif user_data is not None:
                    client_socket.sendall(b'200 OK\nLogging in as client user\n')
                    active_connections.append((user_data[2],client_address[0]))
                    thread = threading.Thread(target=handle_client, args=(client_socket, client_address, db_cursor, owner_id))
                    thread.start()
                else:
                    continue
            else:
                client_socket.sendall(b'401 Invalid command format. Please provide username or password.\n')
                
    db_connection.close()
    client_socket.close()
    
#This function will handle the client after the user log in with non root credentials
def handle_client(client_socket, client_address, db_cursor, owner_id):
    db_connection = sqlite3.connect("pokemon_db.sqlite")
    db_cursor = db_connection.cursor()
    print("Connected a client user to database in thread:", threading.get_ident())
    while True:
        # Receive the client's command
        command = client_socket.recv(4096).decode('utf-8').strip()
        command = command.split()
        command[0] = command[0].upper()

        if not command:
            break
        
        if command[0] == "WHO":
            client_socket.sendall(b'404 Not a root user\n')
            
        if command[0] == "SHUTDOWN":
            client_socket.sendall(b'404 Not a root user\n')

        if command[0] == "QUIT":
            # Terminate the client connection
            client_socket.close()
            break

        if command[0] == "LOGOUT":
            print("LOGOUT")
            client_socket.sendall(b'200 OK\n')
            active_connections.pop(0)
            thread = threading.Thread(target=handle_normal, args=(client_socket, client_address, db_cursor, owner_id))
            thread.start()
            break    

        if command[0] == "BUY":
            # Receive BUY command data
            command.pop(0)
            buy_data = command
            if len(buy_data) == 5:
                card_name, card_type, rarity, price, count = buy_data
                # Check user balance and insert into the database
                db_cursor.execute("SELECT usd_balance FROM Users WHERE ID=?", (owner_id,))
                user_balance = db_cursor.fetchone()
                if user_balance is None:
                    client_socket.sendall(b'User does not exist\n')
                else:
                    price_total = float(price) * int(count)
                    if user_balance[0] >= price_total:
                        db_cursor.execute("UPDATE Users SET usd_balance=usd_balance-? WHERE ID=?", (price_total, owner_id))
                        db_cursor.execute("INSERT INTO Pokemon_cards (card_name, card_type, rarity, count, owner_id) VALUES (?, ?, ?, ?, ?)",
                                            (card_name, card_type, rarity, count, owner_id))
                        db_connection.commit()
                        client_socket.sendall(f'200 OK\nBOUGHT: New balance: {count} {card_name}. User USD balance ${user_balance[0] - price_total:.2f}\n'.encode('utf-8'))
                    else:
                        client_socket.sendall(b'Not enough balance\n')
            else:
                client_socket.sendall(b'Invalid command format\n')


        elif command[0] == "SELL":
            # Receive SELL command data
            command.pop(0)
            sell_data = command
            if len(sell_data) == 3:
                card_name, quantity, price = sell_data
                # Check if user and card exist, then update user balance
                db_cursor.execute("SELECT count FROM Pokemon_cards WHERE card_name=? AND owner_id=?", (card_name, owner_id))
                card_count = db_cursor.fetchone()
                if card_count is not None and card_count[0] >= int(quantity):
                    db_cursor.execute("UPDATE Users SET usd_balance=usd_balance+? WHERE ID=?", (float(price) * int(quantity), owner_id))
                    db_cursor.execute("UPDATE Pokemon_cards SET count=count-? WHERE card_name=? AND owner_id=?", (quantity, card_name, owner_id))
                    db_connection.commit()
                    client_socket.sendall(f'200 OK\nSOLD: Quantity sold: {quantity} {card_name}. Money made: ${float(price) * int(quantity):.2f}\n'.encode())
                else:
                    client_socket.sendall(b'Not enough cards to sell\n')
            else:
                client_socket.sendall(b'Invalid command format\n')

        elif command[0] == "LIST":
            # Retrieve and send the list of Pokémon cards for the user
            db_cursor.execute("SELECT * FROM Pokemon_cards WHERE owner_id=?", (owner_id,))
            card_list = db_cursor.fetchall()
            header = "ID Card Name Type Rarity Count OwnerID\n"
            card_list_str = '\n'.join([' '.join(map(str, card)) for card in card_list])
            response = f'200 OK\nThe list of records in the Pokemon cards table for current user, user {owner_id}:\n{header}{card_list_str}\n'
            client_socket.sendall(response.encode('utf-8'))

        elif command[0] == "BALANCE":
            # Retrieve and send the user's USD balance
            db_cursor.execute("SELECT first_name, last_name, usd_balance FROM Users WHERE ID=?", (owner_id,))
            user_data = db_cursor.fetchone()
            if user_data is not None:
                response = f'200 OK\nBalance for user {user_data[0]} {user_data[1]}: ${user_data[2]:.2f}\n'
                client_socket.sendall(response.encode('utf-8'))
            else:
                client_socket.sendall(b'User does not exist\n')
        
        elif command[0] == "DEPOSIT":
            # Retrieve and send the user's USD balance
            command.pop(0)
            if len(command) == 1:
                db_cursor.execute("SELECT usd_balance FROM Users WHERE ID =?", (owner_id,))
                price_total = db_cursor.fetchone()
                price_total = int(price_total[0]) + int(command[0])
                db_cursor.execute("UPDATE Users SET usd_balance=? WHERE ID=?", (price_total, owner_id))
                db_connection.commit()
                client_socket.sendall(f'deposit successfully. New User balance ${price_total}\n'.encode('utf-8'))
            else:
                client_socket.sendall(b'Invalid Input\n')
        
        elif command[0] == "LOOKUP":
            command.pop(0)
            if len(command) == 1:
                card_name = str(command[0])
                db_cursor.execute("SELECT * FROM Pokemon_cards WHERE card_name=?", (card_name,))
                card_list = db_cursor.fetchall()
                header = "ID Card Name Type Rarity Count OwnerID\n"
                card_list_str = '\n'.join([' '.join(map(str, card)) for card in card_list])
                response = f'200 OK\nFound 1 match\n{header}{card_list_str}\n'
                client_socket.sendall(response.encode('utf-8'))
            else:
                client_socket.sendall(b'404 Your search did not match any records\n')
                

        else:
            client_socket.sendall(b'Invalid command\n')
            
    db_connection.close()
    
#This fucntion will handle the clinet after the user log in with root credentials 
def handle_root(client_socket, client_address, db_cursor, owner_id):
    db_connection = sqlite3.connect("pokemon_db.sqlite")
    db_cursor = db_connection.cursor()
    print("Connected a root user to database in thread:", threading.get_ident())
    while True:
        # Receive the client's command
        command = client_socket.recv(4096).decode('utf-8').strip()
        command = command.split()
        command[0] = command[0].upper()

        if not command:
            break
            
        if command[0] == "SHUTDOWN":
            db_connection.close()
            client_socket.close()
        
        if command[0] == "QUIT":
            # Terminate the client connection
            client_socket.close()
            break

        if command[0] == "LOGOUT":
            print("LOGOUT")
            client_socket.sendall(b'200 OK\n')
            active_connections.pop(0)
            thread = threading.Thread(target=handle_normal, args=(client_socket, client_address, db_cursor, owner_id))
            thread.start()
            break    

        if command[0] == "BUY":
            # Receive BUY command data
            command.pop(0)
            buy_data = command
            if len(buy_data) == 5:
                card_name, card_type, rarity, price, count = buy_data
                # Check user balance and insert into the database
                db_cursor.execute("SELECT usd_balance FROM Users WHERE ID=?", (owner_id,))
                user_balance = db_cursor.fetchone()
                if user_balance is None:
                    client_socket.sendall(b'User does not exist\n')
                else:
                    price_total = float(price) * int(count)
                    if user_balance[0] >= price_total:
                        db_cursor.execute("UPDATE Users SET usd_balance=usd_balance-? WHERE ID=?", (price_total, owner_id))
                        db_cursor.execute("INSERT INTO Pokemon_cards (card_name, card_type, rarity, count, owner_id) VALUES (?, ?, ?, ?, ?)",
                                            (card_name, card_type, rarity, count, owner_id))
                        db_connection.commit()
                        client_socket.sendall(f'200 OK\nBOUGHT: New balance: {count} {card_name}. User USD balance ${user_balance[0] - price_total:.2f}\n'.encode('utf-8'))
                    else:
                        client_socket.sendall(b'Not enough balance\n')
            else:
                client_socket.sendall(b'Invalid command format\n')


        elif command[0] == "SELL":
            # Receive SELL command data
            command.pop(0)
            sell_data = command
            if len(sell_data) == 3:
                card_name, quantity, price = sell_data
                # Check if user and card exist, then update user balance
                db_cursor.execute("SELECT count FROM Pokemon_cards WHERE card_name=? AND owner_id=?", (card_name, owner_id))
                card_count = db_cursor.fetchone()
                if card_count is not None and card_count[0] >= int(quantity):
                    db_cursor.execute("UPDATE Users SET usd_balance=usd_balance+? WHERE ID=?", (float(price) * int(quantity), owner_id))
                    db_cursor.execute("UPDATE Pokemon_cards SET count=count-? WHERE card_name=? AND owner_id=?", (quantity, card_name, owner_id))
                    db_connection.commit()
                    client_socket.sendall(f'200 OK\nSOLD: Quantity sold: {quantity} {card_name}. Money made: ${float(price) * int(quantity):.2f}\n'.encode())
                else:
                    client_socket.sendall(b'Not enough cards to sell\n')
            else:
                client_socket.sendall(b'Invalid command format\n')

        elif command[0] == "LIST":
            # Retrieve and send the list of all Pokémon cards
            db_cursor.execute("SELECT * FROM Pokemon_cards")
            card_list = db_cursor.fetchall()
            header = "ID Card Name Type Rarity Count OwnerID\n"
            card_list_str = '\n'.join([' '.join(map(str, card)) for card in card_list])
            response = f'200 OK\nThe list of records in the Pokemon cards table:\n{header}{card_list_str}\n'
            client_socket.sendall(response.encode('utf-8'))

        elif command[0] == "BALANCE":
            # Retrieve and send the user's USD balance
            db_cursor.execute("SELECT first_name, last_name, usd_balance FROM Users WHERE ID=?", (owner_id,))
            user_data = db_cursor.fetchone()
            if user_data is not None:
                response = f'200 OK\nBalance for user {user_data[0]} {user_data[1]}: ${user_data[2]:.2f}\n'
                client_socket.sendall(response.encode('utf-8'))
            else:
                client_socket.sendall(b'User does not exist\n')
        
        elif command[0] == "DEPOSIT":
            # Retrieve and send the user's USD balance
            command.pop(0)
            if len(command) == 1:
                db_cursor.execute("SELECT usd_balance FROM Users WHERE ID =?", (owner_id,))
                price_total = db_cursor.fetchone()
                price_total = int(price_total[0]) + int(command[0])
                db_cursor.execute("UPDATE Users SET usd_balance=? WHERE ID=?", (price_total, owner_id))
                db_connection.commit()
                client_socket.sendall(f'deposit successfully. New User balance ${price_total}\n'.encode('utf-8'))
            else:
                client_socket.sendall(b'Invalid Input\n')
        
        elif command[0] == "LOOKUP":
            command.pop(0)
            if len(command) == 1:
                card_name = str(command[0])
                db_cursor.execute("SELECT * FROM Pokemon_cards WHERE card_name=?", (card_name,))
                card_list = db_cursor.fetchall()
                header = "ID Card Name Type Rarity Count OwnerID\n"
                card_list_str = '\n'.join([' '.join(map(str, card)) for card in card_list])
                response = f'200 OK\nFound 1 match\n{header}{card_list_str}\n'
                client_socket.sendall(response.encode('utf-8'))
            else:
                client_socket.sendall(b'404 Your search did not match any records\n')
                
        elif command[0] == "WHO":
            command.pop(0)
            response = f'200 OK\nThe list of active users:\n'
            client_socket.sendall(response.encode('utf-8'))
            for i in active_connections:
                client_socket.sendall(f'{i[0]}    {i[1]}\n'.encode('utf-8'))
        else:
            client_socket.sendall(b'Invalid command\n')
            
    db_connection.close()
    

def main():
    # Create a socket and bind it to the server address and port
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((socket.gethostname(), 30376))

    # Listen for incoming connections
    server_socket.listen(10)  # Allow 10 client to connect at a time

    print("Server is listening for connections...")

    # Create or connect to the SQLite database
    db_connection = sqlite3.connect("pokemon_db.sqlite")
    db_cursor = db_connection.cursor()
    print("Connected to database")

    #Loop to initiate the first client
    while True:
        # Accept incoming connection
        client_socket, client_address = server_socket.accept()
        # Create new thread for pre-login client
        start_thread = threading.Thread(target=handle_normal, args=(client_socket, client_address, db_cursor))
        start_thread.start()
            
    client_socket.close()
    print(f"Connection with {client_address} closed")

main()