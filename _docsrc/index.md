---
title: `rslv` Generic Resolver Service
---

`rslv` implements a resolver service. That is, given an identifier string, the service returns information about the identifier or redirects to the known location of the identified resource.

`rslv` is written in Python and requires python version 3.9 or later. `rslv` may be run as a command line application or more typically, as a web service. 

## Installation

`rslv` is not (currently) available on PyPi and so is installed directly or indirectly from GitHub. It is generally a good practice to install in a virtual environment to avoid dependency conflicts.

Installation with `pip`:
```
python -m pip install git+https://github.com/CDLUC3/resolver.git
```

or including as a dependecy in another project `poetry`:
```
poetry add git+https://github.com/CDLUC3/resolver.git
```

## Configuration

Configuration of `rslv` involves optionally setting a couple of operating parameters and setting up the identifier definitions.
The identifier definitions provide the instructions for how identifier resolution requests should be redirected and also defines the metadata associated with each identifier.

See [configuration](configuration.md) for details.

## Deployment

`rslv` is implemented using FastAPI, and is deployed in an [ASGI](https://asgi.readthedocs.io/en/latest/) environment.

For development purposes, `rslv` may be run from the command line to provide a test server at http://localhost:8000/:
```
python rslv/app.py
```

A production deployment should use an ASGI server such as [Uvicorn](https://www.uvicorn.org/) or [Nginx Unit](https://unit.nginx.org/). Uivcorn will generally be deployed behind another web server such as Apache or Nginx whereas `Unit` may be deployed as the web server. 



Alternatively, `rslv` may be deployed to a cloud provider such as `Vercel`




## 