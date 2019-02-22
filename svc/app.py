from aiohttp import web
from aiohttp.web_log import AccessLogger
from aiohttp_swagger import setup_swagger

import logging
import os

from .config import Config
from .core import getCore
from . import apiv1
from . import prometheus

class FilterAccessLogger(AccessLogger):
    """/health and /metrics filter

    Hidding those requests if we have a 200 OK when we are not in DEBUG
    """
    def log(self, request, response, time):
        if self.logger.level != logging.DEBUG \
            and response.status == 200 \
            and request.path in ['/health','/metrics']:

            return

        super().log(request, response, time)

class App:
    def __init__(self):
        # Config
        config = Config()

        # Logging
        logging_default_format = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"

        gunicorn_error = logging.getLogger("gunicorn.error")
        if len(gunicorn_error.handlers) != 0:
            # Seems to use gunicorn so we are using the provided logging level
            logging_level = gunicorn_error.level
        else:
            # using LOGGING_LEVEL env or fallback to DEBUG
            logging_level = int(os.environ.get("LOGGING_LEVEL", logging.DEBUG))

        logging.basicConfig(
            level=logging_level,
            format=logging_default_format
        )

        aiohttp_access = logging.getLogger("aiohttp.access")
        aiohttp_access.setLevel(logging_level)

        # Application
        self.app = web.Application(
            handler_args={
                'access_log_class': FilterAccessLogger
            }
        )
        apiv1.setup(self.app)
        prometheus.setup(self.app)
        setup_swagger(
            self.app,
            title=config["api"]["title"],
            api_version=config["api"]["version"],
            description=config["api"]["description"],
            swagger_url=config["api"]["swagger"]["url"],
            disable_ui=config["api"]["swagger"]["disable_ui"]
        )

        # Create and share the core for all APIs
        self.app["core"] = getCore(config=config)

    def run(self):
        web.run_app(self.app, host="0.0.0.0", port=5000)
