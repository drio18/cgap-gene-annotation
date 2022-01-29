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
    "XML": parsers.XMLParser,
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

SPLIT_FIELDS = "split_fields"
SPLIT_FIELDS_NAME = "name"
SPLIT_FIELDS_CHARACTER = "character"
SPLIT_FIELDS_INDEX = "index"
SPLIT_FIELDS_FIELD = "field"

REPLACEMENT_FIELDS = "replacement_fields"

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

CYTOBAND = "cytoband"
CHROMOSOME = "chromosome"
START = "start"
END = "end"
REFERENCE_FILE = "reference_file"
POSITION_INDEX = "position_index"

SCHEMA = "$schema"
ID = "id"
TITLE = "title"
DESCRIPTION = "description"
TYPE = "type"
OBJECT = "object"
STRING = "string"
NUMBER = "number"
FLOAT = "float"
INTEGER = "integer"
BOOLEAN = "boolean"
ARRAY = "array"
REQUIRED = "required"
PROPERTIES = "properties"
ADDITIONAL_PROPERTIES = "additionalProperties"
ITEMS = "items"
ENUM = "enum"
MINIMUM = "minimum"
MIN_ITEMS = "minItems"
MAX_ITEMS = "maxItems"
NOT = "not"
