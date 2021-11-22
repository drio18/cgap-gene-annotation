import json
import logging

import jsonschema

from .merge import AnnotationMerge
from .utils import open_file
from . import constants, schemas

log = logging.getLogger(__name__)


class SourceAnnotation:
    """"""

    def __init__(
        self,
        parser,
        filter_fields=None,
        fields_to_keep=None,
        fields_to_drop=None,
    ):
        self.parser = parser
        self.filter_fields = filter_fields
        self.fields_to_keep = fields_to_keep
        self.fields_to_drop = fields_to_drop

    def make_annotation(self):
        """"""
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
        """"""
        for field, permissible_values in filter_fields.items():
            field_value = record.get(field)
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
        """"""
        result = {}
        for field in fields_to_keep:
            if record.get(field):
                result[field] = record[field]
        return result

    def remove_fields(self, record, fields_to_drop):
        """"""
        for field in fields_to_drop:
            if record.get(field):
                del record[field]
        return record


class JSONInputError(Exception):
    """"""
    def __init__(self, errors):
        self.errors = errors
        super().__init__()

    def __str__(self):
        """"""
        error_numbers = str(len(self.errors))
        error_messages = []
        first_line = (
            "%s validation error(s) found in the given JSON.\n" % error_numbers
        )
        error_messages.append(first_line)
        for error in self.errors:
            msg = (
                "Location: %s\n"
                "Error: %s\n"
            ) % (".".join([str(x) for x in error.path]), error.message)
            error_messages.append(msg)
        return "\n".join(error_messages)


class GeneAnnotation:
    """
    TODO: Allow merge of annotation source via metadata or via
    addition of formed annotation?
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.metadata = {}
        self.annotations = []

    def create_annotation(self, json_input):
        """"""
        self.validate_create_json(json_input)
        self.add_annotations(json_input)

    def validate_create_json(self, json_input):
        """"""
        validator = jsonschema.Draft4Validator(schemas.CREATE_SCHEMA)
        self.validate_json(validator, json_input)

    def validate_json(self, validator, json_input):
        """"""
        if validator.is_valid(json_input) is False:
            errors = sorted(validator.iter_errors(json_input), key=lambda e: e.path)
            raise JSONInputError(errors)

    def update_annotation(self, json_input):
        """"""
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
        """"""
        validator = jsonschema.Draft4Validator(schemas.UPDATE_SCHEMA)
        self.validate_json(validator, json_input)

    def add_annotations(self, annotation_metadata):
        """"""
        for annotation in annotation_metadata:
            self.add_source(annotation)

    def replace_annotations(self, annotation_metadata):
        """"""
        for annotation in annotation_metadata:
            identifier = annotation.get(constants.PREFIX)
            self.remove_identifier(identifier)
            self.add_source(annotation)

    def remove_annotations(self, annotation_metadata):
        """"""
        for annotation in annotation_metadata:
            identifier = annotation[constants.PREFIX]
            self.remove_identifier(identifier)

    def remove_identifier(self, identifier):
        """"""
        for item in self.annotations:
            if item.get(identifier):
                del item[identifier]
        if identifier in self.metadata:
            del self.metadata[identifier]

    def parse_file(self):
        """"""
        contents = {}
        file_handle = open_file(self.file_path, binary=True)
        for handle in file_handle:
            #  Expecting only JSON for now
            contents = json.load(handle)
        metadata = contents.get(constants.METADATA)
        annotations = contents.get(constants.ANNOTATION)
        if not metadata:
            logging.warning("No annotation metadata found in file: %s." % self.file_path)
        else:
            self.metadata = metadata
            logging.info("Existing annotations' metadata found.")
        if not annotations:
            logging.warning("No annotations found in existing file: %s." %
                    self.file_path)
        else:
            self.annotations = annotations
            logging.info("Existing annotations found.")

    def add_source(self, annotation_metadata):
        """"""
        files = annotation_metadata.get(constants.FILES, [])
        prefix = annotation_metadata.get(constants.PREFIX)
        merge_info = annotation_metadata.get(constants.MERGE)
        parser_metadata = annotation_metadata.get(constants.PARSER)
        filter_fields = annotation_metadata.get(constants.FILTER)
        fields_to_keep = annotation_metadata.get(constants.KEEP_FIELDS)
        fields_to_drop = annotation_metadata.get(constants.DROP_FIELDS)
        base_annotation = annotation_metadata.get(constants.SOURCE)
        metadata = annotation_metadata.get(constants.METADATA)
        for file_path in files:
            parser = self.create_parser(file_path, parser_metadata)
            source_annotation = SourceAnnotation(
                parser,
                filter_fields=filter_fields,
                fields_to_keep=fields_to_keep,
                fields_to_drop=fields_to_drop,
            ).make_annotation()
            if not source_annotation:
                log.warning("No annotations created from source file: %s." % file_path)
            else:
                if base_annotation:
                    log.info(
                        "Adding initial annotations from source file: %s" % file_path
                    )
                    self.annotations += [{prefix: [entry]} for entry in
                            source_annotation]
                else:
                    log.info(
                        "Attempting to merge annotations from source file: %s"
                        % file_path
                    )
                    AnnotationMerge(
                        self.annotations, source_annotation, prefix, merge_info
                    ).merge_annotations()
        if prefix and metadata:
            self.metadata[prefix] = metadata

    def create_parser(self, file_path, parser_metadata):
        """"""
        parser_type = parser_metadata[constants.PARSER_CHOICE]
        parser_kwargs = parser_metadata.get(constants.PARAMETERS, {})
        return constants.PARSERS_AVAILABLE[parser_type](file_path, **parser_kwargs)


    def write_file(self):
        """"""
        with open(self.file_path, "w+") as file_handle:
            contents = {constants.METADATA: self.metadata, constants.ANNOTATION:
                    self.annotations}
            json.dump(contents, file_handle, indent=4)
