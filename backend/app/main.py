from contextlib import asynccontextmanager
import json
import logging
import asyncio
import uuid
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from shopify_app import connector as existing_shopify
from .api import router, actor_for
from . import schema as t
from .db import Database
from .errors import ApplicationError
from .settings import Settings, BACKEND, REPOSITORY
from .payment_sources import RazorpayReadOnly
from .whatsapp_transport import TwilioTransport
from .together_provider import TogetherProvider

log = logging.getLogger("rpa.requests")


def create_app(settings=None, shopify=None, razorpay=None, twilio=None, together=None):
    settings = settings or Settings.from_environment()
    db = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(application):
        from .automation import background
        task=asyncio.create_task(background(db,application.state.together)) if db.sessions else None
        try:yield
        finally:
            if task:
                task.cancel()
                try:await task
                except asyncio.CancelledError:pass
            await db.close()

    application = FastAPI(title="Repeat Purchase Agent",
                          docs_url="/api/docs", openapi_url="/api/openapi.json",
                          redoc_url=None, lifespan=lifespan)
    application.state.settings = settings
    application.state.db = db
    application.state.shopify = shopify or existing_shopify
    application.state.razorpay = razorpay or RazorpayReadOnly()
    application.state.twilio = twilio or TwilioTransport()
    application.state.together = together or TogetherProvider()
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.hosts))

    def error_response(request, status, code, message):
        return JSONResponse(status_code=status, content={"error": {
            "code": code, "message": message, "retryable": status in (429, 502, 503, 504),
            "correlation_id": str(request.state.correlation_id)}})

    @application.middleware("http")
    async def perimeter(request, call_next):
        request.state.correlation_id = uuid.uuid4()
        origin = request.headers.get("origin")
        if (origin and origin not in settings.origins) or request.headers.get("sec-fetch-site") == "cross-site":
            response = error_response(request, 403, "ORIGIN_DENIED", "Use the local application origin.")
        else:
            response = await call_next(request)
        response.headers.update({
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
            "X-Correlation-ID": str(request.state.correlation_id),
        })
        # Never log cookies, URL query strings, request bodies or exception strings.
        log.info(json.dumps({"event": "http.request", "method": request.method,
                             "path": request.url.path, "status": response.status_code,
                             "correlation_id": str(request.state.correlation_id)}))
        return response

    @application.exception_handler(ApplicationError)
    async def application_error(request, error):
        return error_response(request, error.status, error.code, error.message)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request, error):
        return error_response(request, 503, "DATABASE_UNAVAILABLE", "The database or schema is unavailable. Check local setup.")

    @application.exception_handler(HTTPException)
    async def provider_error(request, error):
        return error_response(request, error.status_code, "PROVIDER_ERROR" if error.status_code >= 500 else "REQUEST_REJECTED",
                              str(error.detail))

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Pydantic error objects can echo passwords; return field locations only.
        response = error_response(request, 422, "INVALID_INPUT", "Check the submitted fields.")
        data = json.loads(response.body)
        data["error"]["field_errors"] = [{"field": ".".join(map(str, e["loc"])),
                                          "type": e["type"]} for e in error.errors()]
        return JSONResponse(status_code=422, content=data)

    @application.get("/")
    async def preview():
        return RedirectResponse("/app/", status_code=307)

    @application.get("/foundation")
    async def review():
        return FileResponse(BACKEND / "review" / "index.html")

    @application.get("/api/health")
    async def compatibility_health():
        c = application.state.shopify
        return {"service": "local-shopify-connector", "configured": bool(c.client_id and c.secret),
                "shop": c.shop, "read_only": True}

    @application.get("/api/shopify/snapshot")
    async def compatibility_snapshot(request: Request):
        # Preserve the snapshot shape; the new server requires a member session.
        async with db.unit_of_work() as session:
            actor = await actor_for(request, session)
            permitted = await session.scalar(sa.select(t.connectors.c.id).select_from(
                t.connectors.join(t.workspaces, sa.and_(
                    t.workspaces.c.id == t.connectors.c.workspace_id,
                    t.workspaces.c.merchant_id == t.connectors.c.merchant_id
                )).join(t.memberships, t.memberships.c.merchant_id == t.connectors.c.merchant_id)
            ).where(t.memberships.c.user_id == actor["user_id"],
                t.workspaces.c.environment == "development", t.connectors.c.provider == "shopify",
                t.connectors.c.provider_account_id == application.state.shopify.shop))
            if not permitted:
                raise ApplicationError(404, "NOT_FOUND", "No Shopify development connection in your workspaces.")
        return jsonable_encoder(await application.state.shopify.snapshot())

    application.include_router(router)
    application.mount("/app", StaticFiles(directory=REPOSITORY / "frontend" / "app" / "dist",
                                          html=True, check_dir=False), name="merchant-app")
    application.mount("/frontend", StaticFiles(directory=REPOSITORY / "frontend"), name="frontend")
    return application


app = create_app()
