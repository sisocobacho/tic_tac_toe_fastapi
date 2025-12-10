from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class GameType(enum.Enum):
    VS_COMPUTER = "VS_COMPUTER"
    VS_PLAYER = "VS_PLAYER"


class GameStatus(enum.Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class GameModel(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String, unique=True, index=True)
    board = Column(String)  # Store as JSON string
    current_player = Column(String, default="X")
    winner = Column(String, nullable=True)
    game_over = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    game_type = Column(Enum(GameType), default=GameType.VS_COMPUTER)
    game_status = Column(Enum(GameStatus), default=GameStatus.PLAYING)
    player_x = Column(Integer, ForeignKey("users.id"), nullable=True)
    player_o = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="games", foreign_keys=[user_id])
    player_x_user = relationship("User", foreign_keys=[player_x])
    player_o_user = relationship("User", foreign_keys=[player_o])
