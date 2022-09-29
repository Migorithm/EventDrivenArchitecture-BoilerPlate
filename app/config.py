import os
import sys
import typing
from base64 import b64encode
from datetime import timedelta
from typing import Literal

import boto3
from passlib.context import CryptContext
from pydantic import BaseSettings

# Env


def get_secret() -> None:
    secret_name: str | None = None
    if STAGE == "ci-testing":
        secret_name = "ci-test/harmony/review"
    elif STAGE == "develop":
        secret_name = "dev/harmony/review"
    elif STAGE == "staging":
        secret_name = "stage/harmony/review"
    elif STAGE == "production":
        secret_name = "prod/harmony/review"

    region_name = "ap-northeast-2"
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        raise e
    else:
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
            os.environ.update(eval(secret))


STAGE = typing.cast(
    Literal["local", "ci-testing", "testing", "develop", "staging", "production"],
    os.getenv("STAGE"),
)


if STAGE not in ("local", "testing", "ci-testing"):
    get_secret()

if "pytest" in sys.modules:
    STAGE = "testing"

if not STAGE:
    raise Exception("STAGE is not defined")


class InterServiceURL(BaseSettings):
    INTERNAL_TRANSACTION_URL: str = ""
    TRANSACTION_REVIEW_SKU_URL: str = ""


INTER_SERVICE_URL = InterServiceURL()


class PersistentDB(BaseSettings):
    POSTGRES_SERVER: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_PORT: str = ""
    POSTGRES_PROTOCOL: str = ""


PERSISTENT_DB = PersistentDB()

SQLALCHEMY_DATABASE_URI = "{}://{}:{}@{}:{}/{}".format(
    PERSISTENT_DB.POSTGRES_PROTOCOL,
    PERSISTENT_DB.POSTGRES_USER,
    PERSISTENT_DB.POSTGRES_PASSWORD,
    PERSISTENT_DB.POSTGRES_SERVER,
    PERSISTENT_DB.POSTGRES_PORT,
    PERSISTENT_DB.POSTGRES_DB,
)


class RedisSetting(BaseSettings):
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379


REDIS_SETTING = RedisSetting()

BACKEND_CORS_ORIGINS = eval(os.getenv("BACKEND_CORS_ORIGINS", "['*']"))
API_V1_STR: str = "/api/v1"
# Temporary login
INTERNAL_AUTH_SERVICE_URL = os.getenv("INTERNAL_AUTH_SERVICE_URL", "http://auth-api")
API_V1_TOKEN_URL: str = os.getenv("API_V1_TOKEN_URL", "")

SECRET_KEY: str = os.getenv("SECRET_KEY", "")
JWT_AUTH = {
    "SECRET_KEY": b64encode(SECRET_KEY.encode()).decode(),
    "PUBLIC_KEY": None,
    "PRIVATE_KEY": None,
    "ALGORITHM": "HS256",
    "AUTHORIZATION_TYPE": "Bearer",
    "VERIFY": True,
    "VERIFY_EXPIRATION": True,
    "EXPIRATION_DELTA": timedelta(minutes=30),
    "REFRESH_EXPIRATION_DELTA": timedelta(days=15),
    "ALLOW_REFRESH": True,
}
TZ: str = os.getenv("TZ", "UTC")
PWD_CTX = CryptContext(schemes="bcrypt")


def verify_unsigned_secret_key(plain_password: str, hashed_password: str) -> bool:
    return PWD_CTX.verify(plain_password, hashed_password)
