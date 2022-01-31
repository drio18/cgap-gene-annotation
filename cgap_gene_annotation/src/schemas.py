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
    constants.TITLE: "Annotation Source",
    constants.DESCRIPTION: "Schema for Annotation Source",
    constants.TYPE: constants.OBJECT,
    constants.REQUIRED: [
        constants.FILES,
        constants.PREFIX,
        constants.PARSER,
    ],
    constants.ADDITIONAL_PROPERTIES: False,
    constants.PROPERTIES: {
        constants.METADATA: {
            constants.DESCRIPTION: "Information about this annotation",
            constants.TYPE: constants.OBJECT,
        },
        constants.FILES: {
            constants.DESCRIPTION: "Source files for the annotation",
            constants.TYPE: constants.ARRAY,
            constants.ITEMS: {constants.TYPE: constants.STRING},
        },
        constants.FILTER: {
            constants.DESCRIPTION: (
                "Fields to filter for inclusion in the final annotation"
            ),
            constants.TYPE: constants.OBJECT,
            constants.ADDITIONAL_PROPERTIES: {
                constants.TYPE: constants.ARRAY,
                constants.ITEMS: {constants.TYPE: constants.STRING},
            },
        },
        constants.KEEP_FIELDS: {
            constants.DESCRIPTION: "Fields to add from the annotation",
            constants.TYPE: constants.ARRAY,
            constants.ITEMS: {constants.TYPE: constants.STRING},
        },
        constants.DROP_FIELDS: {
            constants.DESCRIPTION: "Fields to drop from the annotation",
            constants.TYPE: constants.ARRAY,
            constants.ITEMS: {constants.TYPE: constants.STRING},
        },
        constants.REPLACEMENT_FIELDS: {
            constants.DESCRIPTION: "Fields with values to rename",
            constants.TYPE: constants.OBJECT,
            constants.ADDITIONAL_PROPERTIES: {
                constants.DESCRIPTION: (
                    "Mapping of existing field values to replacement value"
                ),
                constants.TYPE: constants.OBJECT,
                constants.ADDITIONAL_PROPERTIES: {
                    constants.DESCRIPTION: "Replacement value",
                    constants.TYPE: constants.STRING,
                },
            },
        },
        constants.SPLIT_FIELDS: {
            constants.DESCRIPTION: (
                "Parameters for creating a new field out of an"
                " existing field in the record by splitting the"
                " existing field value's string"
            ),
            constants.TYPE: constants.ARRAY,
            constants.ITEMS: {
                constants.TYPE: constants.OBJECT,
                constants.ADDITIONAL_PROPERTIES: False,
                constants.PROPERTIES: {
                    constants.SPLIT_FIELDS_NAME: {
                        constants.DESCRIPTION: ("The name for the new field"),
                        constants.TYPE: constants.STRING,
                    },
                    constants.SPLIT_FIELDS_CHARACTER: {
                        constants.DESCRIPTION: (
                            "The character on which to split the"
                            " existing field value"
                        ),
                        constants.TYPE: constants.STRING,
                    },
                    constants.SPLIT_FIELDS_INDEX: {
                        constants.DESCRIPTION: (
                            "The index (zero-based) of the existing,"
                            " split string to use for the new field"
                        ),
                        constants.TYPE: "integer",
                    },
                    constants.SPLIT_FIELDS_FIELD: {
                        constants.DESCRIPTION: (
                            "The name of the existing field to split"
                        ),
                        constants.TYPE: constants.STRING,
                    },
                },
                constants.REQUIRED: [
                    constants.SPLIT_FIELDS_NAME,
                    constants.SPLIT_FIELDS_CHARACTER,
                    constants.SPLIT_FIELDS_FIELD,
                ],
            },
        },
        constants.SOURCE: {
            constants.DESCRIPTION: (
                "Whether annotations are the basis for subsequent annotation merges"
            ),
            constants.TYPE: constants.BOOLEAN,
        },
        constants.DEBUG: {
            constants.DESCRIPTION: (
                "Whether to log debug information for this annotation source"
            ),
            constants.TYPE: constants.BOOLEAN,
        },
        constants.CYTOBAND: {
            constants.DESCRIPTION: (
                "Fields for calculating cytoband locations of annotations"
            ),
            constants.TYPE: constants.OBJECT,
            constants.ADDITIONAL_PROPERTIES: False,
            constants.REQUIRED: [
                constants.CHROMOSOME,
                constants.START,
                constants.END,
                constants.REFERENCE_FILE,
                constants.POSITION_INDEX,
            ],
            constants.PROPERTIES: {
                constants.CHROMOSOME: {
                    constants.DESCRIPTION: "The chromosome annotation field",
                    constants.TYPE: constants.STRING,
                },
                constants.START: {
                    constants.DESCRIPTION: "The start position annotation field",
                    constants.TYPE: constants.STRING,
                },
                constants.END: {
                    constants.DESCRIPTION: "The end position annotation field",
                    constants.TYPE: constants.STRING,
                },
                constants.REFERENCE_FILE: {
                    constants.DESCRIPTION: "Path to the UCSC cytoband reference file",
                    constants.TYPE: constants.STRING,
                },
                constants.POSITION_INDEX: {
                    constants.DESCRIPTION: (
                        "The index of the first position (i.e. 0-based or 1-based)"
                    ),
                    constants.TYPE: constants.INTEGER,
                    constants.ENUM: [0, 1],
                },
            },
        },
        constants.MERGE: {
            constants.DESCRIPTION: "Information on merging the annotation",
            constants.TYPE: constants.OBJECT,
            constants.ADDITIONAL_PROPERTIES: False,
            constants.REQUIRED: [
                constants.MERGE_PRIMARY_FIELDS,
                constants.MERGE_CHOICE,
            ],
            constants.PROPERTIES: {
                constants.MERGE_PRIMARY_FIELDS: {
                    constants.DESCRIPTION: (
                        "Identifiers for fields that must match to merge"
                    ),
                    constants.TYPE: constants.ARRAY,
                    constants.ITEMS: {
                        constants.TYPE: constants.ARRAY,
                        constants.ITEMS: {
                            constants.ONE_OF: [
                                {constants.TYPE: constants.STRING},
                                {
                                    constants.TYPE: constants.ARRAY,
                                    constants.ITEMS: {
                                        constants.TYPE: constants.STRING,
                                    },
                                    constants.MIN_ITEMS: 1,
                                },
                            ]
                        },
                        constants.MIN_ITEMS: 2,
                        constants.MAX_ITEMS: 2,
                    },
                },
                constants.MERGE_SECONDARY_FIELDS: {
                    constants.DESCRIPTION: (
                        "Identifiers for fields to narrow multiple matches to unique"
                        " set"
                    ),
                    constants.TYPE: constants.ARRAY,
                    constants.ITEMS: {
                        constants.TYPE: constants.ARRAY,
                        constants.ITEMS: {
                            constants.ONE_OF: [
                                {constants.TYPE: constants.STRING},
                                {
                                    constants.TYPE: constants.ARRAY,
                                    constants.ITEMS: {
                                        constants.TYPE: constants.STRING,
                                    },
                                    constants.MIN_ITEMS: 1,
                                },
                            ]
                        },
                        constants.MIN_ITEMS: 2,
                        constants.MAX_ITEMS: 2,
                    },
                },
                constants.MERGE_CHOICE: {
                    constants.DESCRIPTION: "The type of merge to execute",
                    constants.TYPE: constants.ARRAY,
                    constants.MIN_ITEMS: 2,
                    constants.MAX_ITEMS: 2,
                    constants.ITEMS: {
                        constants.TYPE: constants.STRING,
                        constants.ENUM: [
                            constants.MERGE_CHOICE_ONE,
                            constants.MERGE_CHOICE_MANY,
                        ],
                    },
                },
            },
        },
        constants.PARSER: {
            constants.DESCRIPTION: "Information on how to parse this annoation source",
            constants.TYPE: constants.OBJECT,
            constants.ADDITIONAL_PROPERTIES: False,
            constants.REQUIRED: [constants.PARSER_CHOICE],
            constants.PROPERTIES: {
                constants.PARAMETERS: {
                    constants.DESCRIPTION: "The kwargs to pass to the parser",
                    constants.TYPE: constants.OBJECT,
                    constants.ADDITIONAL_PROPERTIES: False,
                    constants.PROPERTIES: {
                        constants.parsers.HEADER: {
                            constants.DESCRIPTION: (
                                "The header for the file, provided as a list of"
                                " field names in appropriate order"
                            ),
                            constants.TYPE: constants.ARRAY,
                            constants.ITEMS: {
                                constants.TYPE: constants.STRING,
                            },
                        },
                        constants.parsers.HEADER_LINE: {
                            constants.DESCRIPTION: (
                                "The line containing the header. Useful when the"
                                " header starts with a comment character that indicates"
                                " the line would otherwise be ignored."
                            ),
                            constants.TYPE: "integer",
                            constants.MINIMUM: 0,
                        },
                        constants.parsers.COMMENT_CHARACTERS: {
                            constants.DESCRIPTION: (
                                "Characters at the start of a line that signify the"
                                " line is a comment"
                            ),
                            constants.TYPE: constants.STRING,
                        },
                        constants.parsers.EMPTY_FIELDS: {
                            constants.DESCRIPTION: (
                                "Values that should be considered as an empty value"
                                " for a field and thus not included in the record"
                            ),
                            constants.TYPE: constants.ARRAY,
                            constants.ITEMS: {constants.TYPE: constants.STRING},
                        },
                        constants.parsers.LIST_IDENTIFIER: {
                            constants.DESCRIPTION: (
                                "The character(s) that signify the given field value is"
                                " a list, and upon which the value will be split into a"
                                " list"
                            ),
                            constants.TYPE: constants.STRING,
                        },
                        constants.parsers.STRIP_CHARACTERS: {
                            constants.DESCRIPTION: (
                                "The characters to be removed from the beginning and"
                                " end of all values from a line"
                            ),
                            constants.TYPE: constants.STRING,
                        },
                        constants.parsers.RECORD_PATH: {
                            constants.DESCRIPTION: (
                                "Path to the items of interest in XPath-like syntax"
                            ),
                            constants.TYPE: constants.STRING,
                        },
                    },
                },
                constants.PARSER_CHOICE: {
                    constants.DESCRIPTION: "Description of parser to use",
                    constants.TYPE: constants.STRING,
                    constants.ENUM: list(constants.PARSERS_AVAILABLE),
                },
            },
        },
        constants.PREFIX: {
            constants.DESCRIPTION: "The term used to prefix this annotation",
            constants.TYPE: constants.STRING,
            constants.NOT: {constants.ENUM: [constants.CYTOBAND]},
        },
    },
}

