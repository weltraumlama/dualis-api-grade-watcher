from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    dualis_user: str
    dualis_password: str
    dualis_api_url: str = "http://127.0.0.1:8000"
    refresh_interval_seconds: int = 300
    port: int = 8001
    semester_id: str = ""
    webhook_url: str = "http://127.0.0.1:8002/new-grade"
    state_file: str = "grades_state.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
