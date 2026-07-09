"""Shared OPC UA type model, reversibility corpus, and reference codecs.

Used by the Avro, Protobuf, Arrow and xRegistry extension folders so that every
encoding is checked against the *same* canonical values and equality.
"""
from . import types, values, corpus, json_control  # noqa: F401

__all__ = ["types", "values", "corpus", "json_control"]
