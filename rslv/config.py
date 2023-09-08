import os.path
import pydantic_settings

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

class Settings(pydantic_settings.BaseSettings):
    # env_prefix provides the environment variable prefix
    # for overriding these settings with env vars.
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="rslv_")
    host: str = "localhost"
    port: int = 8000
    protocol: str = "http"
    db_connection_string: str = f"sqlite:///{BASE_FOLDER}/data/pid_config.sqlite"
    log_config: str = os.path.join(BASE_FOLDER, "logging.conf")
    static_dir: str = os.path.join(BASE_FOLDER, "static")
    template_dir: str = os.path.join(BASE_FOLDER, "templates")


settings = Settings()