UPDATE_SCHEMA = {
    constants.SCHEMA: SCHEMA_DEFINITION,
    constants.ID: "schemas/update.json",
    constants.TITLE: "Schema for Updating Existing Annotation",
    constants.TYPE: constants.OBJECT,
    constants.ADDITIONAL_PROPERTIES: False,
    constants.PROPERTIES: {
        constants.ADD: {
            constants.DESCRIPTION: "New annotation sources to add",
            constants.TYPE: constants.ARRAY,
            constants.ITEMS: ANNOTATION_SOURCE,
        },
        constants.REPLACE: {
            constants.DESCRIPTION: "Existing annotation sources to update",
            constants.TYPE: constants.ARRAY,
            constants.ITEMS: ANNOTATION_SOURCE,
        },
        constants.REMOVE: {
            constants.DESCRIPTION: "Existing annotation prefix to remove",
            constants.TYPE: constants.ARRAY,
            constants.ITEMS: ANNOTATION_SOURCE[constants.PROPERTIES][constants.PREFIX],
        },
    },
}

CREATE_SCHEMA = {
    constants.SCHEMA: SCHEMA_DEFINITION,
    constants.ID: "schemas/create.json",
    constants.TITLE: "Schema for Creating New Annotation",
    constants.TYPE: constants.ARRAY,
    constants.ITEMS: ANNOTATION_SOURCE,
}
