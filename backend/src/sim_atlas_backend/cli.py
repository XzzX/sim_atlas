import argparse

import jwt

from .settings import settings


def create_access_token(creator_name: str, creator_email: str):
    to_encode = {"creator_name": creator_name, "creator_email": creator_email}
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
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
