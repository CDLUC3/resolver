import contextlib
import datetime
import typing
import sqlalchemy as sqla
import sqlalchemy.exc
import sqlalchemy.orm as sqlorm
import sqlalchemy.types
import sqlalchemy.sql.expression

import rslv.lib_rslv


def current_time():
    return datetime.datetime.now(tz=datetime.timezone.utc)


class Base(sqlorm.DeclarativeBase):
    pass


def calculate_definition_uniq(scheme, prefix, value):
    s = scheme if scheme is not None else ""
    p = prefix if prefix is not None else ""
    if value is not None:
        return f"{s}:{p}/{value}"
    return f"{s}:{p}"


def default_definition_uniq(context):
    """Create a single string representation of scheme:prefix/value.

    Used when adding a record to the config database to provide a unique
    label for each record based on its properties. This is used for
    synonym target lookup.
    """
    params = context.get_current_parameters()
    return calculate_definition_uniq(
        params["scheme"], params["prefix"], params["value"]
    )


class PidDefinition(Base):
    """Defines a database record that contains configuration for a
    particular combination of scheme:prefix/value.

    Each record is a potential redirect target and contains the information
    needed to handle a redirect or present metadata about the identifier.
    """

    __tablename__ = "piddef"

    uniq: sqlorm.Mapped[str] = sqlorm.mapped_column(
        doc="Unique key for this record, constructed from scheme:prefix/value",
        index=True,
        default=default_definition_uniq,
    )
    scheme: sqlorm.Mapped[str] = sqlorm.mapped_column(
        primary_key=True, doc="Lower case scheme name.", index=True
    )
    # Unique constraint is not enforced in sqlite if values are NULL, so set default to empty string
    prefix: sqlorm.Mapped[str] = sqlorm.mapped_column(
        primary_key=True, default="", doc="PID prefix portion match.", index=True
    )
    value: sqlorm.Mapped[str] = sqlorm.mapped_column(
        primary_key=True, default="", doc="PID value portion match.", index=True
    )
    splitter: sqlorm.Mapped[typing.Optional[str]] = sqlorm.mapped_column(
        doc="Optional alternate splitter function to use."
    )
    pid_model: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default="", doc="Identifier class to use for pids matching this definition."
    )
    # Note we can extend this to support alternate targets based on content negotiation
    # (media-type, profile, etc) by making this a dict and matching request
    # properties with the key, e.g. target = {"*":{"target":PATTERN, "http_code": 302}, ...}
    target: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default=None,
        doc="Pattern for target string generation.",
        nullable=True
    )
    http_code: sqlorm.Mapped[int] = sqlorm.mapped_column(
        default=302, doc="HTTP status code for response."
    )
    canonical: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default="{pid}", doc="Pattern for canonical string representation."
    )
    properties: sqlorm.Mapped[dict[str, typing.Any]] = sqlorm.mapped_column(
        type_=sqlalchemy.types.JSON,
        nullable=True,
        doc="Additional metadata properties associated with this entry.",
    )
    synonym_for: sqlorm.Mapped[str] = sqlorm.mapped_column(
        default=None,
        nullable=True,
        doc="Indicates this entry is a synonym for the referenced entry.",
    )

    # Only allow unique combinations of scheme, group, and value
    __table_args__ = (sqla.UniqueConstraint("scheme", "prefix", "value"),)

    @sqlalchemy.orm.validates("scheme")
    def validate_scheme(self, key, scheme):
        scheme = scheme.strip(":/ ")
        #if "/" in scheme:
        #    raise ValueError("'/' is not allowed in scheme.")
        if ":" in scheme:
            raise ValueError("':' is not allowed in scheme.")
        return scheme

    @sqlalchemy.orm.validates("prefix")
    def validate_prefix(self, key, prefix):
        if prefix is None:
            return ""
        prefix = prefix.strip("/ ")
        if "/" in prefix:
            raise ValueError("'/' is not allowed in prefix.")
        return prefix

    def update(self, entry: "PidDefinition") -> int:
        n_updates = 0
        # uniq, scheme, prefix, and value can not be updated.
        if entry.splitter is not None and entry.splitter != self.splitter:
            self.splitter = entry.splitter
            n_updates += 1
        if entry.pid_model is not None and entry.pid_model != self.pid_model:
            self.pid_mode = entry.pid_model
            n_updates += 1
        if entry.target is not None and entry.target != self.target:
            self.target = entry.target
            n_updates += 1
        if entry.http_code is not None and entry.http_code != self.http_code:
            self.http_code = entry.http_code
            n_updates += 1
        if entry.canonical is not None and entry.canonical != self.canonical:
            self.canonical = entry.canonical
            n_updates += 1
        if entry.synonym_for is not None and entry.synonym_for != self.synonym_for:
            self.synonym_for = entry.synonym_for
            n_updates += 1
        if entry.properties is not None and entry.properties != self.properties:
            self.properties = entry.properties
            n_updates += 1
        return n_updates


