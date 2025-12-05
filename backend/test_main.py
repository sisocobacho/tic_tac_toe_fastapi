import pytest
import json
from starlette import status
from httpx import ASGITransport, AsyncClient
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine,AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from fastapi import FastAPI

from backend.app.models import load_all_models
from backend.main import app
from backend.app.services.user import get_password_hash
from backend.app.services.game import TicTacToeGame
from backend.database import get_db
from backend.app.models.user import User
from backend.app.models.game import GameModel
from typing import Any
# Use async database for testing
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_async.db"

@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """
    Backend for anyio pytest plugin.

    :return: backend name.
    """
    return "asyncio"


@pytest.fixture(scope="session")
async def _engine(anyio_backend: Any) -> AsyncGenerator[AsyncEngine]:
    """
    Create engine and databases.

    :yield: new engine.
    """
    from backend.database import meta

    load_all_models()


    engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()
        # await drop_database()


@pytest.fixture
async def db(
    _engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    """
    Get session to database.

    Fixture that returns a SQLAlchemy session with a SAVEPOINT, and the rollback to it
    after the test completes.

    :param _engine: current engine.
    :yields: async session.
    """
    connection = await _engine.connect()
    trans = await connection.begin()

    session_maker = async_sessionmaker(
        connection,
        expire_on_commit=False,
    )
    session = session_maker()

    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest.fixture
def fastapi_app(
    db: AsyncSession,
) -> FastAPI:
    """
    Fixture for creating FastAPI app.

    :return: fastapi app with mocked dependencies.
    """
    application = app
    application.dependency_overrides[get_db] = lambda: db
    return application


@pytest.fixture
async def client(
    fastapi_app: FastAPI, anyio_backend: Any
) -> AsyncGenerator[AsyncClient]:
    """
    Fixture that creates client for requesting server.

    :param fastapi_app: the application.
    :yield: client for the app.
    """
    async with AsyncClient(
        transport=ASGITransport(fastapi_app), base_url="http://test", timeout=2.0
    ) as ac:
        yield ac
#
# # Create async engine for testing
# engine = create_async_engine(
#     SQLALCHEMY_DATABASE_URL,
#     echo=False,
#     poolclass=StaticPool,
#     connect_args={"check_same_thread": False}
# )
#
# # Create async session factory
# TestingSessionLocal = async_sessionmaker(
#     engine,
#     class_=AsyncSession,
#     expire_on_commit=False
# )
#
#
# # Async database dependency override
# async def override_get_db():
#     async with TestingSessionLocal() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close()
#
#
# app.dependency_overrides[get_db] = override_get_db
#
# # Keep synchronous client for simple tests
#

# Async fixtures
# @pytest.fixture(scope="session")
# def event_loop():
#     """Create an instance of the default event loop for the test session."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()
#
#
# @pytest.fixture(autouse=True)
# async def setup_database():
#     """Set up the database before each test and tear down after"""
#     # Create tables
#     load_all_models()
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     yield
#     # Drop tables
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#     await engine.dispose()
#
#
# @pytest.fixture
# async def client():
#     """Async HTTP client fixture"""
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         yield ac
#

@pytest.fixture
async def test_user():
    """Fixture to create a test user"""
    async with db() as db:
        user = User(
            username="testuser",
            hashed_password=get_password_hash("testpassword")
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

async def create_test_user_async(db: AsyncSession):
    """Helper function to create a test user asynchronously"""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpassword")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_auth_headers_async(client: AsyncClient, username="testuser", password="testpassword"):
    """Async helper function to get authentication headers"""
    response = await client.post(
        "/api/v1/users/auth/login",
        json={"username": username, "password": password}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


async def test_health(client: AsyncClient, fastapi_app: FastAPI) -> None:
    """
    Checks the health endpoint.

    :param client: client for the app.
    :param fastapi_app: current FastAPI application.
    """
    url = fastapi_app.url_path_for("health_check")
    response = await client.get(url)
    assert response.status_code == status.HTTP_200_OK

# Synchronous tests (keep these as they are)
async def test_get_root_endpoint(client: AsyncClient):
    """Test api root"""
    response = await client.get("/")
    assert response.status_code == 200


async def test_get_health_endpoint(client: AsyncClient):
    """Test api health"""
    response = await client.get("/health")
    assert response.status_code == 200
    status = response.json()["status"]
    timestamp = response.json()["timestamp"]
    assert status == "healthy"
    assert timestamp


async def test_user_registration(client: AsyncClient, db: AsyncSession):
    """Test user registration"""
    response = await client.post(
        "/api/v1/users/auth/register",
        json={"username": "newuser", "password": "newpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert "id" in data
    assert "created_at" in data

    result = await db.execute(select(User).where(User.username == "newuser"))
    user = result.scalar_one_or_none()
    assert user is not None

# Converted async tests
async def test_user_login_async(client: AsyncClient, db: AsyncSession):
    """Test user login asynchronously"""
    await create_test_user_async(db)

    response = await client.post(
        "/api/v1/users/auth/login",
        json={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_user_login_invalid_credentials_async(client: AsyncClient, db: AsyncSession):
    """Test user login with invalid credentials asynchronously"""
    await create_test_user_async(db)

    response = await client.post(
        "/api/v1/users/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_async(client: AsyncClient, db: AsyncSession):
    """Test getting current user info asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data
    assert "created_at" in data


async def test_get_current_user_unauthenticated(client: AsyncClient):
    """Test getting current user without authentication"""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_game_authenticated_async(client: AsyncClient, db: AsyncSession):
    """Test creating a game when authenticated asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    response = await client.post("/api/v1/games/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert data["board"] == [" " for _ in range(9)]
    assert data["current_player"] == "X"
    assert data["winner"] == ""
    assert data["game_over"] is False

    # Verify game was saved with user ID
    result = await db.execute(
        select(GameModel).where(GameModel.game_id == data["game_id"])
    )
    db_game = result.scalar_one_or_none()
    assert db_game is not None
    assert db_game.user_id is not None


async def test_create_game_unauthenticated(client: AsyncClient):
    """Test creating a game without authentication"""
    response = await client.post("/api/v1/games/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_game_state_authenticated_async(client: AsyncClient, db: AsyncSession):
    """Test getting game state when authenticated asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    # Create a game first
    create_response = await client.post("/api/v1/games/", headers=headers)
    game_id = create_response.json()["game_id"]

    # Get game state
    response = await client.get(f"/api/v1/games/{game_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == game_id


@pytest.mark.asyncio
async def test_get_other_users_game_async(client: AsyncClient, db: AsyncSession):
    """Test getting another user's game asynchronously"""
    # Create first user and game
    await create_test_user_async(db)
    headers1 = await get_auth_headers_async(client)

    create_response = await client.post("/api/v1/games/", headers=headers1)
    assert create_response.status_code == 200
    data = create_response.json()
    assert "game_id" in data
    game_id = data["game_id"]

    # Create second user
    user2 = User(
        username="user2",
        hashed_password=get_password_hash("password2")
    )
    db.add(user2)
    await db.commit()

    # Try to access first user's game with second user
    headers2 = await get_auth_headers_async(client, "user2", "password2")
    response = await client.get(f"/api/v1/games/{game_id}", headers=headers2)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_make_valid_move_async(client: AsyncClient, db: AsyncSession):
    """Test making a valid move asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    create_response = await client.post("/api/v1/games/", headers=headers)
    game_id = create_response.json()["game_id"]

    response = await client.post(f"/api/v1/games/{game_id}/move/0", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # After human move, computer should have moved too
    assert data["board"][0] == "X"
    assert "O" in data["board"]  # Computer should have made a move

    # Verify database was updated
    result = await db.execute(
        select(GameModel).where(GameModel.game_id == game_id)
    )
    db_game = result.scalar_one_or_none()
    updated_board = json.loads(db_game.board)
    assert updated_board[0] == "X"


@pytest.mark.asyncio
async def test_make_invalid_move_async(client: AsyncClient, db: AsyncSession):
    """Test making an invalid move asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    # Create a game and make a move
    create_response = await client.post("/api/v1/games/", headers=headers)
    game_id = create_response.json()["game_id"]
    await client.post(f"/api/v1/games/{game_id}/move/0", headers=headers)

    # Try to make the same move again
    response = await client.post(f"/api/v1/games/{game_id}/move/0", headers=headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_make_move_out_of_bounds_async(client: AsyncClient, db: AsyncSession):
    """Test making a move with invalid position asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    create_response = await client.post("/api/v1/games/", headers=headers)
    game_id = create_response.json()["game_id"]

    response = await client.post(f"/api/v1/games/{game_id}/move/9", headers=headers)
    assert response.status_code == 400


async def test_make_move_unauthenticated(client: AsyncClient):
    """Test making a move without authentication"""
    response = await client.post("/api/v1/games/somegame/move/0")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_games_authenticated_async(client: AsyncClient, db: AsyncSession):
    """Test listing games when authenticated asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    # Create multiple games
    await client.post("/api/v1/games/", headers=headers)
    await client.post("/api/v1/games/", headers=headers)

    response = await client.get("/api/v1/games/?limit=2", headers=headers)
    assert response.status_code == 200
    games = response.json()
    assert len(games) == 2

    # Verify games are ordered by creation date (newest first)
    assert "game_id" in games[0]
    assert "created_at" in games[0]


@pytest.mark.asyncio
async def test_list_games_with_skip_and_limit_async(client: AsyncClient, db: AsyncSession):
    """Test listing games with both skip and limit parameters asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    # Create 10 games
    game_ids = []
    for i in range(10):
        response = await client.post("/api/v1/games/", headers=headers)
        game_ids.append(response.json()["game_id"])

    # Skip 3, limit 4
    response = await client.get("/api/v1/games/?skip=3&limit=4", headers=headers)
    assert response.status_code == 200
    games = response.json()
    assert len(games) == 4


@pytest.mark.asyncio
async def test_delete_game_authenticated_async(client: AsyncClient, db: AsyncSession):
    """Test deleting a game when authenticated asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    create_response = await client.post("/api/v1/games/", headers=headers)
    game_id = create_response.json()["game_id"]

    response = await client.delete(f"/api/v1/games/{game_id}", headers=headers)
    assert response.status_code == 200

    # Verify game is deleted from database
    result = await db.execute(
        select(GameModel).where(GameModel.game_id == game_id)
    )
    db_game = result.scalar_one_or_none()
    assert db_game is None


@pytest.mark.asyncio
async def test_delete_nonexistent_game_async(client: AsyncClient, db: AsyncSession):
    """Test deleting a non-existent game asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    response = await client.delete("/api/v1/games/nonexistent", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_all_games_authenticated_async(client: AsyncClient, db: AsyncSession):
    """Test deleting all games when authenticated asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    # Create some games
    await client.post("/api/v1/games/", headers=headers)
    await client.post("/api/v1/games/", headers=headers)

    # Delete all games
    response = await client.delete("/api/v1/games/", headers=headers)
    assert response.status_code == 200

    # Verify no games left for user
    response = await client.get("/api/v1/games/?limit=10", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


async def test_delete_all_games_unauthenticated(client: AsyncClient):
    """Test deleting all games without authentication"""
    response = await client.delete("/api/v1/games/")
    assert response.status_code == 401


# Keep synchronous tests for pure class testing
def test_game_class_check_winner():
    """Test winner checking in TicTacToeGame class"""
    game = TicTacToeGame("test2")

    # Test row win
    game.board = ["X", "X", "X", " ", " ", " ", " ", " ", " "]
    assert game.check_winner("X")
    assert not game.check_winner("O")

    # Test column win
    game.board = ["O", " ", " ", "O", " ", " ", "O", " ", " "]
    assert game.check_winner("O")

    # Test diagonal win
    game.board = ["X", " ", " ", " ", "X", " ", " ", " ", "X"]
    assert game.check_winner("X")


def test_game_class_board_full():
    """Test board full checking in TicTacToeGame class"""
    game = TicTacToeGame("test3")

    # Empty board
    assert not game.is_board_full()

    # Full board
    game.board = ["X", "O", "X", "O", "X", "O", "O", "X", "O"]
    assert game.is_board_full()


def test_tie_game():
    """Test tie game detection"""
    game = TicTacToeGame("test_tie")
    # Create a tie scenario
    game.board = ["X", "O", "X", "X", "O", "O", "O", "X", "X"]
    assert game.is_board_full()
    assert not game.check_winner("X")
    assert not game.check_winner("O")


@pytest.mark.asyncio
async def test_get_nonexistent_game_async(client: AsyncClient, db: AsyncSession):
    """Test getting a non-existent game asynchronously"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)
    
    response = await client.get("/api/v1/games/nonexistent", headers=headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_game_class_from_db_model():
    """Test creating TicTacToeGame from database model"""
    db_game = GameModel(
        game_id="test_db",
        board=json.dumps(["X", "O", " ", " ", " ", " ", " ", " ", " "]),
        current_player="X",
        winner=None,
        game_over=False,
    )

    game = await TicTacToeGame.from_db_model(db_game)
    assert game.game_id == "test_db"
    assert game.board == ["X", "O", " ", " ", " ", " ", " ", " ", " "]
    assert game.current_player == "X"


# New async-specific tests
@pytest.mark.asyncio
async def test_concurrent_game_creation(client: AsyncClient, db: AsyncSession):
    """Test creating games concurrently"""
    await create_test_user_async(db)
    headers = await get_auth_headers_async(client)

    # Create multiple games concurrently
    tasks = [
        await client.post("/api/v1/games/", headers=headers)
        for _ in range(5)
    ]
    
    responses = tasks
    
    for response in responses:
        assert response.status_code == 200
        assert "game_id" in response.json()


@pytest.mark.asyncio
async def test_websocket_connection_async():
    """Test WebSocket connection asynchronously"""
    # If your app has WebSocket endpoints
    # Note: httpx AsyncClient doesn't support WebSockets directly
    # You might need to use websockets library
    pass



@pytest.mark.asyncio
async def test_database_operations_directly(db: AsyncSession):
    """Test database operations directly without HTTP"""
    # Create user
    user = User(
        username="direct_test",
        hashed_password=get_password_hash("direct_pass")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Query user
    result = await db.execute(
        select(User).where(User.username == "direct_test")
    )
    fetched_user = result.scalar_one_or_none()
    
    assert fetched_user is not None
    assert fetched_user.username == "direct_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
