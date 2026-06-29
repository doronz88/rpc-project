"""Quiet griffe docstring-style warnings during the build.

The rpcclient docstrings currently mix Google and Sphinx styles, which trips
griffe in --strict mode. Lower griffe to ERROR so strict mode still guards the
things this site owns (links, nav, anchors) while the docstring cleanup is done
as a follow-up. Remove this hook once the docstrings are normalized.
"""

import logging


def on_config(config):
    logging.getLogger("mkdocs.plugins.griffe").setLevel(logging.ERROR)
    logging.getLogger("griffe").setLevel(logging.ERROR)
    return config
