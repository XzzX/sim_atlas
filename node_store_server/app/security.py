import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

header_scheme = APIKeyHeader(name="X-API-KEY")

write_token = secrets.token_hex(16)

print(f"Write API Key: {write_token}")


def has_write_access(key: str = Depends(header_scheme)):
    if key != write_token:
        raise HTTPException(status_code=400, detail="invalid write API key")
    return {"key": key}
