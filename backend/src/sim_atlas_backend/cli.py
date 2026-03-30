import argparse

import jwt
from dotenv import dotenv_values

config = dotenv_values(".env")
JWT_SECRET_KEY = config["JWT_SECRET_KEY"]
JWT_ALGORITHM = config["JWT_ALGORITHM"]


def create_access_token(creator_name: str, creator_email: str):
    if JWT_SECRET_KEY is None:
        raise ValueError("JWT_SECRET_KEY must be set in the .env file")

    if JWT_ALGORITHM is None:
        raise ValueError("JWT_ALGORITHM must be set in the .env file")

    to_encode = {"creator_name": creator_name, "creator_email": creator_email}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a JWT access token for the sim-atlas API."
    )
    parser.add_argument("name", help="Creator name")
    parser.add_argument("email", help="Creator e-mail address")
    args = parser.parse_args()
    print(create_access_token(args.name, args.email))


if __name__ == "__main__":
    main()
