from datetime import datetime
from typing import List, Dict, Optional
import json

from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy import select
from backend.app.models.game import GameModel, GameType, GameStatus


class TicTacToeGame:
    def __init__(
        self,
        game_id: str,
        board: List[str] | None = None,
        current_player: str = "X",
        winner: str = "",
        game_over: bool = False,
        game_type: GameType = GameType.VS_COMPUTER,
        game_status: GameStatus = GameStatus.PLAYING,
        player_x: Optional[int] = None,
        player_o: Optional[int] = None,
    ):
        self.game_id = game_id
        self.board = board if board is not None else [" " for _ in range(9)]
        self.current_player = current_player
        self.winner = winner
        self.game_over = game_over
        self.game_type = game_type
        self.game_status = game_status
        self.player_x = player_x
        self.player_o = player_o

    @classmethod
    async def from_db_model(cls, db_game: GameModel):
        """Create a TicTacToeGame instance from database model"""
        board = json.loads(db_game.board)
        return cls(
            game_id=db_game.game_id,
            board=board,
            current_player=db_game.current_player,
            winner=db_game.winner,
            game_over=db_game.game_over,
            game_type=db_game.game_type,
            game_status=db_game.game_status,
            player_x=db_game.player_x,
            player_o=db_game.player_o,
        )

    async def to_db_model(self, db: Session, user_id: int | None = None) -> GameModel:
        """Convert to database model"""
        s = select(GameModel).where(GameModel.game_id == self.game_id)
        result = await db.execute(s)
        db_game = result.scalar_one_or_none()

        if not db_game:
            db_game = GameModel(
                game_id=self.game_id, user_id=user_id, game_type=self.game_type
            )

        db_game.board = json.dumps(self.board)
        db_game.current_player = self.current_player
        db_game.winner = self.winner
        db_game.game_over = self.game_over
        db_game.game_type = self.game_type
        db_game.game_status = self.game_status
        db_game.player_x = self.player_x
        db_game.player_o = self.player_o
        db_game.updated_at = datetime.utcnow()

        return db_game

    async def save_to_db(self, db: Session, user_id: int | None = None):
        """Save current state to database"""
        db_game = await self.to_db_model(db, user_id)
        db.add(db_game)
        await db.commit()
        await db.refresh(db_game)
        return db_game

    async def make_move(
        self, position: int, db: Session, user_id: int | None = None
    ) -> bool:
        """Make a move in the game and save to db"""
        if self.game_over or self.board[position] != " ":
            return False

        # Make the move
        self.board[position] = self.current_player

        # Check for winner or tie
        if self.check_winner(self.current_player):
            self.winner = self.current_player
            self.game_over = True
            self.game_status = GameStatus.FINISHED
        elif self.is_board_full():
            self.game_over = True
            self.game_status = GameStatus.FINISHED
        else:
            # Switch player
            self.current_player = "O" if self.current_player == "X" else "X"

            # If vs computer and it's computer's turn, make computer move
            if self.game_type == GameType.VS_COMPUTER and self.current_player == "O":
                self.computer_move()

        # Save to database after move
        await self.save_to_db(db, self.player_x)
        return True

    def computer_move(self) -> None:
        """Computer makes a move using minimax algorithm"""
        if self.game_over:
            return

        # Use minimax to find best move
        best_score = float("-inf")
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
                self.game_status = GameStatus.FINISHED
            elif self.is_board_full():
                self.game_over = True
                self.game_status = GameStatus.FINISHED
            else:
                self.current_player = "X"

    def minimax(self, board: List[str], depth: int, is_maximizing: bool) -> float:
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
            best_score = float("-inf")
            for i in range(9):
                if board[i] == " ":
                    board[i] = "O"
                    score = self.minimax(board, depth + 1, False)
                    board[i] = " "
                    best_score = max(score, best_score)
            return best_score
        else:
            best_score = float("inf")
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
        win_conditions = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],  # rows
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],  # columns
            [0, 4, 8],
            [2, 4, 6],  # diagonals
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

    async def get_game_state(self) -> Dict:
        """Return current game state"""
        print(self.game_status.value)
        return {
            "game_id": self.game_id,
            "board": self.board,
            "current_player": self.current_player,
            "winner": self.winner,
            "game_over": self.game_over,
            "game_type": self.game_type.value,
            "game_status": self.game_status.value,
            "player_x": self.player_x,
            "player_o": self.player_o,
        }


async def generate_game_id() -> str:
    """Generate a unique game ID"""
    return f"game_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