class ConfigMeta(Base):
    __tablename__ = "piddef_meta"

    key: sqlorm.Mapped[int] = sqlorm.mapped_column(primary_key=True)
    created: sqlorm.Mapped[datetime.datetime] = sqlorm.mapped_column(
        default=current_time, doc="Time when this configuration was created."
    )
    updated: sqlorm.Mapped[datetime.datetime] = sqlorm.mapped_column(
        nullable=True, default=None, doc="Time when this configuration was updated."
    )
    max_value_length: sqlorm.Mapped[int] = sqlorm.mapped_column(
        doc="Computed maximum length of value entries"
    )
    description: sqlorm.Mapped[str] = sqlorm.mapped_column(
        nullable=True, doc="Human readable description of this configuration."
    )


class PidDefinitionCatalog:
    """A repository of identifier configuration details.

    This class provides methods for operating on the database containing
    the identifier configuration details.
    """

    def __init__(self, session: sqlorm.Session):
        """
        Initial the config repository instance.

        Args:
            session: Returned by engine.connect()
        """
        self._session = session
        # Cache this value as it is used often. -1 indicates it is unset.
        self._cached_max_len = -1

    def initialize_configuration(self, description: str) -> ConfigMeta:
        """
        Initializes the configuration metadata. This should be
        called when creating a new configuration.

        Args:
            description: Human readable description of the configuration.

        Returns: ConfigMeta record.
        """
        meta = ConfigMeta(key=0, max_value_length=0, description=description)
        self._session.add(meta)
        self._session.commit()
        return meta

    def refresh_metadata(self):
        """
        Update the value length count.

        Computes and stores the maximum value length. Call this method
        after altering any definition records.
        """
        max_len_q = sqlalchemy.select(
            sqlalchemy.sql.expression.func.max(
                sqlalchemy.sql.expression.func.char_length(PidDefinition.value)
            )
        )
        result = self._session.execute(max_len_q).fetchone()[0]
        meta = self._session.get(ConfigMeta, 0)
        meta.max_value_length = result
        meta.updated = current_time()
        self._cached_max_len = result
        self._session.commit()

    def get_metadata(self) -> dict[str, typing.Any]:
        meta = self._session.get(ConfigMeta, 0)
        m_updated = meta.updated
        if m_updated is not None:
            m_updated = m_updated.replace(tzinfo=datetime.timezone.utc)
        return {
            "description": meta.description,
            "created": meta.created.replace(tzinfo=datetime.timezone.utc),
            "updated": m_updated
        }

    def get_max_value_length(self) -> int:
        if self._cached_max_len > 0:
            return self._cached_max_len
        meta = self._session.get(ConfigMeta, 0)
        self._cached_max_len = meta.max_value_length
        return self._cached_max_len

    def get_by_uniq(self, uniq: str) -> typing.Optional[PidDefinition]:
        """
        Returns the definition matching the uniq value.

        Note that records with no prefix or value entry have
        an empty string, so the in the case of a record with
        scheme=foo, and not prefix or value set, the uniq
        value will be "foo:/".

        Args:
            uniq: (str) The uniq value to match (scheme:prefix/value)

        Returns:
            PidDefinition if found, otherwise None
        """
        q = sqlalchemy.select(PidDefinition).where(PidDefinition.uniq == uniq)
        result = self._session.execute(q)
        try:
            return result.fetchone()[0]
        except TypeError:
            pass
        return None

    def _get(
        self,
        scheme: str,
        prefix: typing.Optional[str] = None,
        value: typing.Optional[str] = None,
    ) -> typing.Optional[PidDefinition]:
        # scheme and prefix are exact matches
        if (value is None or value == "") and (prefix is None or prefix == ""):
            q = sqlalchemy.select(PidDefinition).where(
                sqlalchemy.and_(
                    PidDefinition.scheme == scheme,
                    PidDefinition.prefix == "",
                    PidDefinition.value == "",
                ),
            )
            result = self._session.execute(q)
            try:
                return result.fetchone()[0]
            except TypeError:
                pass
            return None
        if value is None or value == "":
            q = sqlalchemy.select(PidDefinition).where(
                sqlalchemy.and_(
                    PidDefinition.scheme == scheme,
                    PidDefinition.prefix == prefix,
                    PidDefinition.value == "",
                ),
            )
            result = self._session.execute(q)
            try:
                return result.fetchone()[0]
            except TypeError:
                pass
            return None

        in_length_max = min(len(value), self.get_max_value_length())
        in_values = []
        for i in range(in_length_max, 1, -1):
            in_values.append(value[:i])
        q = (
            sqlalchemy.select(PidDefinition)
            .where(
                sqlalchemy.and_(
                    PidDefinition.scheme == scheme,
                    PidDefinition.prefix == prefix,
                    PidDefinition.value.in_(in_values),
                )
            )
            .order_by(
                sqlalchemy.sql.expression.func.char_length(PidDefinition.value).desc()
            )
        )
        result = self._session.execute(q)
        try:
            return result.fetchone()[0]
        except TypeError:
            pass
        return None

    def get(
        self,
        scheme: str,
        prefix: typing.Optional[str] = None,
        value: typing.Optional[str] = None,
        resolve_synonym: bool = True,
    ) -> typing.Optional[PidDefinition]:
        """
        Return the best matching definition.

        Matches on scheme and prefix values are exact.

        The value match is for the definition with the longest
        value entry that matches the start of the value portion
        of the parsed identifier string. For example, given two
        definitions with value = "fk" and "fk4", a match for
        the identifier with value portion "fkfoo" woruld return
        the definition with value "fk".

        The default behavior is to return the synonym target.

        Args:
            scheme: Scheme string to match.
            prefix: Optional prefix to match.
            value: Optional value portion to match.
            resolve_synonym: (bool) If return the synonym target.

        Returns:
            Matching PidDefinition or None if not match.
        """
        entry = self._get(scheme, prefix=prefix, value=value)
        if entry is None:
            entry = self._get(scheme=scheme, prefix=prefix, value=None)
        if entry is None:
            entry = self._get(scheme=scheme, prefix=None, value=None)
        if entry is None:
            return None
        if entry.synonym_for is None or not resolve_synonym:
            return entry
        synonym_parts = rslv.lib_rslv.split_identifier_string(entry.synonym_for)
        _scheme = (
            synonym_parts["scheme"] if synonym_parts["scheme"] is not None else scheme
        )
        _prefix = synonym_parts["prefix"] if synonym_parts["prefix"] != "" else prefix
        _value = synonym_parts["value"] if synonym_parts["value"] is not None else value
        return self.get(_scheme, prefix=_prefix, value=_value)

    def add(self, entry: PidDefinition) -> str:
        """
        Add an entry to the repository database.

        The entry must be unique otherwise it will fail with a
        UniqueConstraint exception.

        Args:
            entry: A populated PidDefinition for storing in the database.

        Returns:
            str: The computed unique value

        """
        self._session.add(entry)
        self._session.commit()
        return entry.uniq

    def update(self, entry: PidDefinition) -> int:
        existing_entry = self.get_by_uniq(entry.uniq)
        existing_revision =existing_entry.properties.get("revision", 0)
        new_revision = entry.properties.get("revision", 0)
        if new_revision < existing_revision:
            raise ValueError(f"Attempting to update a newer revision. Existing={existing_revision}, new={new_revision}")
        if existing_entry is None:
            raise ValueError(f"No existing record for: {entry.uniq}")
        n_changes = existing_entry.update(entry)
        if n_changes > 0:
            self._session.commit()
        return n_changes

    def add_or_update(self, entry: PidDefinition) -> typing.Dict:
        res = {
            "uniq": "",
            "n_changes": -1,
        }
        try:
            res["uniq"] = self.add(entry)
        except sqlalchemy.exc.IntegrityError as e:
            self._session.rollback()
            entry.uniq = calculate_definition_uniq(
                entry.scheme, entry.prefix, entry.value
            )
            res["uniq"] = entry.uniq
            res["n_changes"] = self.update(entry)
        return res

    def parse(self, pid_str: str, resolve_synonym:bool=True) -> typing.Tuple[dict, typing.Optional[PidDefinition]]:
        parts = rslv.lib_rslv.split_identifier_string(pid_str)
        parts["suffix"] = ""
        pid_definition = self.get(
            scheme=parts["scheme"], prefix=parts["prefix"], value=parts["value"], resolve_synonym=resolve_synonym
        )
        if pid_definition is None:
            return parts, None
        if pid_definition.splitter is not None:
            # TODO: implement additional split
            pass
        # Compute the suffix
        _content = parts.get("content", None)
        if _content is not None:
            pd_value = "" if pid_definition.value is None else pid_definition.value
            suffix_pos = pid_str.find(_content) + len(
                f"{pid_definition.prefix}/{pd_value}"
            )
            parts["suffix"] = pid_str[suffix_pos:]
        # Hack alert - need to deal with the oddness of ARK identifiers ignoring hyphens.
        if parts["scheme"] == "ark":
            # remove hyphens from the content and value portions
            parts["content"] = parts["content"].replace("-", "")
            parts["value"] = parts["value"].replace("-", "")
            parts["suffix"] = parts["suffix"].replace("-", "")
        return parts, pid_definition

    def list_schemes(self, valid_targets_only:bool=False):
        q = sqlalchemy.select(PidDefinition.scheme).distinct(PidDefinition.scheme)
        if valid_targets_only:
            q = q.filter(
                sqlalchemy.or_(
                    PidDefinition.properties[("target","DEFAULT",)] != 'null',
                    PidDefinition.synonym_for != None
                )
            )
        result = self._session.execute(q)
        return result

    def list_prefixes(self, scheme: str):
        q = (
            sqlalchemy.select(PidDefinition.prefix)
            .distinct(PidDefinition.prefix)
            .where(
                sqlalchemy.and_(
                    PidDefinition.scheme == scheme, PidDefinition.prefix != ""
                )
            )
        )
        result = self._session.execute(q)
        return result

    def list_values(self, scheme: str, prefix: str):
        q = (
            sqlalchemy.select(PidDefinition.value)
            .distinct(PidDefinition.value)
            .where(
                sqlalchemy.and_(
                    PidDefinition.scheme == scheme,
                    PidDefinition.prefix == prefix,
                    PidDefinition.value != "",
                )
            )
        )
        result = self._session.execute(q)
        return result


def get_session(engine):
    return sqlalchemy.orm.sessionmaker(bind=engine)()

@contextlib.contextmanager
def get_catalog(engine):
    session = get_session(engine)
    try:
        yield PidDefinitionCatalog(session)
    finally:
        session.close()

def create_database(engine, description: str):
    """
    Executes the DDL to set up the database.

    Args:
        engine: Database instance
    """
    Base.metadata.create_all(engine)
    # See if we need to initialize the metadata
    session = get_session(engine)
    try:
        cfg = PidDefinitionCatalog(session)
        meta = session.get(ConfigMeta, 0)
        if meta is None:
            cfg.initialize_configuration(description)
    finally:
        session.close()


def clear_database(engine):
    """
    Drop all tables from the database.

    Args:
        engine: Database instance
    """
    Base.metadata.drop_all(engine)
