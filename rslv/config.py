import os.path
import typing

import pydantic_settings

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Settings(pydantic_settings.BaseSettings):
    """
    env_prefix provides the environment variable prefix
    for overriding these settings with env vars.
    e.g. RSLV_PORT=11000

    If the file .env is present in the working directory, values will be
    loaded from there.

    The .env file may be overridden by setting the environment variable
    RSLV_ENV_FILE with value being the path to a .env file.

    Order of precedence (highest to lowest):
      value set when instantiating the settings
      value set in environment variable
      value loaded from .env file
      default value provided here

    See: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
    """

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="rslv_", env_file=".env", env_file_encoding="utf-8"
    )
    host: str = "localhost"
    port: int = 8000
    protocol: str = "http"
    data_dir: str = os.path.join(BASE_FOLDER, "data")
    db_connection_string: str = f"sqlite:///{BASE_FOLDER}/data/pid_config.sqlite"
    static_dir: str = os.path.join(BASE_FOLDER, "static")
    template_dir: str = os.path.join(BASE_FOLDER, "templates")
    log_filename: typing.Optional[str] = None
    # Pattern to match this service URL endpoint, and if requests
    # match then trim the service url from the PID
    # For not uncommon situations where pid = "https://n2t.net/ark:/12345/foo"
    service_pattern: typing.Optional[str] = None
    # If pid value matches the definition value, then assume introspection.
    # Note that this should be set False on services offering one-to-one matching of
    # definitions to PIDs. For N2T and arks.org this sould be true to match legacy behavior.
    auto_introspection: bool = True


def load_settings():
    rslv_env_file = os.environ.get("RSLV_ENV_FILE", None)
    if rslv_env_file is not None:
        return Settings(_env_file=rslv_env_file)
    return Settings()
