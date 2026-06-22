from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth import create_token, verify_credentials

router = APIRouter(prefix="/api", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    if not verify_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return TokenResponse(access_token=create_token(body.username))
