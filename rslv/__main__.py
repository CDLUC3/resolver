"""
Script for basic management of the pid configuration sqlite instance.
"""

import json
import logging
import logging.config
import sys
import click
import sqlalchemy

import rslv.lib_rslv.piddefine
import rslv.config

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(name)s:%(levelname)s: %(message)s",
            "dateformat": "%Y-%m-%dT%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "": {
            "handlers": [
                "console",
            ],
            "level": "INFO",
            "propogate": False,
        },
    },
}

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}


def get_logger():
    return logging.getLogger("rslv")


@click.group()
@click.pass_context
@click.option("-V", "--verbosity", default="ERROR", help="Logging level")
def main(ctx, verbosity):
    verbosity = verbosity.upper()
    logging_config["loggers"][""]["level"] = verbosity
    logging.config.dictConfig(logging_config)
    settings = rslv.config.load_settings()
    ctx.ensure_object(dict)
    ctx.obj["engine"] = sqlalchemy.create_engine(
        settings.db_connection_string, pool_pre_ping=True
    )
    return 0


@main.command("initialize")
@click.pass_context
@click.argument("description")
def initialize_configuration(ctx, description):
    """Initializes an empty RSLV configuration database.

    The provided description is included in the metadata for the database.
    """
    rslv.lib_rslv.piddefine.create_database(ctx.obj["engine"], description)


@main.command("schemes")
@click.pass_context
def list_schemes(ctx):
    """List the schemes registered in the database."""
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        schemes = definitions.list_schemes()
        scheme_list = [s[0] for s in schemes]
        print(json.dumps(scheme_list, indent=2))
    finally:
        session.close()


@main.command("prefixes")
@click.pass_context
@click.argument("scheme")
def list_prefixes(ctx, scheme):
    """List the prefixes for the specified scheme."""
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        prefixes = definitions.list_prefixes(scheme)
        prefix_list = [p[0] for p in prefixes]
        print(json.dumps(prefix_list, indent=2))
    finally:
        session.close()


@main.command("values")
@click.pass_context
@click.argument("scheme")
@click.argument("prefix")
def list_value(ctx, scheme, prefix):
    """List the values of the specified scheme, prefix combination."""
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        prefixes = definitions.list_values(scheme, prefix)
        prefix_list = [p[0] for p in prefixes]
        print(json.dumps(prefix_list, indent=2))
    finally:
        session.close()


@main.command("add")
@click.pass_context
@click.option("-s", "--scheme", help="Scheme value for entry")
@click.option("-p", "--prefix", help="Prefix value for entry", default=None)
@click.option("-v", "--value", help="infix value for entry", default=None)
@click.option(
    "-t", "--target", help="Pattern for creation of target values", default="{pid}"
)
@click.option(
    "-r",
    "--redirect",
    help="HTTP redirect status code",
    default=302,
    show_default=True,
    type=int,
)
@click.option(
    "-c",
    "--canonical",
    help="Pattern for creation of canonical values",
    default="{pid}",
)
@click.option(
    "-y", "--synonym", default=None, help="This entry is a synonym for this uniq value."
)
def add_entry(ctx, scheme, prefix, value, target, redirect, canonical, synonym):
    """
    Add an entry to the configuration database.
    """
    if redirect < 301 or redirect > 308:
        raise ValueError("Invalid redirect, must be between 301 and 308")
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        definitions = rslv.lib_rslv.piddefine.PidDefinitionCatalog(session)
        entry = rslv.lib_rslv.piddefine.PidDefinition(
            scheme=scheme,
            prefix=prefix,
            value=value,
            target=target,
            http_code=redirect,
            canonical=canonical,
            synonym_for=synonym,
        )
        result = definitions.add(entry)
        definitions.refresh_metadata()
        print(result)
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
