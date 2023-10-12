"""
Implements a custom logger in JSON-lines format for FastAPI.

Borrowed various pieces from:
- https://stackoverflow.com/questions/70891687/how-do-i-get-my-fastapi-applications-console-log-in-json-format-with-a-differen
- https://www.sheshbabu.com/posts/fastapi-structured-json-logging/
"""
import json
import logging
import sys
import time
import fastapi
import starlette.background
import starlette.middleware.base


class JsonFormatter(logging.Formatter):
    converter = time.gmtime

    def __init__(self, formatter):
        super().__init__(formatter)

    # Format the time for this log event
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            # Default UTC ISO8601 format of "YYYY-mm-ddTHH:MM:SS.fffZ"
            t = time.strftime("%Y-%m-%dT%H:%M:%S", ct)
            s = f"{t}.{record.msecs:03.0f}Z"
        return s

    def format(self, record):
        logging.Formatter.format(self, record)
        res = {
            "t": record.asctime,
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra_info"):
            res["req"] = (record.extra_info["req"],)
            res["res"] = record.extra_info["res"]
        return json.dumps(res)


class LogMiddleware(starlette.middleware.base.BaseHTTPMiddleware):
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.pop("logger")
        super().__init__(*args, **kwargs)

    def get_extra_info(self, request: fastapi.Request, response: fastapi.Response):
        fwd = request.headers.get(
            "forward", request.headers.get("x-forwarded-for", None)
        )
        return {
            "req": {
                "url": request.url.path,
                "headers": {
                    "host": request.headers["host"],
                    "user_agent": request.headers["user-agent"],
                    "accept": request.headers["accept"],
                },
                "method": request.method,
                "http_version": request.scope["http_version"],
                "client_addr": request.client.host,
                "forward": fwd,
            },
            "res": {
                "status_code": response.status_code,
            },
        }

    def write_log_data(self, request, response):
        self.logger.info(
            f"{request.method} {request.url.path}",
            extra={"extra_info": self.get_extra_info(request, response)},
        )

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.background = starlette.background.BackgroundTask(
            self.write_log_data, request, response
        )
        return response

def get_logger(name, level=logging.INFO, log_filename=None, log_stderr=True):
    formatter = JsonFormatter("%(asctime)s")
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if log_filename is not None:
        handler = logging.FileHandler(log_filename)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    if log_stderr or log_filename is None:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
