'''
MicroN2T - General purpose identifier resolver service
'''
import logging.config

import config
import fastapi
import fastapi.responses
import fastapi.middleware.cors

import routers.resolver

__version__ = "0.2.0"
URL_SAFE_CHARS = ":/%#?=@[]!$&'()*+,;"

logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
L = logging.getLogger("resolver")

# Intialize the application
app = fastapi.FastAPI(
    title="Micro N2T",
    description=__doc__,
    version=__version__,
    contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/mit/",
    },
    # Need to add this here because adding to the router has no effect.
    lifespan=routers.resolver.resolver_lifespan
)

# Enables CORS for UIs on different domains
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "HEAD",
    ],
    allow_headers=[
        "*",
    ],
)


@app.get(
    "/",
    include_in_schema=False
)
async def redirect_docs():
    return fastapi.responses.RedirectResponse(url='/docs')


app.include_router(routers.resolver.router)


if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run("app:app", port=config.settings.port, host=config.settings.host)
    except ImportError as e:
        print("Unable to run as uvicorn is not available.")
        print(e)
