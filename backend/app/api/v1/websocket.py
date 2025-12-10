import json
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from backend.app.models.game import GameModel, GameType
from backend.app.services.user import get_current_user_from_token
from backend.database import get_session_factory
from contextlib import asynccontextmanager
from backend.app.services.game import TicTacToeGame

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, game_id: str, user_id: int):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = set()
        self.active_connections[game_id].add(websocket)
        self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, game_id: str, user_id: int):
        if game_id in self.active_connections:
            self.active_connections[game_id].discard(websocket)
            if not self.active_connections[game_id]:
                del self.active_connections[game_id]

        if (
            user_id in self.user_connections
            and self.user_connections[user_id] == websocket
        ):
            del self.user_connections[user_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_game(self, game_id: str, message: dict):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Remove disconnected clients
                    self.active_connections[game_id].discard(connection)


manager = ConnectionManager()


@asynccontextmanager
async def get_db_for_websocket():
    """Get database session for WebSocket connections."""
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@router.websocket("/ws/{game_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    game_id: str,
    token: str,
    # db: AsyncSession = Depends(get_db_session)
):
    """WebSocket endpoint for real-time multiplayer games"""
    # Create database session for this WebSocket connection
    try:
        # Authenticate user
        async with get_db_for_websocket() as db:
            user = await get_current_user_from_token(token, db)
            if not user:
                await websocket.close(code=1008)
                return

            # Get game
            s = select(GameModel).where(GameModel.game_id == game_id)
            result = await db.execute(s)
            db_game = result.scalar_one_or_none()

            if not db_game:
                await websocket.close(code=1008)
                return

        # Check if user has access to the game
        if db_game.game_type == GameType.VS_COMPUTER:
            if db_game.user_id != user.id:
                await websocket.close(code=1008)
                return
        else:
            if db_game.player_x != user.id and db_game.player_o != user.id:
                await websocket.close(code=1008)
                return

        # Connect to game room
        await manager.connect(websocket, game_id, user.id)

        # Send initial game state
        game = await TicTacToeGame.from_db_model(db_game)
        initial_state = await game.get_game_state()

        await manager.send_personal_message(
            {
                "type": "connected",
                "game_id": game_id,
                "data": {
                    "message": f"Connected to game {game_id}",
                    "game_state": initial_state,
                    "user_id": user.id,
                    "username": user.username,
                },
            },
            websocket,
        )

        # Notify other players
        await manager.broadcast_to_game(
            game_id,
            {
                "type": "player_joined",
                "game_id": game_id,
                "data": {"user_id": user.id, "username": user.username},
            },
        )

        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "make_move":
                    position = data.get("position")

                    # Refresh game state from database
                    async with get_db_for_websocket() as db:
                        user = await get_current_user_from_token(token, db)
                        if not user:
                            await websocket.close(code=1008)
                            return

                        # Get game
                        s = select(GameModel).where(GameModel.game_id == game_id)
                        result = await db.execute(s)
                        db_game = result.scalar_one_or_none()
                    if not db_game:
                        continue
                    game = await TicTacToeGame.from_db_model(db_game)
                    state = await game.get_game_state()

                    # Validate move
                    if db_game.game_over:
                        await manager.send_personal_message(
                            {
                                "type": "error",
                                "game_id": game_id,
                                "data": {"message": "Game is over"},
                            },
                            websocket,
                        )
                        continue

                    if db_game.current_player == "X" and db_game.player_x != user.id:
                        await manager.send_personal_message(
                            {
                                "type": "error",
                                "game_id": game_id,
                                "data": {"message": "Not your turn"},
                            },
                            websocket,
                        )
                        continue

                    if db_game.current_player == "O" and db_game.player_o != user.id:
                        await manager.send_personal_message(
                            {
                                "type": "error",
                                "game_id": game_id,
                                "data": {"message": "Not your turn"},
                            },
                            websocket,
                        )
                        continue

                    # Validate position
                    if position is None or position < 0 or position > 8:
                        await manager.send_personal_message(
                            {
                                "type": "error",
                                "game_id": game_id,
                                "data": {"message": "Invalid position"},
                            },
                            websocket,
                        )
                        continue

                    # Get current board state
                    current_board = json.loads(db_game.board)
                    if current_board[position] != " ":
                        await manager.send_personal_message(
                            {
                                "type": "error",
                                "game_id": game_id,
                                "data": {"message": "Position already taken"},
                            },
                            websocket,
                        )
                        continue
                    # Make the move
                    if await game.make_move(position, db, user.id):
                        # Get updated game state
                        updated_state = await game.get_game_state()

                        # Broadcast updated game state to all players
                        await manager.broadcast_to_game(
                            game_id,
                            {
                                "type": "game_state",
                                "game_id": game_id,
                                "data": updated_state,
                            },
                        )

                        # If game is finished, notify players
                        if game.game_over:
                            winner_message = "Game over! It's a tie!"
                            if game.winner:
                                winner_message = f"Game over! Winner: {game.winner}"

                            await manager.broadcast_to_game(
                                game_id,
                                {
                                    "type": "game_over",
                                    "game_id": game_id,
                                    "data": {
                                        "winner": game.winner,
                                        "message": winner_message,
                                    },
                                },
                            )

                elif message_type == "chat_message":
                    # Broadcast chat message to all players in the game
                    message_content = data.get("message", "").strip()
                    if message_content:
                        await manager.broadcast_to_game(
                            game_id,
                            {
                                "type": "chat_message",
                                "game_id": game_id,
                                "data": {
                                    "user_id": user.id,
                                    "username": user.username,
                                    "message": message_content,
                                },
                            },
                        )

                elif message_type == "get_state":
                    # Get current game state and send to requesting player
                    s = select(GameModel).where(GameModel.game_id == game_id)
                    result = await db.execute(s)
                    db_game = result.scalar_one_or_none()

                    if db_game:
                        game = await TicTacToeGame.from_db_model(db_game)
                        game_state = await game.get_game_state()

                        await manager.send_personal_message(
                            {
                                "type": "game_state",
                                "game_id": game_id,
                                "data": game_state,
                            },
                            websocket,
                        )

        except WebSocketDisconnect:
            manager.disconnect(websocket, game_id, user.id)

            # Notify other players
            await manager.broadcast_to_game(
                game_id,
                {
                    "type": "player_left",
                    "game_id": game_id,
                    "data": {"user_id": user.id, "username": user.username},
                },
            )

    except Exception:
        if "user" in locals():
            manager.disconnect(websocket, game_id, user.id)
