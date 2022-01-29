"""Classes for handling annotations from one or more source files.

Classes:
    - SourceAnnotation: Filters raw records parsed from singe source
        file.
    - GeneAnnotation: Contains annotations and metadata for merged data
        from multiple source files as well as methods for creating and
        updating such annotations.
    - JSONInputError: Exception class raised when provided JSON
        parameters do not validate against schema for creating or
        updating annotion file.
"""

import json
import logging
from copy import deepcopy

import jsonschema

from . import constants, schemas
from .cytoband import add_cytoband_field, get_cytoband_locations
from .merge import AnnotationMerge
from .utils import nested_getter, nested_setter, FileHandler


log = logging.getLogger(__name__)


class SourceAnnotation:
    """Class for creating annotations from a source file.

    Primary method to call is make_annotation() to obtain all
    annotations from the source file, with records/fields filtered
    according to parameters.

    :var parser: The parser for the source file
    :vartype parser: class from parsers.py
    :var filter_fields: Field names and permitted values used to
        filter a record from the parser. Only records which contain a
        permitted value for all given field names will be included in
        the annotation created.
    :vartype filter_fields: dict
    :var fields_to_keep: Fields from the record to include in the
        annotation. If present, overrides fields_to_drop.
    :vartype fields_to_keep: list(str)
    :var fields_to_drop: Fieds from the record to exclude from the
        annotation.
    :vartype fields_to_drop: list(str)
    :var split_fields: vareters for creating new field by
        splitting existing fields in record.
    :vartype split_fields: dict
    :var replacement_fields: Fields and value replacements, used
        to convert replace given value to desired one.
    :vartype replacement_fields: dict(dict)
    """

    def __init__(
        self,
        parser,
        filter_fields=None,
        fields_to_keep=None,
        fields_to_drop=None,
        split_fields=None,
        replacement_fields=None,
    ):
        """Create the class.

        :param parser: The parser for the source file
        :type parser: class from parsers.py
        :param filter_fields: Field names and permitted values used to
            filter a record from the parser. Only records which contain a
            permitted value for all given field names will be included in
            the annotation created.
        :type filter_fields: dict
        :param fields_to_keep: Fields from the record to include in the
            annotation. If present, overrides fields_to_drop.
        :type fields_to_keep: list(str)
        :param fields_to_drop: Fields from the record to exclude from the
            annotation.
        :type fields_to_drop: list(str)
        :param split_fields: Parameters for creating new field by
            splitting existing fields in record.
        :type split_fields: dict
        :param replacement_fields: Fields and value replacements, used
            to convert replace given value to desired one.
        :type replacement_fields: dict(dict)
        """
        self.parser = parser
        self.filter_fields = filter_fields
        self.fields_to_keep = fields_to_keep
        self.fields_to_drop = fields_to_drop
        self.split_fields = split_fields
        self.replacement_fields = replacement_fields

    def make_annotation(self):
        """Create all annotations for the source file.

        Parsed records from the source file are filtered and/or pruned
        according to class parameters.

        All parsing of source file occurs within the given
        parser class, with the parser's get_records() method expected to
        return an iterator containing complete, raw annotations.

        :returns: All annotations from the source file.
        :rtype: list(dict)
        """
        annotation = []
        for record in self.parser.get_records():
            parsed_record = deepcopy(record)
            if self.split_fields:
                self.create_split_fields(record)
            if self.replacement_fields:
                self.make_field_replacements(record)
            if self.filter_fields:
                self.filter_record(record)
            if self.fields_to_keep:
                record = self.retain_fields(record)
            elif self.fields_to_drop:
                self.remove_fields(record)
            if not record:
                log.debug("Filtered out record: %s", parsed_record)
                continue
            annotation.append(record)
        return annotation

    def filter_record(self, record):
        """Determine record inclusion/exclusion in annotation.

        Given fields and permissable values, only keep the record if
        all fields are present and record's values for those fields are
        all permitted.

        :param record: A parsed record from a source file.
        :type record: dict
        """
        for field, permissible_values in self.filter_fields.items():
            field_value = nested_getter(record, field, string_return=True)
            if field_value is None:
                record.clear()
                break
            if isinstance(field_value, str):
                if field_value not in permissible_values:
                    record.clear()
                    break
            elif isinstance(field_value, list):
                intersection = set(field_value).intersection(set(permissible_values))
                if not intersection:
                    record.clear()
                    break

    def retain_fields(self, record):
        """Create record with only the requested fields.

        :param record: A parsed record from a source file.
        :type record: dict
        :returns: Record with requested fields (if found).
        :rtype: dict
        """
        result = {}
        for field in self.fields_to_keep:
            value = nested_getter(record, field, string_return=True)
            nested_setter(result, field, value)
        return result

    def remove_fields(self, record):
        """Exclude fields from a record.

        :param record: A parsed record from a source file.
        :type record: dict
        """
        for field in self.fields_to_drop:
            if nested_getter(record, field, string_return=True):
                nested_setter(record, field, delete_field=True)

    def create_split_fields(self, record):
        """Split field in record according to parameters, and update
        the record with the new field.

        Useful for when source file provides Ensembl ID as ID.version
        and only ID can be matched.

        :param record: The record to update.
        :type record: dict
        """
        for split_field in self.split_fields:
            field_to_split = split_field.get(constants.SPLIT_FIELDS_FIELD, "")
            split_character = split_field.get(constants.SPLIT_FIELDS_CHARACTER)
            split_index = split_field.get(constants.SPLIT_FIELDS_INDEX)
            field_name = split_field.get(constants.SPLIT_FIELDS_NAME)
            field_value = nested_getter(record, field_to_split, string_return=True)
            if isinstance(field_value, str):
                split_value = self.get_split_value(
                    field_value, split_character, split_index
                )
                nested_setter(record, field_name, value=split_value)
            elif isinstance(field_value, list):
                split_values = []
                for item in field_value:
                    if isinstance(item, str):
                        split_value = self.get_split_value(
                            item, split_character, split_index
                        )
                        if split_value is not None:
                            split_values.append(split_value)
                nested_setter(record, field_name, value=split_values)

    def get_split_value(self, to_split, split_character, split_index):
        """Split field by character and return specified index (if given)
        or the split list.

        :param to_split: String to split.
        :type to_split: str
        :param split_character: Character(s) on which to split.
        :type split_character: str
        :param split_index: Index of resulting array corresponding to
            desired result.
        :type split_index: int or None
        :returns: Split list or one of its indices.
        :rtype: list(str) or str or None
        """
        split_value = None
        result = None
        try:
            split_value = [x.strip() for x in to_split.split(split_character) if x]
        except ValueError:
            log.exception("Unable to split given string: %s", to_split)
        if split_value is not None:
            if split_index is not None and abs(split_index) < len(split_value):
                result = split_value[split_index]
            elif split_index is None:
                result = split_value
        return result

    def make_field_replacements(self, record):
        """Replace existing values for a given field with given desired
        values.

        Useful for converting source strings to desired strings for
        final annotation, e.g. "AD" --> "Autosomal Dominant".

        :param record: The record to update.
        :type record: dict
        """
        for field_name, replacement_values in self.replacement_fields.items():
            field_value = nested_getter(record, field_name, string_return=True)
            if isinstance(field_value, str):
                new_value = replacement_values.get(field_value)
                if new_value is not None:
                    nested_setter(record, field_name, value=new_value)
            elif isinstance(field_value, list):
                for idx, value in enumerate(field_value):
                    new_value = replacement_values.get(value)
                    if new_value is not None:
                        field_value[idx] = new_value


