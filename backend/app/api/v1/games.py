from fastapi import APIRouter, HTTPException, Depends
from backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy import select, delete
from backend.app.models.user import User
from backend.app.models.game import GameModel, GameType, GameStatus
from backend.app.services.user import get_current_user
from backend.app.services.game import TicTacToeGame, generate_game_id
from backend.app.schema.game import GameStateResponse, GameSummaryResponse, GameCreate
from typing import List

router = APIRouter()


@router.post(
    "/",
    response_model=GameStateResponse,
)
async def create_game(
    game_data: GameCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new Tic Tac Toe game"""
    game_id = await generate_game_id()

    if game_data.game_type == GameType.VS_COMPUTER:
        game = TicTacToeGame(game_id, game_type=game_data.game_type)
        await game.save_to_db(db, current_user.id)
    else:
        # For multiplayer games
        game = TicTacToeGame(
            game_id,
            game_type=game_data.game_type,
            game_status=GameStatus.WAITING,
            player_x=current_user.id,
        )
        await game.save_to_db(db, current_user.id)

    state = await game.get_game_state()
    return GameStateResponse(**state)


@router.post("/{game_id}/join", response_model=GameStateResponse)
async def join_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Join an existing multiplayer game"""
    s = select(GameModel).where(
        GameModel.game_id == game_id,
        GameModel.game_type == GameType.VS_PLAYER,
        GameModel.game_status == GameStatus.WAITING,
    )

    result = await db.execute(s)
    db_game = result.scalar_one_or_none()

    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found or not available")

    if db_game.player_x == current_user.id:
        raise HTTPException(status_code=400, detail="You are already in this game")

    if db_game.player_o is not None:
        raise HTTPException(status_code=400, detail="Game is full")

    # Join as player O
    db_game.player_o = current_user.id
    db_game.game_status = GameStatus.PLAYING
    db_game.current_player = "X"

    await db.commit()
    await db.refresh(db_game)

    game = await TicTacToeGame.from_db_model(db_game)
    state = await game.get_game_state()
    return GameStateResponse(**state)


@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game_state(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current game state"""
    s = select(GameModel).where(GameModel.game_id == game_id)

    result = await db.execute(s)
    db_game = result.scalar_one_or_none()

    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check if user has access to the game
    if db_game.game_type == GameType.VS_COMPUTER:
        if db_game.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        # For multiplayer games, check if user is player X or O
        if db_game.player_x != current_user.id and db_game.player_o != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

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
    """Make a move in the game"""
    if position < 0 or position > 8:
        raise HTTPException(status_code=400, detail="Invalid position")

    s = select(GameModel).where(GameModel.game_id == game_id)

    result = await db.execute(s)
    db_game = result.scalar_one_or_none()

    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check if user can make a move
    if db_game.game_type == GameType.VS_COMPUTER:
        if db_game.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        # For multiplayer games
        if db_game.current_player == "X" and db_game.player_x != current_user.id:
            raise HTTPException(status_code=403, detail="Not your turn")
        if db_game.current_player == "O" and db_game.player_o != current_user.id:
            raise HTTPException(status_code=403, detail="Not your turn")

    game = await TicTacToeGame.from_db_model(db_game)

    if game.game_over:
        raise HTTPException(status_code=400, detail="Game is over")

    if not await game.make_move(position, db, current_user.id):
        raise HTTPException(status_code=400, detail="Invalid move")

    state = await game.get_game_state()
    return GameStateResponse(**state)


@router.get("/multiplayer/available", response_model=List[GameSummaryResponse])
async def get_available_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of available multiplayer games"""
    s = select(GameModel).where(
        GameModel.game_type == GameType.VS_PLAYER,
        GameModel.game_status == GameStatus.WAITING,
        GameModel.player_x != current_user.id,
    )

    result = await db.execute(s)
    db_games = result.scalars().all()

    return [
        GameSummaryResponse(
            game_id=game.game_id,
            current_player=game.current_player,
            winner=game.winner,
            game_over=game.game_over,
            created_at=game.created_at.isoformat(),
            updated_at=game.updated_at.isoformat(),
            game_type=game.game_type,
            game_status=game.game_status,
            player_x=game.player_x,
            player_o=game.player_o,
        )
        for game in db_games
    ]


@router.get("/", response_model=List[GameSummaryResponse])
async def list_games(
    limit: int = 25,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all games for the current user"""
    s = (
        select(GameModel)
        .where(
            (GameModel.user_id == current_user.id)
            | (GameModel.player_x == current_user.id)
            | (GameModel.player_o == current_user.id)
        )
        .order_by(GameModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(s)
    db_games = result.scalars().all()

    return [
        GameSummaryResponse(
            game_id=game.game_id,
            current_player=game.current_player,
            winner=game.winner,
            game_over=game.game_over,
            created_at=game.created_at.isoformat(),
            updated_at=game.updated_at.isoformat(),
            game_type=game.game_type,
            game_status=game.game_status,
            player_x=game.player_x,
            player_o=game.player_o,
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
    s = select(GameModel).where(GameModel.game_id == game_id)
    result = await db.execute(s)
    db_game = result.scalar_one_or_none()

    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check permissions
    if db_game.game_type == GameType.VS_COMPUTER:
        if db_game.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        if db_game.player_x != current_user.id:
            raise HTTPException(status_code=403, detail="Only game creator can delete")

    await db.delete(db_game)
    await db.commit()

    return {"message": "Game deleted"}


@router.delete("/")
async def delete_all_games(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Delete all games for the current user"""
    s = delete(GameModel).where(
        (GameModel.user_id == current_user.id) | (GameModel.player_x == current_user.id)
    )
    await db.execute(s)
    await db.commit()

    return {"message": "All games deleted"}
