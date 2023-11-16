# rslv

FastAPI implementation of an identifier resolver.

The `rslv`  implementation provides a generic identifier resolution service that may be adapted 
to support different schemes. The base requirement is that identifiers are of the 
form `scheme:content` where `scheme` is a scheme name (e.g. "doi" or "ark") and `content` is the 
value of the identifier (e.g. `10.12345/foo` or `99999/fd99`).

## Operation

There are three main components to the `rslv` application: the web application, the configuration database, and a script for managing content in the configuraton database. The web application component is intended to be run within the context of an ASGI server such as [uvicorn](https://www.uvicorn.org/), [unit](https://unit.nginx.org/), [daphne](https://github.com/django/daphne/), or [hypercorn](https://pgjones.gitlab.io/hypercorn/).

```
@startuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml
Component(rslv, rslv, "Resolver service")
ComponentDb(config, config, "Indentifier definitions")
Component(manage, manage, "Management script")
Component_Ext(server, server, "ASGI Server")

Rel(manage, config, "Updates")
Rel(rslv, config, "Uses")
Rel(server, rslv, "Serves", "http")
@enduml
```
Components of `rslv`. The database (typically sqlite) is managed by the `manage.py` script. An ASGI server makes `rslv` accessible over http.

### Managing identifier definitions

An identifier definition specifies the properties of an identifier and the action to be taken. Definitions may match on the scheme

### Development instance with `uvicorn`

With `uvicorn` installed, a development instance of `rslv` can be started from the commandline like:

```
python rslv/app.py
```

The service may be accessed at http://localhost:8000/