'''
`rslv` - General purpose identifier resolver service

This software is developed with support from the [California Digital Library](https://cdlib.org/).

This software implements a general purpose identifier resolver. Given an identifier string,
it will parse the identifier, locate a corresponding definition, and either present information
about the identifier or redirect the user to the registered target.
'''
import logging.config

import rslv.config
import fastapi
import fastapi.responses
import fastapi.middleware.cors

import rslv.routers.resolver

__version__ = "0.3.0"

logging.config.fileConfig("rslv/logging.conf", disable_existing_loggers=False)
L = logging.getLogger("resolver")

# Intialize the application
app = fastapi.FastAPI(
    title="RSLV",
    description=__doc__,
    version=__version__,
    contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/mit/",
    },
    # Need to add this here because adding to the router has no effect.
    lifespan=rslv.routers.resolver.resolver_lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api",
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
    return fastapi.responses.RedirectResponse(url='/api')

@app.get(
    "/favicon.ico",
    include_in_schema=False
)
async def get_favicon():
    raise fastapi.HTTPException(status_code=404, detail="Not found")


app.include_router(rslv.routers.resolver.router)


if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run("app:app", port=rslv.config.settings.port, host=rslv.config.settings.host, reload=True)
    except ImportError as e:
        print("Unable to run as uvicorn is not available.")
        print(e)
