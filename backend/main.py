from fastapi import FastAPI 
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from typing import List, Dict
import time
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = FastAPI(title="Tic Tac Toe API")

# todo change to database 
games = {}

class TicTacToeGame:
    def __init__(self, game_id: str):
        self.game_id = game_id
        self.board = [" " for _ in range(9)]
        self.current_player = "X"  # Human starts
        self.winner = None
        self.game_over = False
    
    def make_move(self, position: int) -> bool:
        """Make a move for the human player"""
        if self.game_over or self.board[position] != " ":
            return False
        
        self.board[position] = "X"
        
        if self.check_winner("X"):
            self.winner = "X"
            self.game_over = True
        elif self.is_board_full():
            self.game_over = True
        else:
            self.computer_move()
        
        return True
    
    def computer_move(self) -> None:
        """Computer makes a move using minimax algorithm"""
        if self.game_over:
            return
        
        # Use minimax to find best move
        best_score = float('-inf')
        best_move = None
        
        for i in range(9):
            if self.board[i] == " ":
                self.board[i] = "O"
                score = self.minimax(self.board, 0, False)
                self.board[i] = " "
                
                if score > best_score:
                    best_score = score
                    best_move = i
        
        if best_move is not None:
            self.board[best_move] = "O"
            
            if self.check_winner("O"):
                self.winner = "O"
                self.game_over = True
            elif self.is_board_full():
                self.game_over = True
            else:
                self.current_player = "X"
    
    def minimax(self, board: List[str], depth: int, is_maximizing: bool) -> int:
        """Minimax algorithm for computer AI"""
        scores = {"X": -1, "O": 1, "tie": 0}
        
        # Check for terminal states
        if self.check_winner_board("O", board):
            return scores["O"]
        if self.check_winner_board("X", board):
            return scores["X"]
        if self.is_board_full_board(board):
            return scores["tie"]
        
        if is_maximizing:
            best_score = float('-inf')
            for i in range(9):
                if board[i] == " ":
                    board[i] = "O"
                    score = self.minimax(board, depth + 1, False)
                    board[i] = " "
                    best_score = max(score, best_score)
            return best_score
        else:
            best_score = float('inf')
            for i in range(9):
                if board[i] == " ":
                    board[i] = "X"
                    score = self.minimax(board, depth + 1, True)
                    board[i] = " "
                    best_score = min(score, best_score)
            return best_score
    
    def check_winner(self, player: str) -> bool:
        """Check if the given player has won"""
        return self.check_winner_board(player, self.board)
    
    def check_winner_board(self, player: str, board: List[str]) -> bool:
        """Check winner for a given board state"""
        # Check rows, columns, and diagonals
        win_conditions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # columns
            [0, 4, 8], [2, 4, 6]              # diagonals
        ]
        
        for condition in win_conditions:
            if all(board[i] == player for i in condition):
                return True
        return False
    
    def is_board_full(self) -> bool:
        """Check if the board is full"""
        return self.is_board_full_board(self.board)
    
    def is_board_full_board(self, board: List[str]) -> bool:
        """Check if a given board is full"""
        return " " not in board
    
    def get_game_state(self) -> Dict:
        """Return current game state"""
        return {
            "game_id": self.game_id,
            "board": self.board,
            "current_player": self.current_player,
            "winner": self.winner,
            "game_over": self.game_over
        }

@app.post("/game")
async def create_game():
    """Create a new Tic Tac Toe game"""
    game_id = str(len(games) + 1)
    game = TicTacToeGame(game_id)
    games[game_id] = game
    return game.get_game_state()

@app.get("/game/{game_id}")
async def get_game_state(game_id: str):
    """Get current game state"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return games[game_id].get_game_state()

@app.post("/game/{game_id}/move/{position}")
async def make_move(game_id: str, position: int):
    """Make a move in the game"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if position < 0 or position > 8:
        raise HTTPException(status_code=400, detail="Invalid position")
    
    game = games[game_id]
    
    if game.game_over:
        raise HTTPException(status_code=400, detail="Game is over")
    
    if not game.make_move(position):
        raise HTTPException(status_code=400, detail="Invalid move")
    
    return game.get_game_state()

@app.delete("/game/{game_id}")
async def delete_game(game_id: str):
    """Delete a game"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    del games[game_id]
    return {"message": "Game deleted"}

@app.get("/")
def read_root():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(index_path)

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
