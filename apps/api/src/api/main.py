from __future__ import annotations

import asyncio
import signal

import tornado.httpserver
import tornado.web

from api.auth.handlers import (
    LogoutAuthHandler,
    PasswordLoginHandler,
    StartAuthHandler,
    VerifyAuthHandler,
)
from api.db import dispose_db, init_db
from api.graphql.handler import GraphQLHandler
from api.logging_config import configure_logging, get_logger
from api.rest.health import HealthHandler
from api.rest.me import MeHandler
from api.rest.tasks import NoteSummaryRunHandler
from api.rest.uploads import UploadSignHandler
from api.settings import get_settings
from api.tasks.base import recover_abandoned_task_runs

logger = get_logger(__name__)


def create_app() -> tornado.web.Application:
    settings = get_settings()
    init_db(settings)

    return tornado.web.Application(
        [
            (r"/api/healthz", HealthHandler),
            (r"/api/auth/start", StartAuthHandler),
            (r"/api/auth/verify", VerifyAuthHandler),
            (r"/api/auth/password-login", PasswordLoginHandler),
            (r"/api/auth/logout", LogoutAuthHandler),
            (r"/api/me", MeHandler),
            (r"/api/tasks/note-summary/run", NoteSummaryRunHandler),
            (r"/api/uploads/sign", UploadSignHandler),
            (r"/graphql", GraphQLHandler),
        ],
        debug=settings.app_env == "local",
        cookie_secret=settings.session_secret,
    )


async def _handle_sigterm(
    sig: signal.Signals,
    server: tornado.httpserver.HTTPServer,
    shutdown_event: asyncio.Event,
) -> None:
    logger.info(
        "shutdown signal received",
        event_type="app.event",
        severity="INFO",
        signal=sig.name,
    )
    server.stop()
    # Allow in-flight requests to drain
    await asyncio.sleep(5)
    await dispose_db()
    shutdown_event.set()


async def run() -> None:
    configure_logging()
    settings = get_settings()
    app = create_app()
    await recover_abandoned_task_runs()
    server = tornado.httpserver.HTTPServer(app)
    server.bind(port=settings.app_port, address=settings.app_host)
    server.start(1)
    logger.info(
        "api started",
        event_type="app.event",
        severity="INFO",
        host=settings.app_host,
        port=settings.app_port,
    )

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _on_signal(s: signal.Signals) -> None:
        asyncio.ensure_future(_handle_sigterm(s, server, shutdown_event))

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _on_signal, sig)
    await shutdown_event.wait()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
