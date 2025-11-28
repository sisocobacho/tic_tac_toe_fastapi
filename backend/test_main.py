import pytest
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db, Base, User, GameModel, TicTacToeGame, get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    """Set up the database before each test and tear down after"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables
    Base.metadata.drop_all(bind=engine)

def create_test_user():
    """Helper function to create a test user"""
    db = next(override_get_db())
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpassword")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_auth_headers(username="testuser", password="testpassword"):
    """Helper function to get authentication headers"""
    response = client.post("/auth/login", json={
        "username": username,
        "password": password
    })
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}

def test_get_root_endpoint():
    """Test api root"""
    response = client.get("/")
    assert response.status_code == 200

def test_get_health_endpoint():
    """Test api health"""
    response = client.get("/health")
    assert response.status_code == 200
    status = response.json()["status"]
    timestamp = response.json()["timestamp"]
    assert status == "healthy"
    assert timestamp

def test_user_registration():
    """Test user registration"""
    response = client.post("/auth/register", json={
        "username": "newuser",
        "password": "newpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert "id" in data
    assert "created_at" in data
    
    # Verify user was saved to database
    db = next(override_get_db())
    user = db.query(User).filter(User.username == "newuser").first()
    assert user is not None

def test_user_login():
    """Test user login"""
    create_test_user()
    
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_user_login_invalid_credentials():
    """Test user login with invalid credentials"""
    create_test_user()
    
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_get_current_user():
    """Test getting current user info"""
    create_test_user()
    headers = get_auth_headers()
    
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data
    assert "created_at" in data

def test_get_current_user_unauthenticated():
    """Test getting current user without authentication"""
    response = client.get("/users/me")
    assert response.status_code == 401

def test_create_game_authenticated():
    """Test creating a game when authenticated"""
    create_test_user()
    headers = get_auth_headers()
    
    response = client.post("/game", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert data["board"] == [" " for _ in range(9)]
    assert data["current_player"] == "X"
    assert data["winner"] is None
    assert data["game_over"] is False
    
    # Verify game was saved with user ID
    db = next(override_get_db())
    db_game = db.query(GameModel).filter(GameModel.game_id == data["game_id"]).first()
    assert db_game is not None
    assert db_game.user_id is not None

def test_create_game_unauthenticated():
    """Test creating a game without authentication"""
    response = client.post("/game")
    assert response.status_code == 401

def test_get_game_state_authenticated():
    """Test getting game state when authenticated"""
    create_test_user()
    headers = get_auth_headers()
    
    # Create a game first
    create_response = client.post("/game", headers=headers)
    game_id = create_response.json()["game_id"]
    
    # Get game state
    response = client.get(f"/game/{game_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == game_id

def test_get_game_state_authenticated():
    """Test getting game state when authenticated"""
    create_test_user()
    headers = get_auth_headers()
    
    # Create a game first
    create_response = client.post("/game", headers=headers)
    game_id = create_response.json()["game_id"]
    
    # Get game state
    response = client.get(f"/game/{game_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == game_id

def test_get_other_users_game():
    """Test getting another user's game"""
    # Create first user and game
    user1 = create_test_user()
    headers1 = get_auth_headers()
    
    create_response = client.post("/game", headers=headers1)
    game_id = create_response.json()["game_id"]
    
    # Create second user
    db = next(override_get_db())
    user2 = User(
        username="user2",
        hashed_password=get_password_hash("password2")
    )
    db.add(user2)
    db.commit()
   
    # Try to access first user's game with second user
    headers2 = get_auth_headers("user2", "password2")
    response = client.get(f"/game/{game_id}", headers=headers2)
    assert response.status_code == 404

