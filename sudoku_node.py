import socket
import threading
import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from server_state import ServerState
from requestHandler import RequestHandler

from sudoku import Sudoku

class SudokuNode:
    def __init__(self, http_port, p2p_port, handicap, anchor_node):
        # Obtain host IP
        self.host = socket.gethostbyname(socket.gethostname())

        self.http_port = http_port
        self.p2p_port = p2p_port
        self.anchor_node = anchor_node

        # Handicap time
        self.handicap = handicap

        # Dictionary to store peer connections
        self.peers = {}

        # Dictionary to store ongoing tasks
        self.sudoku_tasks = {}

        # Dictionary to store collected results
        self.sudoku_results = {}

        # Counter for processed puzzles
        self.processed_puzzles = 0

        # Server socket for P2P communication
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Server state
        self.server_state = ServerState()

        # Request handler
        self.RequestHandler = RequestHandler

    def start(self):
        self.server_socket.bind((self.host, self.p2p_port))
        self.server_socket.listen(5)
        print(f"Node started on {self.host}:{self.p2p_port}")

        # Start the HTTP server
        threading.Thread(target=self.start_http_server).start()

        # Check if current node is an anchor node
        anchor_host = self.anchor_node.split(':')[0]
        anchor_port = int(self.anchor_node.split(':')[1])

        if self.host == anchor_host and self.p2p_port == anchor_port:
            print("This node is an anchor node")
            self.peers[f"{self.host}:{self.p2p_port}"] = []
        else:
            self.connect_to_peer(anchor_host, anchor_port)

        threading.Thread(target=self.accept_connections).start()

    def start_http_server(self):
        http_server = HTTPServer((self.host, self.http_port), self.RequestHandler)
        http_server.node = self  # Pass reference to node
        print(f"HTTP server started on {self.host}:{self.http_port}")
        http_server.serve_forever()

    def accept_connections(self):
        while True:
            client_socket, address = self.server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if message:
                    self.process_message(json.loads(message), client_socket)
            except (socket.error, json.JSONDecodeError):
                client_socket.close()
                return

    def process_message(self, message, client_socket):
        print(f"Received message: {message}")
        msg_type = message.get('type')

        if msg_type == 'JOIN':
            new_peer = f"{message['host']}:{message['port']}"
            print(f"New node joined: {new_peer}")

            # Add the new peer to the dictionary
            if new_peer not in self.peers:
                self.peers[new_peer] = []

            # Add the new peer to all existing peers' lists
            for peer in self.peers:
                if peer != new_peer:
                    self.peers[peer].append(new_peer)

            # Update the new node with the current network state
            # clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # clientsocket.connect((self.host, self.http_port)

            # Inform the new node about all existing peers
            for peer_address in self.peers:
                if peer_address != new_peer:
                    peer_host, peer_port = peer_address.split(':')
                    new_peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        # new_peer_host, new_peer_port = new_peer_socket.split(':')
                        new_peer_socket.connect((message['host'], int(message['port'])))
                        update_message = {'type': 'UPDATE', 'host': peer_host, 'port': int(peer_port)}
                        new_peer_socket.send(json.dumps(update_message).encode('utf-8'))
                        new_peer_socket.close()
                    except ConnectionRefusedError:
                        print(f"Peer {peer_address} is not available")
            

            response = {'type': 'NETWORK', 'peers': self.peers}
            client_socket.send(json.dumps(response).encode('utf-8'))

            # Inform all existing peers about the new node
            for peer_address in self.peers:
                if peer_address != new_peer:
                    peer_host, peer_port = peer_address.split(':')
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        peer_socket.connect((peer_host, int(peer_port)))
                        update_message = {'type': 'UPDATE', 'host': message['host'], 'port': message['port']}
                        peer_socket.send(json.dumps(update_message).encode('utf-8'))
                        peer_socket.close()
                    except ConnectionRefusedError:
                        print(f"Peer {peer_address} is not available")

        elif msg_type == 'UPDATE':
            new_peer = f"{message['host']}:{message['port']}"
            if new_peer not in self.peers:
                self.peers[new_peer] = []

            for peer in self.peers:
                if peer != new_peer and new_peer not in self.peers[peer]:
                    self.peers[peer].append(new_peer)

        elif msg_type == 'LEAVE':
            leaving_peer = f"{message['host']}:{message['port']}"
            if leaving_peer in self.peers:
                del self.peers[leaving_peer]
                for peer in self.peers:
                    if leaving_peer in self.peers[peer]:
                        self.peers[peer].remove(leaving_peer)
                client_socket.close()

        elif msg_type == 'REQUEST':
            self.handle_sudoku_request(message, client_socket)
            self.server_state.update_stats(message['node_address'], validated=True)

        elif msg_type == 'PARTIAL_SOLUTION':
            self.handle_partial_solution(message)
            self.server_state.update_stats(message['node_address'], validated=True)

        elif msg_type == 'SOLUTION':
            self.handle_sudoku_solution(message)
            self.server_state.update_stats(message['node_address'], solved=True)

        elif msg_type == 'NETWORK':
            self.peers = message['peers']
            print(f"Network topology updated: {self.peers}")

    def handle_sudoku_request(self, message, client_socket):
        sudoku_id = message['sudoku_id']
        part = message['part']
        position = message['position']
        node_address = f"{self.host}:{self.http_port}"  # Get the node address

        sudoku = Sudoku(part)
        self.solve_sudoku_part(sudoku, sudoku_id, position)

        # Send the partially solved Sudoku part back to the main node
        peer_address = self.anchor_node 
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            peer_socket.connect((peer_address.split(':')[0], int(peer_address.split(':')[1])))
            response = {
                'type': 'PARTIAL_SOLUTION',
                'sudoku_id': sudoku_id,
                'part': sudoku.grid,
                'position': position,
                'node_address': node_address
            }  # Include position and node_address in response
            peer_socket.send(json.dumps(response).encode('utf-8'))
        except ConnectionRefusedError:
            print(f"Main node {peer_address} is not available")
        finally:
            peer_socket.close()


    def solve_sudoku_part(self, sudoku, sudoku_id, position):
        self._solve(sudoku, 0, 0)
        node_address = f"{self.host}:{self.http_port}"
        response = {'type': 'PARTIAL_SOLUTION', 'sudoku_id': sudoku_id, 'part': sudoku.grid, 'position': position, 'node_address': node_address}
        peer_address = self.anchor_node
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_address.split(':')[0], int(peer_address.split(':')[1])))
        peer_socket.send(json.dumps(response).encode('utf-8'))
        peer_socket.close()


    def _solve(self, sudoku, row, col):
        # Base case: If we reached beyond the last row, the puzzle is solved
        if row == 3:
            return True
        
        # Move to the next row when we reach the last column of the current row
        if col == 3:
            return self._solve(sudoku, row + 1, 0)
        
        # If the cell is already filled, move to the next cell
        if sudoku.grid[row][col] != 0:
            return self._solve(sudoku, row, col + 1)
        
        # Try filling the current cell with numbers from 1 to 9
        for num in range(1, 10):
            if self.is_valid(sudoku, row, col, num):
                sudoku.grid[row][col] = num
                # Recursive call for the next cell in the same row
                if self._solve(sudoku, row, col + 1):
                    return True
                # Backtrack if the solution is not valid
                sudoku.grid[row][col] = 0
                
        # If no number is valid for the current cell, backtrack
        return False

    def is_valid(self, sudoku, row, col, num):
        # Function to check if the placement of 'num' at (row, col) is valid
        # Check row, column, and subgrid for duplicates
        for i in range(3):
            if sudoku.grid[row][i] == num or sudoku.grid[i][col] == num:
                return False
        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                if sudoku.grid[start_row + i][start_col + j] == num:
                    return False
        return True

    def handle_sudoku_solution(self, message):
        sudoku_id = message['sudoku_id']
        if sudoku_id not in self.sudoku_results:
            self.sudoku_results[sudoku_id] = Sudoku([[0] * 9 for _ in range(9)])

        partial_solution = message['part']
        position = message['position']
        start_row, start_col = position

        for i in range(3):
            for j in range(3):
                if partial_solution[i][j] != 0:
                    self.sudoku_results[sudoku_id].grid[start_row + i][start_col + j] = partial_solution[i][j]

        if self.sudoku_results[sudoku_id].check():
            print(f"Sudoku {sudoku_id} solved:\n{self.sudoku_results[sudoku_id]}")
        else:
            print(f"Sudoku {sudoku_id} partially solved. Current state:\n{self.sudoku_results[sudoku_id]}")
            # Once all parts are received, solve the entire Sudoku
            self.solve_sudoku_part(self.sudoku_results[sudoku_id], sudoku_id, position)
            if self.sudoku_results[sudoku_id].check():
                print(f"Sudoku {sudoku_id} fully solved:\n{self.sudoku_results[sudoku_id]}")
            else:
                print(f"Sudoku {sudoku_id} could not be solved.\n{self.sudoku_results[sudoku_id]}")

    def handle_partial_solution(self, message):
        sudoku_id = message['sudoku_id']
        if sudoku_id not in self.sudoku_results:
            self.sudoku_results[sudoku_id] = Sudoku([[0] * 9 for _ in range(9)])

        partial_solution = message['part']
        position = message['position']
        start_row, start_col = position

        for i in range(3):
            for j in range(3):
                if partial_solution[i][j] != 0:
                    self.sudoku_results[sudoku_id].grid[start_row + i][start_col + j] = partial_solution[i][j]

        # Check if the entire Sudoku is solved
        if self.sudoku_results[sudoku_id].check():
            print(f"Sudoku {sudoku_id} fully solved:\n{self.sudoku_results[sudoku_id]}")
            self.server_state.update_stats(message['node_address'], validated=True)
        else:
            print(f"Sudoku {sudoku_id} partially solved. Current state:\n{self.sudoku_results[sudoku_id]}")
            self.server_state.update_stats(message['node_address'], validated=True)

    def distribute_sudoku_task(self, sudoku, sudoku_id):
        parts = self.split_sudoku(sudoku)
        node_address = f"{self.host}:{self.http_port}"  # Get the node address
        positions = [(i, j) for i in range(0, 9, 3) for j in range(0, 9, 3)]
        for part, position in zip(parts, positions):
            peer_address = random.choice(list(self.peers.keys()))
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                print(f"Connecting to peer {peer_address}")
                peer_socket.connect((peer_address.split(':')[0], int(peer_address.split(':')[1])))
                request = {'type': 'REQUEST', 'sudoku_id': sudoku_id, 'part': part, 'position': position, 'node_address': node_address}
                peer_socket.send(json.dumps(request).encode('utf-8'))
                peer_socket.close() 
            except ConnectionRefusedError:
                print(f"Peer {peer_address} is not available")

    def split_sudoku(self, sudoku):
        parts = []
        for i in range(0, 9, 3):
            for j in range(0, 9, 3):
                part = [[sudoku.grid[i + x][j + y] for y in range(3)] for x in range(3)]
                parts.append(part)
        return parts
    
    def connect_to_peer(self, host, port):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((host, port))
            message = {'type': 'JOIN', 'host': self.host, 'port': self.p2p_port}
            client_socket.send(json.dumps(message).encode('utf-8'))

            response = client_socket.recv(1024).decode('utf-8')
            response_data = json.loads(response)
            if response_data['type'] == 'NETWORK':
                self.peers = response_data['peers']
                print(f"Connected to network: {self.peers}")
        except ConnectionRefusedError:
            print(f"Anchor node {host}:{port} is not available")
            return
    
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sudoku Node')
    parser.add_argument('-p', type=int, default=8000, help='HTTP port')
    parser.add_argument('-s', type=int, default=8001, help='P2P port')
    parser.add_argument('-a', '--anchor', default="127.0.1.1:7000", help='Anchor node')
    #parser.add_argument('-a', '--anchor', default="192.168.1.27:7000", help='Anchor node')
    parser.add_argument('--handicap', type=int, default=0, help='Handicap time')
    args = parser.parse_args()

    node = SudokuNode(args.p, args.s, args.handicap, args.anchor)
    node.start()
    print(f"Node started on {node.host}:{node.http_port} (HTTP) and {node.p2p_port} (P2P)")
