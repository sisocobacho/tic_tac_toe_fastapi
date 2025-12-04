from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status
from backend.database import get_db
from app.services.user import (
    get_password_hash,
    get_user_by_username,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.models.user import User
from app import schema
from backend.config import settings

router = APIRouter()


# Authentication endpoints
@router.post("/auth/register", response_model=schema.UserResponse)
async def register(user: schema.UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user"""
    # Check if username already exists
    db_user = await get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    # db.commit()
    # db.refresh(db_user)

    print(type(db_user.created_at))
    return schema.UserResponse(
        id=db_user.id, username=db_user.username, created_at=db_user.created_at
    )


@router.post("/auth/login", response_model=schema.Token)
async def login(user_login: schema.UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schema.UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return schema.UserResponse(
        id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at,
    )
