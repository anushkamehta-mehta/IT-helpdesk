"""Application settings, loaded from environment variables / the root .env file."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str
    db_password: str  # no default on purpose: must come from the environment
    db_name: str = "it_helpdesk"
    # The server's CA certificate (e.g. Aiven's ca.pem), to connect over verified SSL as hosted MySQL
    # such as Aiven requires. Either a file path (relative paths are from the project root) or the
    # certificate text itself ("-----BEGIN CERTIFICATE-----..."), e.g. pasted into a Vercel env var.
    db_ssl_ca: str = ""

    jwt_secret: str  # no default on purpose
    jwt_expire_minutes: int = 60
    cookie_secure: bool = False

    cors_origins: str = ""

    # Outgoing email (SMTP). Leave smtp_host empty to turn email off.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""  # sender address; defaults to smtp_user
    # Brevo (brevo.com) HTTPS email API. When set it is used instead of SMTP, e.g. on Render's free
    # plan, which blocks SMTP ports. SMTP_FROM must then be a sender verified in Brevo.
    brevo_api_key: str = ""
    mail_from_name: str = "IT Helpdesk"
    # Public address of the helpdesk, used for links in emails.
    app_base_url: str = "http://127.0.0.1:8000"

    @property
    def database_url(self) -> URL:
        # URL.create safely escapes special characters in the password
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def db_ssl_ca_pem(self) -> str | None:
        """The CA certificate when given as text rather than as a file path."""
        value = self.db_ssl_ca.strip().replace("\\n", "\n")  # tolerate a one-line value with literal \n
        return value if value.startswith("-----BEGIN") else None

    @property
    def db_ssl_ca_path(self) -> Path | None:
        if not self.db_ssl_ca or self.db_ssl_ca_pem:
            return None
        path = Path(self.db_ssl_ca)
        return path if path.is_absolute() else ROOT_DIR / path

    @property
    def database_label(self) -> str:
        """Where the data lives, without the password, e.g. for logs."""
        return f"{self.db_user}@{self.db_host}:{self.db_port}/{self.db_name} (SSL {'on' if self.db_ssl_ca else 'off'})"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
