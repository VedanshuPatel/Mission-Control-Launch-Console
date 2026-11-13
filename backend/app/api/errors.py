"""Map validation errors to plain-English {errors:[{field,message}]}."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


def _messages_from_validation(exc: RequestValidationError | ValidationError) -> list[dict]:
    errors: list[dict] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = "body"
        for part in loc:
            if part in {"body", "query", "path"}:
                continue
            field = str(part)
            break
        msg = str(err.get("msg", "invalid"))
        # Pydantic prefixes "Value error, "
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        # Missing field
        if err.get("type") == "missing":
            msg = f"{field} is required"
        errors.append({"field": field, "message": msg})
    return errors


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"errors": _messages_from_validation(exc)})
