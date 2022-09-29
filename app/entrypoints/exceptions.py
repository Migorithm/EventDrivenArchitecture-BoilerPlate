from typing import Any

from fastapi import status
from pydantic import BaseModel


class ExceptionDetail(BaseModel):
    message: str
    type: str
    code: str
    data: Any


class APIExceptionSchema(BaseModel):
    error: ExceptionDetail


class APIExceptionErrorCodes:
    INTERNAL_ERROR = ("internal_error", status.HTTP_500_INTERNAL_SERVER_ERROR)
    BAD_REQUEST = ("bad_request", status.HTTP_400_BAD_REQUEST)
    FORBIDDEN = ("forbidden", status.HTTP_403_FORBIDDEN)
    OBJECT_NOT_FOUND = ("not_found", status.HTTP_404_NOT_FOUND)
    SCHEMA_ERROR = ("schema_error", status.HTTP_422_UNPROCESSABLE_ENTITY)

    INVALID_ARGUMENT = ("invalid", status.HTTP_403_FORBIDDEN)  # For pagination
    LOGIN_CREDENTIAL_INCORRECT = (
        "unauthorized",
        status.HTTP_401_UNAUTHORIZED,
    )  # For login
    OBJECT_DATA_ERROR = (
        "object_data_error",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    TOKEN_EXPIRED = ("expired_token", status.HTTP_401_UNAUTHORIZED)
    TOKEN_INVALID = ("token_invalid", status.HTTP_401_UNAUTHORIZED)

    ANONYMOUS_USER_PASSWORD_NOT_MATCHED = (
        "anonymous_user_password_error",
        status.HTTP_400_BAD_REQUEST,
    )
    ANONYMOUS_USER_PASSWORD_NOT_GIVEN = (
        "anonyous_user_password_not_given",
        status.HTTP_401_UNAUTHORIZED,
    )
    LOGIN_CHECKING_FAILED = (
        "Login Checker Not Working",
        status.HTTP_417_EXPECTATION_FAILED,
    )
    OUT_OF_STOCK = ("out_of_stock", status.HTTP_410_GONE)

    PG_RESULT_FAILED = ("pg_result_failed", status.HTTP_400_BAD_REQUEST)
    SKU_UPDATE_FAIL = ("sku_update_fail", status.HTTP_400_BAD_REQUEST)
    INCORRECT_REQUEST = ("INCORRECT_REQUEST", status.HTTP_400_BAD_REQUEST)
    PG_DATA_PARSING_ERROR = (
        "pg_data_parsing_error",
        status.HTTP_412_PRECONDITION_FAILED,
    )


class APIExceptionTypes:
    DATA_VALIDATION = "validation"
    INVALID_REQUEST = "invalid"


class APIException(Exception):
    def __init__(
        self,
        exception_code: tuple,
        error_type: str = APIExceptionTypes.INVALID_REQUEST,
        message: Any = "",
        data: Any = None,
    ):
        self.status_code = exception_code[1]
        self.error_code = exception_code[0]
        self.type = error_type or APIExceptionTypes.INVALID_REQUEST
        self.message = message
        self.data = data

    def get_exception_content(self) -> APIExceptionSchema:
        content = {
            "error": {
                "message": self.message,
                "type": self.type,
                "code": self.error_code,
                "data": self.data if self.data else [],
            }
        }

        return APIExceptionSchema(**content)
