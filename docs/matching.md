---
comment: |
  codebraid pandoc –katex –from markdown+tex_math_single_backslash –filter pandoc-sidenote –to html5+smart –template=$HOME/.pandoc/templates/template.html5 --css=$HOME/.pandoc/theme.css –toc –wrap=none matching.md \> matching.html style and template from https://jez.io/pandoc-markdown-css-theme/
title: Parse and Match Identifier
---

- [Matching and Resolution](#matching-and-resolution)
  - [Splitting the identifier string](#splitting-the-identifier-string)
  - [Matching a Definition](#matching-a-definition)

# Matching and Resolution

The core functionality of `rslv` is to match a provided identifier to a redirect target definition and either return information about the corresponding definition or redirect the requestor to the defined target.

It does this by splitting the input identifier string into various components and finding the best match to the components from a list of identifier definitions. The components and defintion are then used to construct a response that will be either a redirect to the registered target or metadata about the identifier (Figure 1).

<figure>

[![Identifier matching](https://tinyurl.com/ylejjbcr)](https://tinyurl.com/ylejjbcr)<!--![Identifier matching](./assets/matching.puml)-->

<figcaption>

**Figure 1.** Overview of process for handling a user supplied identifier string. The string is split into components as a `parsed_pid` instance. That instance is matched against the available definitions. A match provides a `pid_definition` instance which is used with the \`If a match is found then the response is a redirect to the registered target or the matched definition metadata.

</figcaption>
</figure>

## Splitting the identifier string

The provided identifier string is split into several components (Figure 2) by applying the following rules:

1.  Split the string at the first occurrence of a colon (“:”).
2.  The first portion is the `scheme`.
3.  Left trim whitespace or any instances of the characters `:`, `/` from the second portion. This portion is the `content`.
4.  Split `content` at the first occurrence of the forward slash character (“/”).
5.  The first portion is the `prefix`
6.  Left trim whitespace pr any instance of the characters `:`, `/` from the second portion. This portion is the `value`.

<figure>

            ________content__________ 
           /                         \
       ark:12345/some_value/with?extra
       \_/ \___/ \___________________/
        |    |           |  
     scheme  |         value
           prefix      
           
    scheme = "ark"
    content = "12345/some_value/with?extra"
    prefix = "12345"
    value = "some_value/with?extra"

<figcaption>

**Figure 2.** Components of a `parsed_pid`. After parsing, extracted components of the identifier are available for locating a matching definition and formatting the response.

</figcaption>
</figure>

Some examples of parsed identifiers follow. `pid` is the input identifier:

``` stderr
Traceback (most recent call last):
  File "source.py", line 2, in <module>
    doc_parts.split_examples()
  File "~/Documents/Projects/rslv/_docsrc/doc_parts/__init__.py", line 66, in split_examples
    ppid = rslv.lib_rslv.ParsedPID(pid=pid)
AttributeError: module 'rslv.lib_rslv' has no attribute 'ParsedPID'
```

## Matching a Definition

Identifier definitions provide the rules for creating a target address given a set of identifier components (i.e. a `parsed_pid` instance). The definition corresponding with a particular identifier is found by matching `parsed_pid` components with entries in the definition catalog, starting with the most specific match and progressively relaxing the number of matching components until a match is found or not (Figure 3).

<figure>

[![Match progress expansion](https://tinyurl.com/yq7grlh9)](https://tinyurl.com/yq7grlh9)<!--![Match progress expansion](./assets/pidmatch.puml)-->

<figcaption>

**Figure 3.** General process for matching a defintion given a `parsed_pid`. Match requirements are progressively relaxed until a match is found or not. Value comparison is performed by searching for the longest definition value that matches the start of the `pid_definition.value` property. Matches on `prefix` and `scheme` are performed by exact comparison.

</figcaption>
</figure>

Examples of identifier matching to a set of definitions.

Given the definitions:

The following matches result:
