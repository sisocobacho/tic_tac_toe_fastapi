from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class GameStateResponse(BaseModel):
    game_id: str
    board: List[str]
    current_player: str
    winner: Optional[str] = None
    game_over: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    

class GameSummaryResponse(BaseModel):
    game_id: str
    current_player: str
    winner: Optional[str] = None
    game_over: bool
    created_at: datetime
    updated_at: datetime

