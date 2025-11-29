import time
import os
import json

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session 
from typing import List, Dict
from datetime import datetime, timedelta

from .config import settings
from .database import get_db, Base, engine
from .app.models import GameModel, User        
from .app import schema
from .app.services.user import get_password_hash, get_user_by_username, authenticate_user, create_access_token, get_current_user
from .app.services.game import TicTacToeGame, generate_game_id

app = FastAPI(title="Tic Tac Toe API")

# Create tables
Base.metadata.create_all(bind=engine)

# Authentication endpoints
@app.post("/auth/register", response_model=schema.UserResponse)
async def register(user: schema.UserCreate, db: Session = Depends(get_db)):
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
    
    return schema.UserResponse(
        id=db_user.id,
        username=db_user.username,
        created_at=db_user.created_at
    )

@app.post("/auth/login", response_model=schema.Token)
async def login(user_login: schema.UserLogin, db: Session = Depends(get_db)):
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

@app.get("/users/me", response_model=schema.UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return schema.UserResponse(
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
