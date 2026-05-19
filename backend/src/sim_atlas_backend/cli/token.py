import argparse

import jwt

from ..exceptions import MissingConfigError
from ..settings import load_settings


def create_access_token(jwt_secret_key: str, jwt_algorithm: str, creator_name: str, creator_email: str):
    to_encode = {"creator_name": creator_name, "creator_email": creator_email}
    encoded_jwt = jwt.encode(
        to_encode, jwt_secret_key, algorithm=jwt_algorithm
    )
    return encoded_jwt


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a JWT access token for the sim-atlas API."
    )
    parser.add_argument("name", help="Creator name")
    parser.add_argument("email", help="Creator e-mail address")
    args = parser.parse_args()
    
    try:
        settings = load_settings()
    except MissingConfigError:
        return
    
    print(create_access_token(settings.jwt_secret_key, settings.jwt_algorithm, args.name, args.email))


if __name__ == "__main__":
    main()
