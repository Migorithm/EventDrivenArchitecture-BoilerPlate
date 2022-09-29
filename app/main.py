import asyncio

import uvloop
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from harmony_core.exceptions import APIException as HarmonyCoreAPIException
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import config as settings
from app.entrypoints.dependencies import BOOTSTRAP
from app.entrypoints.exceptions import APIException, APIExceptionErrorCodes, APIExceptionTypes
from app.entrypoints.router import api_router

app = FastAPI(title="Harmony: Review Service", openapi_url=f"{settings.API_V1_STR}/openapi.json")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=APIExceptionErrorCodes.SCHEMA_ERROR[1],
        content={
            "error": {
                "message": "schema error. please refer to data for details",
                "type": APIExceptionTypes.DATA_VALIDATION,
                "code": APIExceptionErrorCodes.SCHEMA_ERROR[0],
                "data": exc.errors(),
            }
        },
    )


@app.exception_handler(APIException)
@app.exception_handler(HarmonyCoreAPIException)
async def api_exception_handler(request: Request, exc: APIException | HarmonyCoreAPIException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.get_exception_content().dict())


@app.on_event("startup")
async def configure_database_environment():
    if settings.STAGE not in ("testing", "ci-testing"):
        BOOTSTRAP.start_orm = True
        BOOTSTRAP.start_mappers()
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
