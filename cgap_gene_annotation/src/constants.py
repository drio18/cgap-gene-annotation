"""Constants used across modules, primarily specifying terms used
within schemas for creating/updating annotation files.

NOTE: PARSERS_AVAILABLE must be updated with appropriate key, value
pairs whenever parsers added to or removed from parsers module.
"""

from . import parsers

PARSERS_AVAILABLE = {
    "TSV": parsers.TSVParser,
    "CSV": parsers.CSVParser,
    "GTF": parsers.GTFParser,
    "GenBank": parsers.GenBankParser,
    "UniProtDAT": parsers.UniProtDATParser,
}

METADATA = "metadata"
ANNOTATION = "annotation"

ADD = "add"
REPLACE = "replace"
REMOVE = "remove"

FILES = "files"

FILTER = "filter"

KEEP_FIELDS = "keep"

DROP_FIELDS = "drop"

SOURCE = "source"

MERGE = "merge"
MERGE_PRIMARY_FIELDS = "primary_fields"
MERGE_SECONDARY_FIELDS = "secondary_fields"
MERGE_CHOICE = "type"
MERGE_CHOICE_ONE = "one"
MERGE_CHOICE_MANY = "many"

PARSER = "parser"
PARAMETERS = "parameters"
PARSER_CHOICE = "type"

PREFIX = "prefix"