def test_make_valid_move():
    """Test making a valid move"""
    create_test_user()
    headers = get_auth_headers()
    
    create_response = client.post("/game", headers=headers)
    game_id = create_response.json()["game_id"]
    
    response = client.post(f"/game/{game_id}/move/0", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # After human move, computer should have moved too
    assert data["board"][0] == "X"
    assert "O" in data["board"]  # Computer should have made a move
    
    # Verify database was updated
    db = next(override_get_db())
    db_game = db.query(GameModel).filter(GameModel.game_id == game_id).first()
    updated_board = json.loads(db_game.board)
    assert updated_board[0] == "X"

def test_make_invalid_move():
    """Test making an invalid move"""
    create_test_user()
    headers = get_auth_headers()
    
    # Create a game and make a move
    create_response = client.post("/game", headers=headers)
    game_id = create_response.json()["game_id"]
    client.post(f"/game/{game_id}/move/0", headers=headers)
    
    # Try to make the same move again
    response = client.post(f"/game/{game_id}/move/0", headers=headers)
    assert response.status_code == 400

def test_make_move_out_of_bounds():
    """Test making a move with invalid position"""
    create_test_user()
    headers = get_auth_headers()
    
    create_response = client.post("/game", headers=headers)
    game_id = create_response.json()["game_id"]
    
    response = client.post(f"/game/{game_id}/move/9", headers=headers)
    assert response.status_code == 400

def test_make_move_unauthenticated():
    """Test making a move without authentication"""
    response = client.post("/game/somegame/move/0")
    assert response.status_code == 401

def test_list_games_authenticated():
    """Test listing games when authenticated"""
    create_test_user()
    headers = get_auth_headers()
    
    # Create multiple games
    client.post("/game", headers=headers)
    client.post("/game", headers=headers)
    
    response = client.get("/games", headers=headers)
    assert response.status_code == 200
    games = response.json()
    assert len(games) == 2
    
    # Verify games are ordered by creation date (newest first)
    assert "game_id" in games[0]
    assert "created_at" in games[0]

def test_delete_game_authenticated():
    """Test deleting a game when authenticated"""
    create_test_user()
    headers = get_auth_headers()
    
    create_response = client.post("/game", headers=headers)
    game_id = create_response.json()["game_id"]
    
    response = client.delete(f"/game/{game_id}", headers=headers)
    assert response.status_code == 200
    
    # Verify game is deleted from database
    db = next(override_get_db())
    db_game = db.query(GameModel).filter(GameModel.game_id == game_id).first()
    assert db_game is None

def test_delete_nonexistent_game():
    """Test deleting a non-existent game"""
    create_test_user()
    headers = get_auth_headers()
    
    response = client.delete("/game/nonexistent", headers=headers)
    assert response.status_code == 404

def test_delete_all_games_authenticated():
    """Test deleting all games when authenticated"""
    create_test_user()
    headers = get_auth_headers()
    
    # Create some games
    client.post("/game", headers=headers)
    client.post("/game", headers=headers)
    
    # Delete all games
    response = client.delete("/games", headers=headers)
    assert response.status_code == 200
    
    # Verify no games left for user
    response = client.get("/games", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_delete_all_games_unauthenticated():
    """Test deleting all games without authentication"""
    response = client.delete("/games")
    assert response.status_code == 401

def test_game_class_check_winner():
    """Test winner checking in TicTacToeGame class"""
    game = TicTacToeGame("test2")
    
    # Test row win
    game.board = ["X", "X", "X", " ", " ", " ", " ", " ", " "]
    assert game.check_winner("X") == True
    assert game.check_winner("O") == False
    
    # Test column win
    game.board = ["O", " ", " ", "O", " ", " ", "O", " ", " "]
    assert game.check_winner("O") == True
    
    # Test diagonal win
    game.board = ["X", " ", " ", " ", "X", " ", " ", " ", "X"]
    assert game.check_winner("X") == True

def test_game_class_board_full():
    """Test board full checking in TicTacToeGame class"""
    game = TicTacToeGame("test3")
    
    # Empty board
    assert game.is_board_full() == False
    
    # Full board
    game.board = ["X", "O", "X", "O", "X", "O", "O", "X", "O"]
    assert game.is_board_full() == True

def test_game_class_make_move():
    """Test making moves in TicTacToeGame class"""
    game = TicTacToeGame("test4")
    db = next(override_get_db())
    # Valid move
    assert game.make_move(0, db) == True
    assert game.board[0] == "X"
    # Invalid move (position already taken)
    assert game.make_move(0, db) == False

def test_tie_game():
    """Test tie game detection"""
    game = TicTacToeGame("test_tie")
    # Create a tie scenario
    game.board = ["X", "O", "X", "X", "O", "O", "O", "X", "X"]
    assert game.is_board_full() == True
    assert game.check_winner("X") == False
    assert game.check_winner("O") == False

def test_get_nonexistent_game():
    """Test getting a non-existent game"""
    create_test_user()
    headers = get_auth_headers()
    response = client.get("/game/nonexistent", headers=headers)
    assert response.status_code == 404

def test_game_class_from_db_model():
    """Test creating TicTacToeGame from database model"""
    db_game = GameModel(
        game_id="test_db",
        board=json.dumps(["X", "O", " ", " ", " ", " ", " ", " ", " "]),
        current_player="X",
        winner=None,
        game_over=False
    )
    
    game = TicTacToeGame.from_db_model(db_game)
    assert game.game_id == "test_db"
    assert game.board == ["X", "O", " ", " ", " ", " ", " ", " ", " "]
    assert game.current_player == "X"

    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
