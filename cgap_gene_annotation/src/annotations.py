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

import jsonschema

from . import constants, schemas
from .cytoband import add_cytoband_field, get_cytoband_locations
from .merge import AnnotationMerge
from .utils import FileHandler


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
    """

    def __init__(
        self,
        parser,
        filter_fields=None,
        fields_to_keep=None,
        fields_to_drop=None,
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
        :param fields_to_drop: Fieds from the record to exclude from the
            annotation.
        :type fields_to_drop: list(str)
        """
        self.parser = parser
        self.filter_fields = filter_fields
        self.fields_to_keep = fields_to_keep
        self.fields_to_drop = fields_to_drop

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
            if self.filter_fields:
                record = self.filter_record(record, self.filter_fields)
                if not record:
                    log.debug("Filtered out record: %s" % record)
                    continue
            if self.fields_to_keep or self.fields_to_drop:
                if self.fields_to_keep:
                    record = self.retain_fields(record, self.fields_to_keep)
                elif self.fields_to_drop:
                    record = self.remove_fields(record, self.fields_to_drop)
                if not record:
                    log.debug("Filtered out record: %s" % record)
                    continue
            annotation.append(record)
        return annotation

    def filter_record(self, record, filter_fields):
        """Determine record inclusion/exclusion in annotation.

        Given fields and permissable values, only keep the record if
        all fields are present and record's values for those fields are
        all permitted.

        :param record: A parsed record from a source file.
        :type record: dict
        :param filter_fields: The field names and their permissible
            values to qualify for inclusion in the annotation.
        :type filter_fields: dict
        :returns: The incoming record if all filter fields are
            permissible or None.
        :rtype: dict or None
        """
        for field, permissible_values in filter_fields.items():
            field_value = record.get(field)
            if field_value is None:
                record = None
                break
            if isinstance(field_value, str):
                if field_value not in permissible_values:
                    record = None
                    break
            elif isinstance(field_value, list):
                intersection = set(field_value).intersection(set(permissible_values))
                if not intersection:
                    record = None
                    break
        return record

    def retain_fields(self, record, fields_to_keep):
        """Create record with only the requested fields.

        :param record: A parsed record from a source file.
        :type record: dict
        :param fields_to_keep: The fields to include in the result.
        :type fields_to_keep: list(str)
        :returns: A processed record with only the fields requested.
        :rtype: dict
        """
        result = {}
        for field in fields_to_keep:
            if record.get(field):
                result[field] = record[field]
        return result

    def remove_fields(self, record, fields_to_drop):
        """Exclude fields from a record.

        :param record: A parsed record from a source file.
        :type record: dict
        :param fields_to_drop: The fields to exclude from the record.
        :type fields_to_drop: list(str)
        :returns: A processed record with requested fields removed.
        :rtype: dict
        """
        for field in fields_to_drop:
            if record.get(field):
                del record[field]
        return record


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