class JSONInputError(Exception):
    """Exception class for JSON input that does not validate.

    Accumulates all validation errors and provides readable messages to
    users regarding the error locations and issues.

    :var errors: All errors found while validating JSON input.
    :vartype errors: list
    """

    def __init__(self, errors):
        """Create the class.

        :param errors: All errors found while validating JSON input.
        :type errors: list
        """
        self.errors = errors
        super().__init__()

    def __str__(self):
        """Generate the output message for the class.

        Provide clear information on number of errors, their locations,
        and their exact validation issues.

        :returns: Error message
        :rtype: str
        """
        error_numbers = str(len(self.errors))
        error_messages = []
        first_line = "%s validation error(s) found in the given JSON.\n" % error_numbers
        error_messages.append(first_line)
        for error in self.errors:
            msg = ("Location: %s\n" "Error: %s\n") % (
                ".".join([str(x) for x in error.path]),
                error.message,
            )
            error_messages.append(msg)
        return "\n".join(error_messages)


class GeneAnnotation:
    """Class to gather annotations and metadata from multiple sources.

    High-level object in the package that utilizes most other modules
    directly or indirectly to generate or update the merged annotations
    as instructed by given JSON input parameters.

    Input JSON for annotation creation/update is validated and parsed
    within two primary methods for the class:
        - create_annotation(json_input): Validates JSON for annotation
            creation and generates new merged annotation.
        - update_annotation(json_input): Validates JSON for annotation
            update and revises existing annotation accordingly.

    :var file_path: The path to the merged annotations to write or to
        update.
    :vartype file_path: str
    :var metadata: The accumulated metadata from all sources used to
        create the annotations.
    :vartype metadata: dict
    :var annotations: The accumulated, merged annotations from all
        source files.
    :vartype annotations: list(dict)
    """

    def __init__(self, file_path):
        """Create the class.

        :param file_path: The path to the merged annotations to write
            or to update.
        :type file_path: str
        """
        self.file_path = file_path
        self.metadata = {}
        self.annotations = []

    def create_annotation(self, json_input):
        """Validate input and create a new annotation per provided
        parameters.

        :param json_input: Parameters for creating annotation.
        :type json_input: list(dict)
        """
        self.validate_create_json(json_input)
        self.add_annotations(json_input)

    def validate_create_json(self, json_input):
        """ "Validate input JSON for creating an annotation.

        :param json_input: The provided JSON parameters.
        :type json_input: object
        """
        validator = jsonschema.Draft4Validator(schemas.CREATE_SCHEMA)
        self.validate_json(validator, json_input)

    def validate_json(self, validator, json_input):
        """Validate JSON input for any given schema.

        The incoming validator should already have schema information
        stored to validate input against.

        :param validator: The JSON validator.
        :type validator: class from jsonschema
        :param json_input: The JSON to validate.
        :type json_input: object

        :raises JSONInputError: If errors occurred while validating the
            input.
        """
        if validator.is_valid(json_input) is False:
            errors = sorted(validator.iter_errors(json_input), key=lambda e: e.path)
            raise JSONInputError(errors)

    def update_annotation(self, json_input):
        """Validate input and update an existing annotation per
        provided parameters.

        :param json_input: Parameters for updating annotation.
        :type json_input: dict
        """
        self.validate_update_json(json_input)
        self.parse_file()
        to_add = json_input.get(constants.ADD)
        to_replace = json_input.get(constants.REPLACE)
        to_remove = json_input.get(constants.REMOVE)
        if to_remove:
            self.remove_annotations(to_remove)
        if to_replace:
            self.replace_annotations(to_replace)
        if to_add:
            self.add_annotations(to_add)

    def validate_update_json(self, json_input):
        """Validate input JSON for updating an annotation.

        :param json_input: The provided JSON parameters.
        :type json_input: object
        """
        validator = jsonschema.Draft4Validator(schemas.UPDATE_SCHEMA)
        self.validate_json(validator, json_input)

    def add_annotations(self, annotation_metadata):
        """Add new annotations to the existing annotation.

        :param annotation_metadata: Information on the new source
            annotations.
        :type annotation_metadata: list(dict)
        """
        for annotation in annotation_metadata:
            self.add_source(annotation)

    def replace_annotations(self, annotation_metadata):
        """Replace existing annotations with specified sources.

        Replaces annotations based on the "prefix" of the new source,
        so these must match for desired behavior.

        :param annotation_metadata: Information on which sources to
            replace from the existing annotations.
        :type annotation_metadata: list(dict)
        """
        for annotation in annotation_metadata:
            identifier = annotation.get(constants.PREFIX)
            self.remove_identifier(identifier)
            self.add_source(annotation)

    def remove_annotations(self, annotation_metadata):
        """Update existing annotations by removing specified sources.

        :param annotation_metadata: Information on which sources to
            remove from the existing annotations.
        :type annotation_metadata: list(dict)
        """
        for annotation in annotation_metadata:
            identifier = annotation[constants.PREFIX]
            self.remove_identifier(identifier)

    def remove_identifier(self, identifier):
        """Remove a given source from annotations and metadata.

        The source's "prefix" is the expected identifier.

        :param identifier: The identifier for the annotation source.
        :type identifier: str
        """
        for item in self.annotations:
            if item.get(identifier):
                del item[identifier]
            if item.get(constants.CYTOBAND, {}).get(identifier):
                del item[constants.CYTOBAND][identifier]
        if identifier in self.metadata:
            del self.metadata[identifier]

    def parse_file(self):
        """Load the existing information for the complete annotation.

        Update self.metadata and self.annotations with loaded content.

        NOTE: If file does not exist, FileHandler.get_handle() returns
        an empty generator, so no contents will be loaded.
        """
        contents = {}
        file_handle = FileHandler(self.file_path, binary=True).get_handle()
        for handle in file_handle:
            #  Expecting only JSON for now
            contents = json.load(handle)
        metadata = contents.get(constants.METADATA)
        annotations = contents.get(constants.ANNOTATION)
        if not metadata:
            logging.warning("No annotation metadata found in file: %s", self.file_path)
        else:
            self.metadata = metadata
            logging.info("Existing annotations' metadata found.")
        if not annotations:
            logging.warning("No annotations found in existing file: %s", self.file_path)
        else:
            self.annotations = annotations
            logging.info("Existing annotations found.")

    def add_source(self, annotation_metadata):
        """Add metadata and annotations from a source file.

        If the source file is marked as an initial annotation, add it
        directly to self.annotations. If not, merge it to the existing
        annotations in self.annotations.

        :param annotation_metadata: Information on how to process the
            annotation (e.g. parsing, merging, etc.)
        :type annotation_metadata: dict
        """
        files = annotation_metadata.get(constants.FILES, [])
        prefix = annotation_metadata.get(constants.PREFIX)
        merge_info = annotation_metadata.get(constants.MERGE)
        parser_metadata = annotation_metadata.get(constants.PARSER)
        split_fields = annotation_metadata.get(constants.SPLIT_FIELDS)
        replacement_fields = annotation_metadata.get(constants.REPLACEMENT_FIELDS)
        filter_fields = annotation_metadata.get(constants.FILTER)
        fields_to_keep = annotation_metadata.get(constants.KEEP_FIELDS)
        fields_to_drop = annotation_metadata.get(constants.DROP_FIELDS)
        base_annotation = annotation_metadata.get(constants.SOURCE)
        metadata = annotation_metadata.get(constants.METADATA)
        cytoband_metadata = annotation_metadata.get(constants.CYTOBAND)
        for file_path in files:
            parser = self.create_parser(file_path, parser_metadata)
            source_annotation = SourceAnnotation(
                parser,
                filter_fields=filter_fields,
                fields_to_keep=fields_to_keep,
                fields_to_drop=fields_to_drop,
                split_fields=split_fields,
                replacement_fields=replacement_fields,
            ).make_annotation()
            if not source_annotation:
                log.warning("No annotations created from source file: %s", file_path)
            else:
                if base_annotation:
                    log.info(
                        "Adding initial annotations from source file: %s", file_path
                    )
                    self.annotations += [
                        {prefix: [entry]} for entry in source_annotation
                    ]
                else:
                    log.info(
                        "Attempting to merge annotations from source file: %s",
                        file_path,
                    )
                    AnnotationMerge(
                        self.annotations, source_annotation, prefix, merge_info
                    ).merge_annotations()
        if prefix and metadata:
            self.metadata[prefix] = metadata
        if cytoband_metadata:
            self.add_cytoband_to_annotations(prefix, cytoband_metadata)

    def add_cytoband_to_annotations(self, prefix, cytoband_metadata):
        """Add calculated cytobands to all records for which
        calculation is feasible.

        :param prefix: Prefix used for annotation source for which
            cytoband calculation is made.
        :type prefix: str
        :param cytoband_metadata: Metadata for calculating cytoband.
        :type cytoband_metadata: dict
        """
        cytoband_reference_file = cytoband_metadata.get(constants.REFERENCE_FILE)
        cytoband_locations = get_cytoband_locations(cytoband_reference_file)
        if cytoband_locations:
            for record in self.annotations:
                if record.get(prefix):
                    add_cytoband_field(
                        record, prefix, cytoband_metadata, cytoband_locations
                    )
        else:
            log.info(
                "No attempt to calculate cytobands due to lack of information from"
                " reference file for annotation with prefix: %s",
                prefix,
            )

    def create_parser(self, file_path, parser_metadata):
        """Create a parser class for a source file.

        :param file_path: Path of the source file.
        :type file_path: str
        :param parser_metadata: Information on which parser to use for
            the source file and which kwargs to pass to it.
        :type parser_metadata: dict
        :returns: A parser for the source file.
        :rtype: class from parsers.py
        """
        parser_type = parser_metadata[constants.PARSER_CHOICE]
        parser_kwargs = parser_metadata.get(constants.PARAMETERS, {})
        return constants.PARSERS_AVAILABLE[parser_type](file_path, **parser_kwargs)

    def write_file(self):
        """Write the merged metadata and annotations to file as JSON.

        If file already exists, will be rewritten.
        """
        with open(self.file_path, "w+") as file_handle:
            contents = {
                constants.METADATA: self.metadata,
                constants.ANNOTATION: self.annotations,
            }
            json.dump(contents, file_handle, indent=4)
