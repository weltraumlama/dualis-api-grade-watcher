from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    telegram_chat_id: str
    port: int = 8002

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
