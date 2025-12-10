from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from enum import Enum


class GameType(str, Enum):
    VS_COMPUTER = "VS_COMPUTER"
    VS_PLAYER = "VS_PLAYER"


class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class GameStateResponse(BaseModel):
    game_id: str
    board: List[str]
    current_player: str
    winner: Optional[str] = None
    game_over: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    game_type: GameType
    game_status: GameStatus
    player_x: Optional[int] = None
    player_o: Optional[int] = None


class GameSummaryResponse(BaseModel):
    game_id: str
    current_player: str
    winner: Optional[str] = None
    game_over: bool
    created_at: datetime
    updated_at: datetime
    game_type: GameType
    game_status: GameStatus
    player_x: Optional[int] = None
    player_o: Optional[int] = None


class GameCreate(BaseModel):
    game_type: GameType = GameType.VS_COMPUTER


class GameJoin(BaseModel):
    game_id: str


class WebSocketMessage(BaseModel):
    type: str
    game_id: str
    data: dict
