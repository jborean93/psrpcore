# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import typing

from sphinx.application import Sphinx

sys.path.insert(0, os.path.abspath(".."))

import re

from psrpcore.types import PSEnumBase, PSFlagBase, PSObject
from psrpcore.types._base import _UnsetValue

_PARAM_PATTERN = re.compile(r":param (\w*):")

# -- Project information -----------------------------------------------------

project = "psrpcore"
copyright = "2021, Jordan Borean"
author = "Jordan Borean"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinxcontrib.apidoc",
]

apidoc_module_dir = "../src/psrpcore"
apidoc_output_dir = "source"

# Add any paths that contain templates here, relative to this directory.
templates_path = [
    "_templates",
]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


def autodoc_process_docstring(
    app: Sphinx,
    what: str,
    name: str,
    obj: typing.Any,
    options: typing.Dict[str, typing.Any],
    lines: typing.List[str],
) -> None:
    """Auto inserts param type details for PSObjects."""
    if what != "class" or not issubclass(obj, PSObject):
        return

    prop_entries = {p.name: p for p in obj.PSObject.adapted_properties}
    prop_entries.update({p.name: p for p in obj.PSObject.extended_properties})

    total_lines = len(lines)
    insertions = []
    for idx in range(total_lines):
        line = lines[idx]
        param_match = _PARAM_PATTERN.match(line)
        if not param_match:
            continue

        param_name = param_match.group(1)

        # Need to get the next line that isn't a continuation of the param docs
        # e.g. has no leading spaces.
        next_line = ""
        while idx + 1 != total_lines:
            idx += 1
            next_line = lines[idx]
            if not next_line.startswith(" "):
                break

        if next_line.startswith(f":type {param_name}:"):
            continue

        insertions.append((idx, param_name))

    insertion_offset = 0
    for idx, param_name in insertions:
        prop = prop_entries.get(param_name)
        if not prop:
            continue

        param_type = prop.ps_type if prop.ps_type is not None else PSObject
        if param_type.__module__ == "builtins":
            param_type_str = param_type.__name__

        else:
            param_type_str = f"{param_type.__module__}.{param_type.__name__}"

        type_line = f":type {param_name}: :obj:`{param_type.__name__} " f"<{param_type_str}>`"
        lines.insert(idx + insertion_offset, type_line)
        insertion_offset += 1


def autodoc_process_signature(
    app: Sphinx,
    what: str,
    name: str,
    obj: typing.Any,
    options: typing.Dict[str, typing.Any],
    signature: typing.Optional[str],
    return_annotations: typing.Optional[str],
) -> typing.Optional[typing.Tuple[typing.Optional[str], typing.Optional[str]]]:
    """Auto format PSObject signatures to document proper args/kwargs."""
    if what != "class":
        return None

    # Make sure PS enum types have the proper enum signature.
    if issubclass(obj, (PSEnumBase, PSFlagBase)):
        return "(value)", return_annotations

    # Make sure PSObject classes that use __init__ from PSObject define the
    # proper signature.
    if not isinstance(obj, PSObject) and obj.__init__ != PSObject.__init__:
        return None

    prop_entries = {p.name: p for p in obj.PSObject.adapted_properties}
    prop_entries.update({p.name: p for p in obj.PSObject.extended_properties})
    kwargs = []
    for prop in prop_entries.values():
        ps_type = prop.ps_type if prop.ps_type is not None else PSObject

        if ps_type.__module__ == "builtins":
            ps_type_str = ps_type.__name__

        else:
            ps_type_str = ps_type.__name__

        if prop.mandatory:
            entry = f"{prop.name}: {ps_type_str}"

        else:
            default_value = prop._value
            if prop._value == _UnsetValue:
                default_value = None

            entry = f"{prop.name}: Optional[{ps_type_str}] = {default_value!r}"

        kwargs.append(entry)

    signature = f'({", ".join(kwargs)})' if kwargs else None

    return signature, return_annotations


def autodoc_skip_member_handler(
    app: Sphinx,
    what: str,
    name: str,
    obj: typing.Any,
    skip: bool,
    options: typing.Dict[str, typing.Any],
) -> bool:
    a = ""
    return (
        skip
        # This is a metadata class for all PSObject types, end users don't need
        # to know about this for every single class in the codebase.
        or (name == "PSObject" and (obj != PSObject and obj != PSObject.PSObject))
        or name
        in [
            # These 2 methods are used to customize the (de)serialization process
            # for a specific class. They are not for public use and should not be
            # documented.
            "FromPSObjectForRemoting",
            "ToPSObjectForRemoting",
        ]
    )


def setup(
    app: Sphinx,
) -> None:

    app.connect("autodoc-process-docstring", autodoc_process_docstring)
    app.connect("autodoc-process-signature", autodoc_process_signature)
    app.connect("autodoc-skip-member", autodoc_skip_member_handler)
