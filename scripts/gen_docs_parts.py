"""
Used to generate parts of the documentation
"""

import json
import logging
import click
from py_markdown_table.markdown_table import markdown_table
import sqlalchemy
import rslv.lib_rslv
import rslv.lib_rslv.piddefine

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "FATAL": logging.CRITICAL,
    "CRITICAL": logging.CRITICAL,
}

EXAMPLE_PIDS = [
    "foo",
    "foo:1234",
    "foo:1234/bar",
    "ark:/12345/foo?baz",
    "doi:10.12345/foo?baz",
    "IGSN:AU1243",
    "orcid:0000-0002-5355-2576",
    "z017/biomodels.db:BIOMD0000000048",
]

DEFINITIONS = [
    rslv.lib_rslv.piddefine.PidDefinitionSQL(
        scheme="ark"
    ),
    rslv.lib_rslv.piddefine.PidDefinitionSQL(
        scheme="ark",
        prefix="99999",
    ),
    rslv.lib_rslv.piddefine.PidDefinitionSQL(
        scheme="ark",
        prefix="99999",
        value="fk4"
    ),
    rslv.lib_rslv.piddefine.PidDefinitionSQL(
        scheme="ark",
        prefix="99999",
        value="fk"
    ),
    rslv.lib_rslv.piddefine.PidDefinitionSQL(
        scheme="ark",
        prefix="example",
        synonym_for="ark:99999"
    ),
    rslv.lib_rslv.piddefine.PidDefinitionSQL(
        scheme="bark",
        synonym_for="ark:"
    ),
]

def initialize():
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    rslv.lib_rslv.piddefine.create_database(engine, "Examples")
    catalog = rslv.lib_rslv.piddefine.get_catalog(engine)
    for defn in DEFINITIONS:
        catalog.add_as_definition(defn)
    return engine


def split_examples():
    parsed = []
    for pid in EXAMPLE_PIDS:
        ppid = rslv.lib_rslv.ParsedPID(pid=pid)
        ppid.split()
        parsed.append(ppid.model_dump(mode="json", exclude={"clean_value", }))
    for p in parsed:
        for k,v in p.items():
            if v is None:
                p[k] = ""
            else:
                p[k] = f"`{v}`"
    print(markdown_table(parsed).set_params(row_sep='markdown', quote=False).get_markdown())


@click.group()
@click.pass_context
@click.option("-V", "--verbosity", default="ERROR", help="Logging level")
def main(ctx, verbosity):
    verbosity = verbosity.upper()
    logging.basicConfig(level=LOG_LEVELS.get(verbosity, "INFO"))
    L = logging.getLogger()
    ctx.obj["L"] = L
    ctx.ensure_object(dict)
    ctx.obj["engine"] = initialize()


@main.command("split")
@click.pass_context
def split_examples_cli(ctx):
    split_examples()


if __name__ == "__main__":
    main()