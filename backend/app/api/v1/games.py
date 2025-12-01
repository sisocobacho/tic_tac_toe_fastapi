from fastapi import HTTPException, Depends 
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session 
from ....database import get_db
from ...models import GameModel, User        
from ...services.user import  get_current_user
from ...services.game import TicTacToeGame, generate_game_id
from ...schema.game import GameStateResponse, GameSummaryResponse
from typing import List

router = APIRouter()

@router.post("/")
async def create_game(
    current_user: User = Depends(get_current_user),
    response_model=GameStateResponse,
    db: Session = Depends(get_db)
):
    """Create a new Tic Tac Toe game"""
    game_id = generate_game_id() 
    game = TicTacToeGame(game_id)
    game.save_to_db(db, current_user.id)
    return GameStateResponse(**game.get_game_state())

@router.get("/{game_id}")
async def get_game_state(
    game_id: str,
    response_model=GameStateResponse,
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
    return GameStateResponse(**game.get_game_state())

@router.post("/{game_id}/move/{position}")
async def make_move(
    game_id: str,
    position: int,
    response_model=GameStateResponse,
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
    
    return GameStateResponse(**game.get_game_state())

@router.get("/")
async def list_games(
    limit: int,
    skip: int=0,
    response_model=List[GameStateResponse],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all games for the current user"""
    db_games = db.query(GameModel).filter(
        GameModel.user_id == current_user.id
    ).order_by(GameModel.created_at.desc()).offset(skip).limit(limit).all()

    return [
       GameSummaryResponse( 
            game_id = game.game_id,
            current_player = game.current_player,
            winner = game.winner,
            game_over = game.game_over,
            created_at = game.created_at.isoformat(),
            updated_at = game.updated_at.isoformat()
        )
        for game in db_games
    ]

@router.delete("/{game_id}")
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

@router.delete("/")
async def delete_all_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all games for the current user"""
    db.query(GameModel).filter(GameModel.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All games deleted"}


