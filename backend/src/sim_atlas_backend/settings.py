from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    jwt_secret_key: str
    jwt_algorithm: str
    llm_api_key: str
    llm_api_url: str
    llm_embedding_model: str
    llm_chat_model: str
    voyage_api_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
