import time
import os

from fastapi import FastAPI, HTTPException, Depends 
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session 

from .config import settings
from .database import get_db, Base, engine
from .app.models import GameModel, User        
from .app.services.game import TicTacToeGame, generate_game_id
from .app.api.v1 import users
from .app.services.user import  get_current_user

app = FastAPI(title="Tic Tac Toe API")

# Create tables
Base.metadata.create_all(bind=engine)

# routers
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["users"]
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
