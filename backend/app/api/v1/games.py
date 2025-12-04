from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy import select
from app.models.user import User
from app.models.game import GameModel
from app.services.user import get_current_user
from app.services.game import TicTacToeGame, generate_game_id
from app.schema.game import GameStateResponse, GameSummaryResponse
from typing import List

router = APIRouter()


@router.post(
    "/",
    response_model=GameStateResponse,
)
async def create_game(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Create a new Tic Tac Toe game"""
    game_id = await generate_game_id()
    game = TicTacToeGame(game_id)
    await game.save_to_db(db, current_user.id)
    state = await game.get_game_state()
    return GameStateResponse(**state)


@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game_state(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current game state (only if user owns the game)"""
    s = select(GameModel).where(
        GameModel.game_id == game_id, GameModel.user_id == current_user.id
    )

    result = await db.execute(s)
    db_game = result.scalar_one_or_none()

    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    game = await TicTacToeGame.from_db_model(db_game)
    state = await game.get_game_state()
    return GameStateResponse(**state)


@router.post("/{game_id}/move/{position}", response_model=GameStateResponse)
async def make_move(
    game_id: str,
    position: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Make a move in the game (only if user owns the game)"""
    if position < 0 or position > 8:
        raise HTTPException(status_code=400, detail="Invalid position")

    s = select(GameModel).where(
        GameModel.game_id == game_id, GameModel.user_id == current_user.id
    )

    result = await db.execute(s)

    db_game = result.scalar_one_or_none()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    game = await TicTacToeGame.from_db_model(db_game)
    print("game", game, game.game_id, db_game.game_id)
    if game.game_over:
        raise HTTPException(status_code=400, detail="Game is over")

    if not await game.make_move(position, db):
        raise HTTPException(status_code=400, detail="Invalid move")

    state = await game.get_game_state()
    return GameStateResponse(**state)


@router.get("/", response_model=List[GameSummaryResponse])
async def list_games(
    limit: int,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all games for the current user"""
    s = (
        select(GameModel)
        .where(GameModel.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(s)
    db_games = result.all()

    return [
        GameSummaryResponse(
            game_id=game.game_id,
            current_player=game.current_player,
            winner=game.winner,
            game_over=game.game_over,
            created_at=game.created_at.isoformat(),
            updated_at=game.updated_at.isoformat(),
        )
        for game in db_games
    ]


@router.delete("/{game_id}")
async def delete_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a game (only if user owns the game)"""
    s = select(GameModel).where(
        GameModel.game_id == game_id, GameModel.user_id == current_user.id
    )
    result = await db.execute(s)
    db_game = result.scalar_one_or_none()
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    await db.delete(db_game)
    await db.commit()

    return {"message": "Game deleted"}


@router.delete("/")
async def delete_all_games(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete all games for the current user"""

    s = select(GameModel).where(GameModel.user_id == current_user.id)
    await db.delete(s)
    await db.commit()

    return {"message": "All games deleted"}
