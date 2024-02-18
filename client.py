import socket


# Create a socket connection to the server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((socket.gethostname(), 30376))

try:
    while True:
        # Get user input for the command
        command = input("normal (LOGIN, QUIT)\nclient (BUY, SELL, BALANCE, LIST, QUIT, LOGOUT, LOOKUP, DEPOSIT)\nroot (BUY, SELL, BALANCE, LIST, QUIT, LOGOUT, WHO, LOOKUP, DEPOSIT, SHUTDOWN)\nEnter Command: ").strip().upper()

        if command == "QUIT":
            # Send QUIT command
            client_socket.sendall(b'QUIT\n')
            break
        
        if command == "SHUTDOWN":
            # Send SHUTDOWN command
            client_socket.close()
            break

        elif command in ["BUY", "SELL", "BALANCE", "LIST", "LOGIN", "LOGOUT", "WHO", "LOOKUP", "DEPOSIT" ]:
            # Send the command to the server
            client_socket.sendall(f'{command}\n'.encode('utf-8'))
            if command == "LOGIN":
                # Send LOGIN command
                user_info = input("Enter UserID and Password separated by space: ").strip()
                client_socket.sendall(f'LOGIN {user_info}\n'.encode('utf-8'))

            if command == "LOGOUT":
                # Send LOGOUT command
                client_socket.sendall(b'LOGOUT\n')

            if command == "WHO":
                # Send WHO command
                client_socket.sendall(b'WHO\n')

            if command == "LOOKUP":
                # Send LOOKUP command
                card_name = input("Enter card name to lookup: ").strip()
                client_socket.sendall(f'LOOKUP {card_name}\n'.encode('utf-8'))

            if command == "DEPOSIT":
                # Send DEPOSIT command
                amount = input("Enter amount to deposit: ").strip()
                client_socket.sendall(f'DEPOSIT {amount}\n'.encode('utf-8'))
            
            # Additional handling for BUY commands
            if command == "BUY":
                data = input("Enter data (card_name, card_type, rarity, price, count): ").strip()
                client_socket.sendall(f'{data}\n'.encode('utf-8'))
                print(data)
                
            # Additional handling for SELL commands
            if command == "SELL":
                data = input("Enter data (card_name, quantity, price): ").strip()
                client_socket.sendall(f'{data}\n'.encode('utf-8')) 
                print(data)

            # Additional handling for LIST and BALANCE commands
            if command == "LIST":
                client_socket.sendall(b'LIST\n')
            
            if command == "BALANCE":
                client_socket.sendall(b'BALANCE\n')
                

            # Receive and display the server's response
            response = client_socket.recv(4096)
            response_str = response.decode('utf-8')
            print(response_str)

        else:
            # Error handling
            print("Invalid command. Please enter a valid command")

finally:
    # Close the socket connection
    client_socket.close()
