from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.response import success_response
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    PasswordResetCodeRequest,
    PasswordResetConfirmRequest,
    ChangePasswordRequest,
)
from app.services.auth_service import AuthService
from app.services.password_reset_service import (
    PasswordResetService,
    RESET_CODE_SENT_MESSAGE,
)

router = APIRouter(tags=["认证"])
service = AuthService()
reset_service = PasswordResetService()


@router.post("/register", status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await service.register(db, data)
    return success_response(
        data=UserResponse.model_validate(user).model_dump(),
        msg="注册成功",
        code=201,
    )


@router.post("/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    token = await service.login(db, data)
    return success_response(
        data=token.model_dump(),
        msg="登录成功",
    )


@router.post("/refresh")
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token = await service.refresh_token(db, data.refresh_token)
    return success_response(
        data=token.model_dump(),
        msg="Token 刷新成功",
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(),
        msg="获取用户信息成功",
    )


@router.post("/password-reset/request")
async def request_password_reset_code(
    data: PasswordResetCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    await reset_service.request_code(db, data)
    return success_response(msg=RESET_CODE_SENT_MESSAGE)


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    data: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    await reset_service.confirm(db, data)
    return success_response(msg="密码重置成功，请使用新密码登录")


@router.put("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.change_password(db, current_user.id, data)
    return success_response(msg="密码修改成功")
