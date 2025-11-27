import pytest
from fastapi.testclient import TestClient
from main import app, TicTacToeGame

client = TestClient(app)

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
    # Valid move
    assert game.make_move(0) == True
    assert game.board[0] == "X"
    # Invalid move (position already taken)
    assert game.make_move(0) == False

def test_tie_game():
    """Test tie game detection"""
    game = TicTacToeGame("test_tie")
    # Create a tie scenario
    game.board = ["X", "O", "X", "X", "O", "O", "O", "X", "X"]
    assert game.is_board_full() == True
    assert game.check_winner("X") == False
    assert game.check_winner("O") == False

def test_create_game():
    """Test creating a new game"""
    response = client.post("/game")
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert data["board"] == [" " for _ in range(9)]
    assert data["current_player"] == "X"
    assert data["winner"] is None
    assert data["game_over"] is False

def test_get_game_state():
    """Test getting game state"""
    # Create a game first
    create_response = client.post("/game")
    game_id = create_response.json()["game_id"]
    
    # Get game state
    response = client.get(f"/game/{game_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == game_id

def test_get_nonexistent_game():
    """Test getting a non-existent game"""
    response = client.get("/game/nonexistent")
    assert response.status_code == 404

def test_make_valid_move():
    """Test making a valid move"""
    create_response = client.post("/game")
    game_id = create_response.json()["game_id"]
    
    response = client.post(f"/game/{game_id}/move/0")
    assert response.status_code == 200
    data = response.json()
    # After human move, computer should have moved too
    assert data["board"][0] == "X"
    assert "O" in data["board"]  # Computer should have made a move

def test_make_invalid_move():
    """Test making an invalid move"""
    create_response = client.post("/game")
    game_id = create_response.json()["game_id"]
    
    # Make a move
    client.post(f"/game/{game_id}/move/0")
    
    # Try to make the same move again
    response = client.post(f"/game/{game_id}/move/0")
    assert response.status_code == 400

def test_make_move_out_of_bounds():
    """Test making a move with invalid position"""
    create_response = client.post("/game")
    game_id = create_response.json()["game_id"]
    
    response = client.post(f"/game/{game_id}/move/9")
    assert response.status_code == 400

def test_delete_game():
    """Test deleting a game"""
    create_response = client.post("/game")
    game_id = create_response.json()["game_id"]
    
    response = client.delete(f"/game/{game_id}")
    assert response.status_code == 200
    
    # Verify game is deleted
    response = client.get(f"/game/{game_id}")
    assert response.status_code == 404
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
