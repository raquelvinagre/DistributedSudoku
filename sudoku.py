import time
from collections import deque


class Sudoku:
    def __init__(self, sudoku):
        self.grid = sudoku
        self.recent_requests = deque()

    def _limit_calls(self, base_delay=0.01, interval=10, threshold=5):
        current_time = time.time()
        self.recent_requests.append(current_time)
        num_requests = len([t for t in self.recent_requests if current_time - t < 10])

        if num_requests > 5:
            delay = 0.01 * (num_requests - 5 + 1)
            time.sleep(delay)

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += str(self.grid[i][j])
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation

    def update_row(self, row, values):
        """Update the values of the given row."""
        self.grid[row] = values
    
    def update_column(self, col, values):
        """Update the values of the given column."""
        for row in range(9):
            self.grid[row][col] = values[row]

    def check_row(self, row, base_delay=0.01, interval=10, threshold=5):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check row
        if sum(self.grid[row]) != 45 or len(set(self.grid[row])) != 9:
            return False

        return True

    def check_column(self, col, base_delay=0.01, interval=10, threshold=5):
        """Check if the given row is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check col
        if sum([self.grid[row][col] for row in range(9)]) != 45 or len(set([self.grid[row][col] for row in range(9)])) != 9:
            return False

        return True

    def check_square(self, row, col, base_delay=0.01, interval=10, threshold=5):
        """Check if the given 3x3 square is correct."""
        self._limit_calls(base_delay, interval, threshold)

        # Check square
        if sum([self.grid[row+i][col+j] for i in range(3) for j in range(3)]) != 45 or len(set([self.grid[row+i][col+j] for i in range(3) for j in range(3)])) != 9:
            return False

        return True

    def check(self, base_delay=0.01, interval=10, threshold=5):
        """Check if the given Sudoku solution is correct.
        
        You MUST incorporate this method without modifications into your final solution.
        """
        
        for row in range(9):
            if not self.check_row(row, base_delay, interval, threshold):
                return False

        # Check columns
        for col in range(9):
            if not self.check_column(col, base_delay, interval, threshold):
                return False

        # Check 3x3 squares
        for i in range(3):
            for j in range(3):
                if not self.check_square(i*3, j*3, base_delay, interval, threshold):
                    return False

        return True


# if __name__ == "__main__":
#
#     sudoku = Sudoku([[3, 5, 6, 2, 1, 4, 7, 8, 9], [2, 7, 1, 3, 8, 9, 4, 5, 6], [8, 4, 9, 5, 7, 6, 1, 2, 3], [5, 1, 2, 4, 3, 8, 9, 6, 7], [4, 3, 7, 9, 6, 2, 5, 1, 8], [6, 9, 8, 1, 5, 7, 2, 3, 4], [1, 2, 4, 6, 9, 3, 8, 7, 5], [7, 6, 5, 8, 4, 1, 3, 9, 2], [9, 8, 3, 7, 2, 5, 6, 4, 1]])
#
#     print(sudoku)
#
#     if sudoku.check():
#         print("Sudoku is correct!")
#     else:
#         print("Sudoku is incorrect! Please check your solution.")