import time
import os
import json

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Session, relationship
from typing import List, Dict
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings
from .database import get_db, Base, engine
from .app.models import GameModel        

app = FastAPI(title="Tic Tac Toe API")

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

# Database models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    games = relationship("GameModel", back_populates="user")


# Create tables
Base.metadata.create_all(bind=engine)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user

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

# Authentication endpoints
@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    # Check if username already exists
    db_user = get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        created_at=db_user.created_at
    )

@app.post("/auth/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at
    )


@app.post("/game")
async def create_game(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new Tic Tac Toe game"""
    game_id = generate_game_id() 
    game = TicTacToeGame(game_id)
    game.save_to_db(db, current_user.id)
    return game.get_game_state()

@app.get("/game/{game_id}")
async def get_game_state(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current game state (only if user owns the game)"""
    db_game = db.query(GameModel).filter(
        GameModel.game_id == game_id,
        GameModel.user_id == current_user.id
    ).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = TicTacToeGame.from_db_model(db_game)
    return game.get_game_state()

@app.post("/game/{game_id}/move/{position}")
async def make_move(
    game_id: str,
    position: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Make a move in the game (only if user owns the game)"""
    if position < 0 or position > 8:
        raise HTTPException(status_code=400, detail="Invalid position")
    
    db_game = db.query(GameModel).filter(
        GameModel.game_id == game_id,
        GameModel.user_id == current_user.id
    ).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = TicTacToeGame.from_db_model(db_game)
    
    if game.game_over:
        raise HTTPException(status_code=400, detail="Game is over")
    
    if not game.make_move(position, db):
        raise HTTPException(status_code=400, detail="Invalid move")
    
    return game.get_game_state()

@app.get("/games")
async def list_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all games for the current user"""
    db_games = db.query(GameModel).filter(
        GameModel.user_id == current_user.id
    ).order_by(GameModel.created_at.desc()).all()
    return [
        {
            "game_id": game.game_id,
            "current_player": game.current_player,
            "winner": game.winner,
            "game_over": game.game_over,
            "created_at": game.created_at.isoformat(),
            "updated_at": game.updated_at.isoformat()
        }
        for game in db_games
    ]

@app.delete("/game/{game_id}")
async def delete_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a game (only if user owns the game)"""
    db_game = db.query(GameModel).filter(
        GameModel.game_id == game_id,
        GameModel.user_id == current_user.id
    ).first()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    db.delete(db_game)
    db.commit()
    return {"message": "Game deleted"}

@app.delete("/games")
async def delete_all_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all games for the current user"""
    db.query(GameModel).filter(GameModel.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All games deleted"}

@app.get("/")
def read_root():
    index_path = os.path.join(settings.FRONTEND_DIR, "index.html")
    return FileResponse(index_path)

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
