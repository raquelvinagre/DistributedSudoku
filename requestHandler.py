import json
import random
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
from sudoku import Sudoku

class RequestHandler(BaseHTTPRequestHandler):
        
    def do_POST(self):
        parsed_path = urlparse(self.path)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        node_address = self.client_address[0] + ":" + str(self.client_address[1])

        if parsed_path.path == '/check':
            sudoku_grid = data.get('sudoku')
            if sudoku_grid:
                sudoku = Sudoku(sudoku_grid)
                response = {'solved': sudoku.check()}
                self.server.node.server_state.update_stats(node_address, validated=True)
                self.server.node.server_state.solution_found = True
            else:
                response = {'error': 'Invalid Sudoku data'}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif parsed_path.path == '/solve':
            sudoku_grid = data.get('sudoku')
            if sudoku_grid:
                sudoku = Sudoku(sudoku_grid)
                sudoku_id = random.randint(0, 100000)
                self.server.node.sudoku_tasks[sudoku_id] = sudoku
                self.server.node.distribute_sudoku_task(sudoku, sudoku_id)

                # Wait until the puzzle is solved or a timeout occurs
                start_time = time.time()
                timeout = 30  # Timeout in seconds
                while time.time() - start_time < timeout:
                    if sudoku_id in self.server.node.sudoku_results and self.server.node.sudoku_results[sudoku_id].check():
                        response = {'status': 'Solved', 'sudoku_id': sudoku_id, 'sudoku': self.server.node.sudoku_results[sudoku_id].grid}
                        self.server.node.server_state.update_stats(node_address, solved=True)
                        self.server.node.server_state.solution_found = True
                        break
                    time.sleep(1)
                else:
                    response = {'status': 'Solving', 'sudoku_id': sudoku_id}
            else:
                response = {'error': 'Invalid Sudoku data'}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/network':
            response = {'network': self.server.node.peers}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=4).encode('utf-8'))

        if parsed_path.path == '/stats':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"stats": self.server.node.server_state.get_stats()}, indent=4).encode('utf-8'))
