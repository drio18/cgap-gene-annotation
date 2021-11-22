import logging
import re

from Bio import SeqIO

from .utils import open_file


def get_lines(file_path):
    """"""
    file_handle = open_file(file_path)
    for handle in file_handle:
        for line in handle:
            yield line.strip()


class TSVParser:
    """"""

    FIELD_SEPARATOR = "\t"

    def __init__(
        self,
        file_path,
        header=None,
        header_line=None,
        comment_characters="#",
        empty_fields=tuple([""]),
        list_identifier=None,
        strip_characters=(" '" + '"'),
    ):
        self.file_path = file_path
        self.header = header
        self.header_line = header_line
        self.comment_characters = comment_characters
        self.empty_fields = empty_fields
        self.list_identifier = list_identifier
        self.strip_characters = strip_characters

    def get_records(self):
        """"""
        for idx, line in enumerate(get_lines(self.file_path)):
            if self.header_line is not None and self.header is None:
                if idx == self.header_line:
                    self.header = self.parse_header(line)
            elif line.startswith(self.comment_characters):
                continue
            elif self.header is None:
                self.header = self.parse_header(line)
            else:
                record = self.parse_entry(line)
                self.remove_empty_fields(record)
                if record:
                    yield record

    def parse_header(self, entry):
        """"""
        entry = entry.strip(self.comment_characters)
        header = [field.strip() for field in entry.split(self.FIELD_SEPARATOR) if field]
        return header

    def parse_entry(self, entry):
        """"""
        fields = {}
        if entry:
            field_values = entry.split(self.FIELD_SEPARATOR)
            field_values = [
                value.strip(self.strip_characters) for value in field_values
            ]
            if self.list_identifier is not None:
                for idx, value in enumerate(field_values):
                    if self.list_identifier in value:
                        new_value = [
                            x for x in value.split(self.list_identifier) if x.strip()
                        ]
                        field_values[idx] = new_value
            fields = dict(zip(self.header, field_values))
        return fields

    def remove_empty_fields(self, record):
        """"""
        fields_to_remove = []
        for field_name, field_value in record.items():
            if field_value in self.empty_fields:
                fields_to_remove.append(field_name)
        for field_name in fields_to_remove:
            del record[field_name]


class CSVParser(TSVParser):
    """"""

    FIELD_SEPARATOR = ","


class GTFParser(TSVParser):
    """
    GFF V2 https://useast.ensembl.org/info/website/upload/gff.html
    """

    ATTRIBUTE_SEPARATOR = ";"
    ATTRIBUTE_SPLIT = '"'
    ATTRIBUTE = "attribute"
    HEADER = [
        "seqname",
        "source",
        "feature",
        "start",
        "end",
        "score",
        "strand",
        "frame",
        ATTRIBUTE,
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, header=self.HEADER, empty_fields=["."], **kwargs)

    def parse_entry(self, entry):
        """"""
        fields = {}
        if entry:
            fields = dict(zip(self.header, entry.split(self.FIELD_SEPARATOR)))
        attributes = fields.get(self.ATTRIBUTE, "")
        if attributes:
            attributes = attributes.split(self.ATTRIBUTE_SEPARATOR)
            parsed_attributes = {}
            for attribute in attributes:
                attribute = attribute.strip()
                if not attribute or (attribute in self.empty_fields):
                    continue
                attribute_name, attribute_value = [
                    x.strip() for x in attribute.split(self.ATTRIBUTE_SPLIT) if x
                ]
                if attribute_name in parsed_attributes:
                    attribute_value = list(attribute_value)
                    previous_value = parsed_attributes[attribute_name]
                    if isinstance(previous_value, str):
                        attribute_value.append(previous_value)
                    elif isinstance(previous_value, list):
                        attribute_value = attribute_value + previous_value
                parsed_attributes[attribute_name] = attribute_value
            fields[self.ATTRIBUTE] = parsed_attributes
        return fields


class GenBankParser:
    """
    https://www.ncbi.nlm.nih.gov/Sitemap/samplerecord.html
    """

    # GenBank formatting constants
    ANNOTATIONS = "annotations"
    FIELDS_TO_KEEP = ["id", "name", "description", ANNOTATIONS]
    COMMENT = "comment"
    GENE_TYPE = "gene"
    DB_XREF = "db_xref"
    GENE_QUALIFIER_FIELDS = ["gene", DB_XREF]
    QUALIFIER_DB_XREF_SPLIT = ":"
    SUMMARY_PATTERN = re.compile("\nSummary:")

    # SeqIO constants
    GENBANK = "genbank"  # SeqIO input file specification

    # Class constants
    SUMMARY_FIELD_NAME = "summary"

    def __init__(self, file_path):
        self.file_path = file_path

    def get_records(self):
        """"""
        # TODO: Error handling here. Consider rewriting if too slow with SeqIO
        for seq_record in SeqIO.parse(self.file_path, self.GENBANK):
            record = self.parse_entry(seq_record)
            yield record

    def parse_entry(self, seq_record):
        """"""
        result = {}
        seq_record_attributes = seq_record.__dict__
        for field in self.FIELDS_TO_KEEP:
            field_value = seq_record_attributes.get(field)
            if field_value:
                if field == self.ANNOTATIONS:
                    summary = self.get_summary(field_value)
                    if summary:
                        result[self.SUMMARY_FIELD_NAME] = summary
                result[field] = field_value
        return result

    def get_summary(self, annotations):
        """"""
        summary = None
        comment = annotations.get(self.COMMENT)
        if comment:
            summary_search = self.SUMMARY_PATTERN.search(comment)
            if summary_search:
                summary_end_index = summary_search.end()
                summary = comment[summary_end_index:].replace("\n", " ").strip()
        return summary


class UniProtDATParser:
    """Need to loop through all lines in file before yielding
    records due to annoying data structure here.

    This is spiking memory usage at the moment ...
    """

    FIELD_SEPARATOR = "\t"
    ID_SPLIT_CHARACTER = "-"
    EMPTY_FIELD = "-"
    UNIPROT_ACCESSION_KEY = "UniProtKB-AC"

    def __init__(self, file_path):
        self.file_path = file_path
        self.records = {}

    def get_records(self):
        for line in get_lines(self.file_path):
            uniprot_accession, database, database_id = self.get_line_values(line)
            self.add_to_record(uniprot_accession, database, database_id)
        for key, value in self.records.items():
            record = self.reformat_record(key, value)
            yield record

    def get_line_values(self, line):
        """"""
        uniprot_accession = ""
        database = ""
        database_id = ""
        if line:
            uniprot_accession, database, database_id = [
                x.strip() for x in line.split(self.FIELD_SEPARATOR)
            ]
        uniprot_accession = uniprot_accession.split(self.ID_SPLIT_CHARACTER)[0]
        return (uniprot_accession, database, database_id)

    def add_to_record(self, uniprot_accession, database, database_id):
        """"""
        if (
            uniprot_accession
            and database
            and database_id
            and database_id != self.EMPTY_FIELD
        ):
            record = self.records.get(uniprot_accession)
            if record is None:
                record = {}
                self.records[uniprot_accession] = record
            database_values = record.get(database)
            if database_values is None:
                record[database] = set()
            record[database].add(database_id)

    def reformat_record(self, uniprot_accession, record):
        """"""
        result = {}
        result[self.UNIPROT_ACCESSION_KEY] = [uniprot_accession]
        for key, value in record.items():
            result[key] = list(value)
        return result
