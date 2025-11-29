from datetime import datetime 
from typing import List, Dict
import json

from sqlalchemy.orm import Session

from ..models import GameModel

class TicTacToeGame:
    def __init__(self, game_id: str, board: List[str] = None, current_player: str = "X", 
                 winner: str = None, game_over: bool = False):
        self.game_id = game_id
        self.board = board if board is not None else [" " for _ in range(9)]
        self.current_player = current_player
        self.winner = winner
        self.game_over = game_over
    
    @classmethod
    def from_db_model(cls, db_game: GameModel):
        """Create a TicTacToeGame instance from database model"""
        board = json.loads(db_game.board)
        return cls(
            game_id=db_game.game_id,
            board=board,
            current_player=db_game.current_player,
            winner=db_game.winner,
            game_over=db_game.game_over
        )
    
    def to_db_model(self, db: Session, user_id: int = None) -> GameModel:
        """Convert to database model"""
        db_game = db.query(GameModel).filter(GameModel.game_id == self.game_id).first()
        if not db_game:
            db_game = GameModel(game_id=self.game_id, user_id=user_id)
        
        db_game.board = json.dumps(self.board)
        db_game.current_player = self.current_player
        db_game.winner = self.winner
        db_game.game_over = self.game_over
        db_game.updated_at = datetime.utcnow()

        return db_game
    
    def save_to_db(self, db: Session, user_id: int = None):
        """Save current state to database"""
        db_game = self.to_db_model(db, user_id)
        db.add(db_game)
        db.commit()
        db.refresh(db_game)
        return db_game
        
    def make_move(self, position: int, db: Session, user_id: int = None) -> bool:
        """Make a move for the human player and save to db"""
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
        
        # Save to database after move
        self.save_to_db(db, user_id)
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

def generate_game_id() -> str:
    """Generate a unique game ID"""
    return f"game_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"



