"""
Script for basic management of the pid configuration sqlite instance.
"""
import logging
import logging.config
import sys
import click
import sqlalchemy

import rslv.lib_rslv.piddefine
from rslv.config import settings

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
    L = get_logger()
    ctx.ensure_object(dict)
    ctx.obj["engine"] = sqlalchemy.create_engine(settings.db_connection_string, pool_pre_ping=True)
    return 0

@main.command("initialize")
@click.pass_context
@click.argument("description")
def initialize_configuration(ctx, description):
    rslv.lib_rslv.piddefine.create_database(
        ctx.obj["engine"],
        description
    )

@main.command("add")
@click.pass_context
@click.option("-s", "--scheme", help="Scheme value for entry")
@click.option("-p", "--prefix", help="Prefix value for entry", default=None)
@click.option("-v", "--value", help="infix value for entry", default=None)
@click.option("-t", "--target", help="Pattern for creation of target values", default="{pid}")
@click.option("-c", "--canonical", help="Pattern for creation of canonical values", default="{pid}")
def add_entry(ctx, scheme, prefix, value, target, canonical):
    session = rslv.lib_rslv.piddefine.get_session(ctx.obj["engine"])
    try:
        cfg = rslv.lib_rslv.piddefine.SQLPidConfig(session)
        entry = rslv.lib_rslv.piddefine.PidDefinition(
            scheme=scheme,
            prefix=prefix,
            value=value,
            target=target,
            canonical=canonical
        )
        result = cfg.add(entry)
        print(result)
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())