from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["认证"])
service = AuthService()


@router.post("/register", response_model=dict, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await service.register(db, data)
    return {"data": UserResponse.model_validate(user)}


@router.post("/login", response_model=dict)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    token = await service.login(db, data)
    return {"data": token.model_dump()}


@router.post("/refresh", response_model=dict)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token = await service.refresh_token(db, data.refresh_token)
    return {"data": token.model_dump()}


@router.get("/me", response_model=dict)
async def get_me(current_user: User = Depends(get_current_user)):
    return {"data": UserResponse.model_validate(current_user)}
