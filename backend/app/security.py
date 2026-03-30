from typing import Annotated

import jwt
from dotenv import dotenv_values
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

config = dotenv_values(".env")
JWT_SECRET_KEY = config["JWT_SECRET_KEY"]
JWT_ALGORITHM = config["JWT_ALGORITHM"]

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


class Creator(BaseModel):
    name: str
    email: str


async def get_current_user(access_token: Annotated[str, Depends(api_key_header)]):
    if JWT_SECRET_KEY is None:
        raise ValueError("JWT_SECRET_KEY must be set in the .env file")

    if JWT_ALGORITHM is None:
        raise ValueError("JWT_ALGORITHM must be set in the .env file")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        creator_name = payload.get("creator_name")
        if creator_name is None:
            raise credentials_exception
        creator_email = payload.get("creator_email")
        if creator_email is None:
            raise credentials_exception
    except InvalidTokenError as e:
        raise credentials_exception from e

    return Creator(name=creator_name, email=creator_email)
