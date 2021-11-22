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
            "type": "object"
        },
        constants.FILES: {
            "description": "Source files for the annotation",
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        constants.FILTER: {
            "description": "Fields to filter for inclusion in the final annotation",
            "type": "object",
            "additionalProperties": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        },
        constants.KEEP_FIELDS: {
            "description": "Fields to add from the annotation",
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        constants.DROP_FIELDS: {
            "description": "Fields to drop from the annotation",
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        constants.SOURCE: {
            "description": "Whether annotations are the basis for subsequent annotations",
            "type": "boolean"
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
                        "items": {
                            "type": "string"
                        },
                        "minItems": 2,
                        "maxItems": 2
                    }
                },
                constants.MERGE_SECONDARY_FIELDS: {
                    "description": "Identifiers for fields to narrow multiple matches to unique set",
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "minItems": 2,
                        "maxItems": 2
                    }
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
                            constants.MERGE_CHOICE_MANY
                        ]
                    }
                }
            }
        },
        constants.PARSER: {
            "description": "Information on how to parse this annoation source",
            "type": "object",
            "additionalProperties": False,
            "required": [
                constants.PARSER_CHOICE
            ],
            "properties": {
                constants.PARAMETERS: {
                    "description": "The kwargs to pass to the parser",
                    "type": "object"
                },
                constants.PARSER_CHOICE: {
                    "description": "Description of parser to use",
                    "type": "string",
                    "enum": [x for x in constants.PARSERS_AVAILABLE],
                }
            }
        },
        constants.PREFIX: {
            "description": "The term used to prefix this annotation",
            "type": "string"
        }
    }
}

UPDATE_SCHEMA = {
    "$schema": SCHEMA_DEFINITION,
    "id": "schemas/update",
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
            "items": ANNOTATION_SOURCE["properties"][constants.PREFIX]
        }
    }
}

CREATE_SCHEMA = {
    "$schema": SCHEMA_DEFINITION,
    "id": "schemas/create",
    "title": "Schema for Creating New Annotation",
    "type": "array",
    "items": ANNOTATION_SOURCE
}
