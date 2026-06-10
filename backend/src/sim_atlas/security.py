from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

from .settings import load_settings

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


class Creator(BaseModel):
    name: str
    email: str


async def get_current_user(access_token: Annotated[str, Depends(api_key_header)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    settings = load_settings()
    try:
        payload = jwt.decode(
            access_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        creator_name = payload.get("creator_name")
        if creator_name is None:
            raise credentials_exception
        creator_email = payload.get("creator_email")
        if creator_email is None:
            raise credentials_exception
    except InvalidTokenError as e:
        raise credentials_exception from e

    return Creator(name=creator_name, email=creator_email)
