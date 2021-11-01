import json
import logging

from .merge import AnnotationMerge
from .parsers import TSVParser, CSVParser, GTFParser, GenBankParser, UniProtDATParser

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

    @staticmethod
    def filter_record(record, filter_fields):
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

    @staticmethod
    def retain_fields(record, fields_to_keep):
        """"""
        result = {}
        for field in fields_to_keep:
            if record.get(field):
                result[field] = record[field]
        return result

    @staticmethod
    def remove_fields(record, fields_to_drop):
        """"""
        for field in fields_to_drop:
            if record.get(field):
                del record[field]
        return record


class GeneAnnotation:
    """
    TODO: Allow merge of annotation source via metadata or via
    addition of formed annotation?
    """

    PARSERS = {
        "TSV": TSVParser,
        "CSV": CSVParser,
        "GTF": GTFParser,
        "GenBank": GenBankParser,
        "UniProtDAT": UniProtDATParser,
    }

    def __init__(self, file_path):
        self.file_path = file_path
        self.annotation, self.metadata = self.parse_file(file_path)

    @staticmethod
    def parse_file(file_path):
        """"""
        # Try to open and load current gene annotation. If it doesn't exist, fine.
        # If it does, try to load contents
        return [], {}

    def add_annotations(self, annotation_metadata):
        """"""
        for annotation in annotation_metadata:
            metadata_check = self.check_metadata(annotation)
            if metadata_check:
                self.add_source(annotation)

    def check_metadata(self, metadata):
        """"""
        # Ensure metadata contains all required fields here, noting errors and deciding
        # whether to parse/add the annotation at this step
        return True

    def add_source(self, annotation):
        """"""
        # TODO: Update self.metadata with incoming metadata for each source
        files = annotation["files"]
        prefix = annotation["prefix"]
        merge_info = annotation.get("merge")
        parser_metadata = annotation["parser"]
        filter_fields = annotation.get("filter")
        fields_to_keep = annotation.get("fields_to_keep")
        fields_to_drop = annotation.get("fields_to_drop")
        for file_path in files:
            parser = self.create_parser(file_path, parser_metadata)
            source_annotation = SourceAnnotation(
                parser,
                filter_fields=filter_fields,
                fields_to_keep=fields_to_keep,
                fields_to_drop=fields_to_drop,
            ).make_annotation()
            if not source_annotation:
                log.warning(
                    "No annotations created from source file: %s." % file_path
                )
            else:
                if self.annotation:
                    log.info(
                        "Attempting to merge annotations from source file: %s"
                        % file_path
                    )
                    AnnotationMerge(
                        self.annotation, source_annotation, prefix, merge_info
                    ).merge_annotations()
                else:
                    log.info(
                        "Adding initial annotations from source file: %s" % file_path
                    )
                    self.annotation = [{prefix: [entry]} for entry in source_annotation]

    def create_parser(self, file_path, parser_metadata):
        """"""
        parser_type = parser_metadata["type"]
        parser_kwargs = parser_metadata.get("kwargs", {})
        return self.PARSERS[parser_type](file_path, **parser_kwargs)

    def replace_annotations(self, annotation_metadata):
        """"""

    def remove_annotations(self, identifiers):
        """"""
        # Also need to remove the metadata
        for identifier in identifiers:
            for item in self.annotation:
                if item.get(identifier):
                    del item[identifier]
            if identifier in self.metadata:
                del self.metadata[identifier]

    def write_file(self, style="JSON"):
        """"""
        with open(self.file_path, "w+") as file_handle:
            if style == "JSON":
                contents = {"Metadata": self.metadata, "Annotation": self.annotation}
                json.dump(contents, file_handle, indent=4)
