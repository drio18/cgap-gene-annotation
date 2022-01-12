"""Schemas used for validation of input data.

CREATE_SCHEMA validates input for creation of new annotation file,
while UPDATE_SCHEMA validates input for update of existing
annotation file.

We generate the schemas as python objects here to facilitate
schema maintanence should any of the constants, such as the parsers
available, change moving forward.
"""

from . import constants

SCHEMA_DEFINITION = "http://json-schema.org/draft-04/schema#"

ANNOTATION_SOURCE = {
    "title": "Annotation Source",
    "description": "Schema for Annotation Source",
    "type": "object",
    "required": [
        "files",
        "prefix",
        "parser",
    ],
    "additionalProperties": False,
    "properties": {
        constants.METADATA: {
            "description": "Information about this annotation",
            "type": "object",
        },
        constants.FILES: {
            "description": "Source files for the annotation",
            "type": "array",
            "items": {"type": "string"},
        },
        constants.FILTER: {
            "description": "Fields to filter for inclusion in the final annotation",
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
        },
        constants.KEEP_FIELDS: {
            "description": "Fields to add from the annotation",
            "type": "array",
            "items": {"type": "string"},
        },
        constants.DROP_FIELDS: {
            "description": "Fields to drop from the annotation",
            "type": "array",
            "items": {"type": "string"},
        },
        constants.SOURCE: {
            "description": (
                "Whether annotations are the basis for subsequent annotations"
            ),
            "type": "boolean",
        },
        constants.MERGE: {
            "description": "Information on merging the annotation",
            "type": "object",
            "additionalProperties": False,
            "required": [
                constants.MERGE_PRIMARY_FIELDS,
                constants.MERGE_CHOICE,
            ],
            "properties": {
                constants.MERGE_PRIMARY_FIELDS: {
                    "description": "Identifiers for fields that must match to merge",
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                constants.MERGE_SECONDARY_FIELDS: {
                    "description": "Identifiers for fields to narrow multiple matches to unique set",
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                constants.MERGE_CHOICE: {
                    "description": "The type of merge to execute",
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 2,
                    "items": {
                        "type": "string",
                        "enum": [
                            constants.MERGE_CHOICE_ONE,
                            constants.MERGE_CHOICE_MANY,
                        ],
                    },
                },
            },
        },
        constants.PARSER: {
            "description": "Information on how to parse this annoation source",
            "type": "object",
            "additionalProperties": False,
            "required": [constants.PARSER_CHOICE],
            "properties": {
                constants.PARAMETERS: {
                    "description": "The kwargs to pass to the parser",
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        constants.parsers.HEADER: {
                            "description": (
                                "The header for the file, provided as a list of"
                                " field names in appropriate order"
                            ),
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                        },
                        constants.parsers.HEADER_LINE: {
                            "description": (
                                "The line containing the header. Useful when the"
                                " header starts with a comment character that indicates"
                                " the line would otherwise be ignored."
                            ),
                            "type": "integer",
                            "minimum": 0,
                        },
                        constants.parsers.COMMENT_CHARACTERS: {
                            "description": (
                                "Characters at the start of a line that signify the"
                                " line is a comment"
                            ),
                            "type": "string",
                        },
                        constants.parsers.EMPTY_FIELDS: {
                            "description": (
                                "Values that should be considered as an empty value"
                                " for a field and thus not included in the record"
                            ),
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        constants.parsers.LIST_IDENTIFIER: {
                            "description": (
                                "The character(s) that signify the given field value is"
                                " a list, and upon which the value will be split into a"
                                " list"
                            ),
                            "type": "string",
                        },
                        constants.parsers.STRIP_CHARACTERS: {
                            "description": (
                                "The characters to be removed from the beginning and"
                                " end of all values from a line"
                            ),
                            "type": "string",
                        },
                        constants.parsers.SPLIT_FIELDS: {
                            "description": (
                                "Parameters for creating a new field out of an"
                                " existing field in the record by splitting the"
                                " existing field value's string"
                            ),
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    constants.parsers.SPLIT_FIELDS_NAME: {
                                        "description": (
                                            "The name for the new field"
                                        ),
                                        "type": "string",
                                    },
                                    constants.parsers.SPLIT_FIELDS_CHARACTER: {
                                        "description": (
                                            "The character on which to split the"
                                            " existing field value"
                                        ),
                                        "type": "string",
                                    },
                                    constants.parsers.SPLIT_FIELDS_INDEX: {
                                        "description": (
                                            "The index (zero-based) of the existing,"
                                            " split string to use for the new field"
                                        ),
                                        "type": "integer",
                                        "minimum": 0,
                                    },
                                    constants.parsers.SPLIT_FIELDS_FIELD: {
                                        "description": (
                                            "The name of the existing field to split"
                                        ),
                                        "type": "string",
                                    },
                                },
                            },
                        },
                    },
                },
                constants.PARSER_CHOICE: {
                    "description": "Description of parser to use",
                    "type": "string",
                    "enum": [x for x in constants.PARSERS_AVAILABLE],
                },
            },
        },
        constants.PREFIX: {
            "description": "The term used to prefix this annotation",
            "type": "string",
        },
    },
}

UPDATE_SCHEMA = {
    "$schema": SCHEMA_DEFINITION,
    "id": "schemas/update.json",
    "title": "Schema for Updating Existing Annotation",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        constants.ADD: {
            "description": "New annotation sources to add",
            "type": "array",
            "items": ANNOTATION_SOURCE,
        },
        constants.REPLACE: {
            "description": "Existing annotation sources to update",
            "type": "array",
            "items": ANNOTATION_SOURCE,
        },
        constants.REMOVE: {
            "description": "Existing annotation prefix to remove",
            "type": "array",
            "items": ANNOTATION_SOURCE["properties"][constants.PREFIX],
        },
    },
}

CREATE_SCHEMA = {
    "$schema": SCHEMA_DEFINITION,
    "id": "schemas/create.json",
    "title": "Schema for Creating New Annotation",
    "type": "array",
    "items": ANNOTATION_SOURCE,
}
