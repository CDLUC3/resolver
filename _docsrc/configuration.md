---
title: Configuring rslv
---

# Configuring RSLV

## Service Setup

- `config.py` options
- `logging.conf`

## Resolver Configuration

RSLV performs resolution by matching a provided identifier with an entry (a "definition") in the configuration database. Each definition describes what to do with an identifier that matches. Each definition has three properties that are used for comparison with identifiers:

```
PidDefinition:
  scheme: str
  prefix: Optional[str] = ''
  value: Optional[str] = ''
```

An identifier is matched to a definition by comparing three properties of the identifier (scheme, prefix, and value) by performing an exact match on the scheme and prefix, and the longest defininition value matching the start of the identifier value portion. When matching, scheme has the highest precedence, followed by prefix, then value.

Definitions should be treated as a hierarchy of potential matches, with complete definitions having corresponding partially filled definitions. For example, given a configuration:

```
definition("ark", "12345", "fk4")
definition("ark", "12345", "")
definition("ark", "99999", "")
definition("ark", "", "")
```

The following matches apply:

```
"ark:12345/fk4foo" -> definition("ark", "12345", "fk4")
"ark:12345/fk4"    -> definition("ark", "12345", "fk4")
"ark:12345/zz"     -> definition("ark", "12345", "")
"ark:12345"        -> definition("ark", "12345", "")
"ark:99999/fk4foo" -> definition("ark", "99999", "")
"ark:33333/foo"    -> definition("ark", "", "")
```

Three aspects of an identifier are considered in the comparison: scheme, prefix, and value.

```
      pid
-------------------
scheme:prefix/value
       ------------
         content
```

Target Template

The target is specified in the definition as a template with placeholders that are filled by components of the parsed identifier.
