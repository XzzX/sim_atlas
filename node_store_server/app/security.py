import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

header_scheme = APIKeyHeader(name="X-API-KEY")

read_token = secrets.token_hex(16)
readwrite_token = secrets.token_hex(16)

print(f"Read API Key: {read_token}")
print(f"ReadWrite API Key: {readwrite_token}")


def has_read_access(key: str = Depends(header_scheme)):
    if key != read_token and key != readwrite_token:
        raise HTTPException(status_code=400, detail="invalid read API key")
    return {"key": key}


def has_write_access(key: str = Depends(header_scheme)):
    if key != readwrite_token:
        raise HTTPException(status_code=400, detail="invalid write API key")
    return {"key": key}
