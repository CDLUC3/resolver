import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    # env_prefix provides the environment variable prefix
    # for overriding these settings with env vars.
    model_config = pydantic_settings.SettingsConfigDict(env_prefix='n2t_')
    host: str = "localhost"
    port: int = 8000
    protocol: str = "http"
    db_connection_string:str = "sqlite:///data/pid_config.sqlite"


settings = Settings()
