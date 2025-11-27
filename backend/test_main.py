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
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
