"""All parsers for annotation source text files.

Each parser MUST contain a get_records() method that returns a
generator of dictionaries, where each dictionary is a single record
containing field names as keys and the record's field value as values.

Parsers should accept **kwargs in __init__() method so no exception
raised if parameter passed that isn't expected/used in the class.

If adding a new parser here, update PARSERS_AVAILABLE in
constants module to make available for use within package.

If adding any new kwarg to any parser, update schemas to validate it.

Classes:
    - TSVParser: General-purpose parser for TSVs.
    - CSVParser: General-purpose parser for CSVs.
    - GTFParser: Parser for GTF (Gene Transfer Format) files.
    - GenBankParser: Parser for GenBank Flat File Format files.
    - UniProtDATParser: Parser for UniProt DAT file.
"""

import re
from xml.etree import ElementTree as ET

from .utils import FileHandler


# Parser kwarg names used in schema
HEADER = "header"
HEADER_LINE = "header_line"
COMMENT_CHARACTERS = "comment_characters"
EMPTY_FIELDS = "empty_fields"
LIST_IDENTIFIER = "list_identifier"
STRIP_CHARACTERS = "strip_characters"
SPLIT_FIELDS = "split_fields"
SPLIT_FIELDS_NAME = "name"
SPLIT_FIELDS_CHARACTER = "character"
SPLIT_FIELDS_INDEX = "index"
SPLIT_FIELDS_FIELD = "field"


def get_lines(file_path):
    """Get lines from a file and return as generator.

    If FileHandler.handle result is empty (file couldn't be opened),
    result here will be an empty generator as well.

    :param file_path: The path to the source file.
    :type file_path: str
    :returns: Lines from the file.
    :rtype: collections.Iterable[str]
    """
    file_handle = FileHandler(file_path).handle
    for handle in file_handle:
        for line in handle:
            yield line.strip()


def create_split_fields(record, split_fields):
    """Split field in record according to parameters, and update
    the record with the new field.

    Useful for when source file provides Ensembl ID as ID.version
    and only ID can be matched.

    :param record: The record to update.
    :type record: dict
    :param split_fields: Parameters for creating new field by
        splitting existing field in record.
    :type split_fields: dict
    """
    for split_field in split_fields:
        field_to_split = split_field.get(SPLIT_FIELDS_FIELD)
        split_character = split_field.get(SPLIT_FIELDS_CHARACTER)
        split_index = split_field.get(SPLIT_FIELDS_INDEX)
        field_name = split_field.get(SPLIT_FIELDS_NAME)
        field_value = record.get(field_to_split)
        if isinstance(field_value, str):
            split_value = field_value.split(split_character)
            if split_index < len(split_value):
                new_value = split_value[split_index]
                record[field_name] = new_value


class TSVParser:
    """Parser for general, flat TSV files.

    If file is not "flat," can use this as parent class with a few
    additional methods for nested portions (e.g. see GTFParser).

    Primary method for use is get_records().

    :var file_path: The path to the source file.
    :vartype file_path: str
    :var header: The header for the records.
    :vartype header: list(str)
    :var header_line: The line the header is located on (0-based).
    :vartype header_line: int
    :var comment_characters: Characters at the start of a line in the
        file that indicate the line is a comment and should be omitted.
    :vartype comment_characters: str
    :var empty_fields: Characters in lines signifying a value is
        missing for that field.
    :vartype empty_fields: list(str) or tuple(str)
    :var list_identifier: Characters in lines signifying the values for
        a field are a list.
    :vartype list_identifier: str
    :var strip_characters: Characters to remove from lines if present.
    :vartype strip_characters: str
    :var split_fields: Parameters for creating new fields in a
        record from existing fields by splitting the string in the
        existing field.
    :vartype split_fields: list(dict)

    """

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
        split_fields=None,
        **kwargs,
    ):
        """Create the class and set attributes.

        :param file_path: The path to the source file.
        :type file_path: str
        :param header: The header for the records.
        :type header: list(str)
        :param header_line: The line the header is located on (0-based).
        :type header_line: int
        :param comment_characters: Characters at the start of a line in the
            file that indicate the line is a comment and should be omitted.
        :type comment_characters: str
        :param empty_fields: Characters in lines signifying a value is
            missing for that field.
        :type empty_fields: list(str) or tuple(str)
        :param list_identifier: Characters in lines signifying the values for
            a field are a list.
        :type list_identifier: str
        :param strip_characters: Characters to remove from lines if present.
        :type strip_characters: str
        :param split_fields: Parameters for creating new fields in a
            record from existing fields by splitting the string in the
            existing field.
        :type split_fields: list(dict)
        """
        self.file_path = file_path
        self.header = header
        self.header_line = header_line
        self.comment_characters = comment_characters
        self.empty_fields = empty_fields
        self.list_identifier = list_identifier
        self.strip_characters = strip_characters
        self.split_fields = split_fields

    def get_records(self):
        """Identify header and create records from source file.

        :returns: Records from file, as a key/value pairing of field
            names from header and values.
        :rtype: collections.Iterable[dict]
        """
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
                if self.split_fields:
                    create_split_fields(record, self.split_fields)
                if record:
                    yield record

    def parse_header(self, entry):
        """Convert header line to field names.

        :param entry: The header line.
        :type entry: str
        :returns: The header field names.
        :rtype: list(str)
        """
        entry = entry.strip(self.comment_characters)
        header = [
            field.strip(self.strip_characters)
            for field in entry.split(self.FIELD_SEPARATOR) if field
        ]
        return header

    def parse_entry(self, entry):
        """Convert line to record.

        :param entry: The line.
        :type entry: str
        :returns: The record, with header field names matched to values
            from the line.
        :rtype: dict
        """
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
        """Remove fields from record if field value is considered
        empty.

        :param record: The record to update.
        :type record: dict
        """
        fields_to_remove = []
        for field_name, field_value in record.items():
            if field_value in self.empty_fields:
                fields_to_remove.append(field_name)
        for field_name in fields_to_remove:
            del record[field_name]


class CSVParser(TSVParser):
    """Parser for general, flat CSV files.

    All args, kwargs, and methods as for TSVParser.
    """

    FIELD_SEPARATOR = ","


class GTFParser(TSVParser):
    """Parser for GTF (Gene Transfer Format) files.

    GTF files are non-flat TSV files, which may be identical to v2 GFF
    files (see https://useast.ensembl.org/info/website/upload/gff.html).

    Rewrites parent class' parse_entry() method to correctly parse non-
    flat sections of lines; otherwise, methods as for parent TSVParser.
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
    EMPTY_FIELDS = ["."]

    def __init__(self, file_path, **kwargs):
        """Create class and set attributes.

        Header and empty field characters are fixed.
        """
        header = kwargs.pop(HEADER, None) or self.HEADER
        empty_fields = kwargs.pop(EMPTY_FIELDS, None) or self.EMPTY_FIELDS
        super().__init__(file_path, header=header, empty_fields=empty_fields, **kwargs)

    def parse_entry(self, entry):
        """Convert line to record.

        :param entry: The line.
        :type entry: str
        :returns: The record, with header field names matched to values
            from the line.
        :rtype: dict
        """
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
    """Class for parsing GenBank flat files.

    For more information on these files, see:
    https://www.ncbi.nlm.nih.gov/Sitemap/samplerecord.html

    Primary method for use is get_records().

    NOTE: BioPython's Bio.seqIO module contains full parser for these
    files, but it is quite slow, mostly because it parses/stores all of
    the lines on a record and the majority of these are not required
    for current CGAP purposes.

    :var file_path: The path to the source file.
    :vartype file_path: str
    """

    # File constants
    LOCUS = "LOCUS"
    DEFINITION = "DEFINITION"
    ACCESSION = "ACCESSION"
    VERSION = "VERSION"
    KEYWORDS = "KEYWORDS"
    SOURCE = "SOURCE"
    COMMENT = "COMMENT"
    PRIMARY = "PRIMARY"
    FEATURES = "FEATURES"
    ORIGIN = "ORIGIN"
    ENTRY_END = "//"
    SUMMARY_STRING = "Summary:"

    # File sections with lines to parse
    LINE_STARTS_OF_INTEREST = [
        DEFINITION,
        ACCESSION,
        VERSION,
        COMMENT,
    ]

    # File sections with lines to ignore
    LINE_STARTS_IGNORED = [
        LOCUS,
        KEYWORDS,
        SOURCE,
        PRIMARY,
        FEATURES,
        ORIGIN,
    ]

    # Record field names (as in BioPython seqIO where applicable)
    DEFINITION_FIELD = "description"
    ACCESSION_FIELD = "name"
    VERSION_FIELD = "id"
    COMMENT_FIELD = "comment"
    SUMMARY_FIELD = "summary"

    def __init__(self, file_path, **kwargs):
        """Create class and set attributes.

        :param file_path: The path to the source file for annotations.
        :type file_path: str
        """
        self.file_path = file_path

    def get_records(self):
        """Create records from source file.

        Since these files are quite large, skip over lines that don't
        fall within the sections of interest (currently most lines are
        entirely ignored).

        :returns: Records from file, as a key/value pairing of field
            names and values.
        :rtype: collections.Iterable[dict]
        """
        section_words = {}
        current_section = None
        for line in get_lines(self.file_path):
            line_words = line.split()
            if not line_words:
                continue
            first_word = line_words[0]
            if first_word in self.LINE_STARTS_OF_INTEREST:
                current_section = first_word
                section_words[first_word] = line_words[1:]
            elif first_word in self.LINE_STARTS_IGNORED:
                current_section = None
            elif current_section in self.LINE_STARTS_OF_INTEREST:
                section_words[current_section] += line_words
            elif first_word == self.ENTRY_END:
                record = self.create_record_from_sections(section_words)
                yield record
                current_section = None
                section_words.clear()

    def create_record_from_sections(self, section_words):
        """Create individual record.

        :param section_words: The sections and corresponding words.
        :type section_words: dict
        :returns: The record generated.
        :rtype: dict
        """
        record = {}
        for section, words in section_words.items():
            new_fields = {}
            if section == self.DEFINITION:
                new_fields = self.make_simple_field(self.DEFINITION_FIELD, words)
            elif section == self.ACCESSION:
                new_fields = self.make_simple_field(self.ACCESSION_FIELD, words)
            elif section == self.VERSION:
                new_fields = self.make_simple_field(self.VERSION_FIELD, words)
            elif section == self.COMMENT:
                new_fields = self.parse_comment_section(words)
            record.update(new_fields)
        return record

    def make_simple_field(self, field_key, words):
        """Match field name with field value with no parsing required.

        :param field_key: The field name used within a record.
        :type field_key: str
        :param words: The words of the section corresponding to the
            field_key.
        :type words: list(str)
        :returns: Key, value pair of field name and sentence(s) from
            word.
        :rtype: dict
        """
        result = {}
        if field_key and words:
            result[field_key] = " ".join(words)
        return result

    def parse_comment_section(self, words):
        """Get field key, value pairs from COMMENT section.

        Pull out the summary from the comment since it is key field for
        gene annotations from these source files.

        :param words: The words of the section.
        :type words: list(str)
        :returns: Key, value pair(s) of field name(s) and sentence(s)
            from the section.
        :rtype: dict
        """
        result = {}
        if words:
            try:
                summary_index = words.index(self.SUMMARY_STRING)
                comment_without_summary = " ".join(words[:summary_index])
                if comment_without_summary:
                    result[self.COMMENT_FIELD] = comment_without_summary
                summary = " ".join(words[(summary_index + 1):])
                if summary:
                    result[self.SUMMARY_FIELD] = summary
            except ValueError:  # Most, but not all, records have a summary
                result[self.COMMENT_FIELD] = " ".join(words)
        return result


class UniProtDATParser:
    """Parser for UniProt DAT files.

    These files have an odd structure such that lines need to be
    accumulated to create a single record, but the lines for a record
    are not necessarily consecutive.

    Primary method for use is get_records(). Method is currently
    sacrificing memory for speed due to issue above; see method's
    docstring for more info and alternative algorithm.

    :var file_path: The path to the source file.
    :vartype file_path: str
    :var records: Accumulated records from lines of source file. Keys
        are UniProt accessions, and values are database information
        associated with the accessions.
    :vartype records: dict
    """

    FIELD_SEPARATOR = "\t"
    ID_SPLIT_CHARACTER = "-"
    EMPTY_FIELD = "-"
    UNIPROT_ACCESSION_KEY = "UniProtKB-AC"

    def __init__(self, file_path, **kwargs):
        """Create the class and set attributes.

        :param file_path: The path to the source file.
        :type file_path: str
        """
        self.file_path = file_path
        self.records = {}

    def get_records(self):
        """Create all records from source file.

        Since lines for a given record are not always consecutive, we
        generate all records and then yield one at a time. This makes
        self.records a large dictionary but only requires one loop
        through all lines, opting for speed over memory.

        An alternative algortithm that was explored that prioritizes
        memory over speed is to loop through all lines matching line
        indices to accessions, and then looping through lines again for
        each record until the record is finished. The necessity of
        reading from disk so many times was not worth the decreased
        memory utilization.

        :returns: The annotation records from the source file.
        :rtype: collections.Iterable[dict]
        """
        for line in get_lines(self.file_path):
            uniprot_accession, database, database_id = self.get_line_values(line)
            self.add_to_record(uniprot_accession, database, database_id)
        for key, value in self.records.items():
            record = self.reformat_record(key, value)
            yield record

    def get_line_values(self, line):
        """Parse a line for its values.

        :param line: A line from the source file.
        :type line: str
        :returns: The UniProt accession, database, and database ID of
            the given line.
        :rtype: (str, str, str)
        """
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
        """Add values from a line to a record.

        Update self.records, creating a new record if UniProt accession
        not yet seen.

        :param uniprot_accession: The UniProt accession of a line.
        :type uniprot_accession: str
        :param database: The database of a line.
        :type database: str
        :param database_id: The database ID of a line.
        :type database_id: str
        """
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
        """Reformat record from self.records to format for annotation.

        :param uniprot_accession: The UniProt accession of the record.
        :type uniprot_accession: str
        :param record: The record for the UniProt accession.
        :type record: dict
        :returns: Reformatted record as desired for annotation.
        :rtype: dict
        """
        result = {}
        result[self.UNIPROT_ACCESSION_KEY] = [uniprot_accession]
        for key, value in record.items():
            result[key] = list(value)
        return result


class XMLParser:
    """"""
    XML_START = "start"
    XML_END = "end"

    RECORD_PATH_SPLIT = "/"
    RECORD_PATH_ATTRIBUTE = re.compile(r"\[@[\w]*=[\w]*\]")

    def __init__(self, file_path, record_path=None, empty_fields=tuple([""]),
            list_identifier=None, split_fields=None, **kwargs):
        self.file_path = file_path
        self.record_path = self.parse_record_path(record_path)
        self.empty_fields = empty_fields
        self.list_identifier = list_identifier
        self.split_fields = split_fields

    def parse_record_path(self, record_path):
        """"""
        path = []
        if record_path:
            path_elements = [x for x in record_path.split(self.RECORD_PATH_SPLIT) if x]
            for idx, element in enumerate(path_elements):
                attributes = self.RECORD_PATH_ATTRIBUTE.findall(element)
                if attributes:
                    attribute_start = self.RECORD_PATH_ATTRIBUTE.search(element).start()
                    path_element = element[:attribute_start]
                    element_attributes = {}
                    for attribute in attributes:
                        attribute = attribute[2:-1]
                        key, value = [x.strip() for x in attribute.split("=")]
                        element_attributes[key] = value
                    path.append((path_element, element_attributes))
                else:
                    path.append((element, None))
        return path

    def get_records(self):
        """"""
        depth = -1
        child_depth = -1
        children = set()
        record = {}
        record_element = False
        current_path = [None for path_tuple in self.record_path]
        record_path_length = len(self.record_path)
        file_handle = FileHandler(self.file_path).handle
        for handle in file_handle:
            tree = ET.iterparse(handle, events=(self.XML_START, self.XML_END))
            _, root = next(tree)
            root.clear()  # Don't build the root tree?
            for event, element in tree:
                if event == self.XML_START:
                    depth += 1
                    if depth < record_path_length:
                        current_path[depth] = element
                        if self.is_path_to_record(current_path):
                            record_element = True
                elif event == self.XML_END:
                    if depth < record_path_length:
                        if self.is_path_to_record(current_path):
                            record_element = False
                            self.add_element_to_record(element, record)
                            if self.split_fields:
                                create_split_fields(record, self.split_fields)
                            yield record
                            record = {}
                            child_depth = -1
                        current_path[depth] = None
                    elif record_element:
                        if depth < child_depth:
                            self.add_element_to_record(element, record,
                                    children=children, depth=depth)
                            self.clear_children(children, depth)
                        else:
                            self.add_element_to_record(element, record)
                        child_depth = depth
                        children.add((element.tag, depth))
                    element.clear()
                    depth -= 1

    def is_path_to_record(self, path):
        """"""
        result = True
        if not path:
            result = False
        elif any(item is None for item in path):
            result = False
        else:
            for idx, element in enumerate(path):
                record_tag, record_attributes = self.record_path[idx]
                if element.tag != record_tag:
                    result = False
                    break
                if record_attributes:
                    attributes_match = True
                    element_attributes = element.attrib
                    for key, value in record_attributes.items():
                        element_value = element_attributes.get(key)
                        if element_value != value:
                            attributes_match = False
                            break
                    if not attributes_match:
                        result = False
                        break
        return result


    def add_element_to_record(self, element, record, children=None, depth=None):
        """"""
        tag = element.tag
        if children and depth:
            for child_tag, child_depth in children:
                if depth >= child_depth:
                    continue
                child_value = record.get(child_tag)
                if not child_value:
                    continue
                value_to_add = {child_tag: child_value}
                del record[child_tag]
                existing_tag_value = record.get(tag)
                if not existing_tag_value:
                    record[tag] = value_to_add
                else:
                    if child_tag in existing_tag_value:
                        record[tag] = [existing_tag_value, value_to_add]
                    else:
                        record[tag].update(value_to_add)
        elif len(element) == 0 and element.text:
            text = element.text.strip()
            if self.list_identifier and (self.list_identifier in text):
                text = text.split(self.list_identifier)
            if self.empty_fields and (text not in self.empty_fields):
                existing_tag_value = record.get(tag)
                if existing_tag_value:
                    if not isinstance(existing_tag_value, list):
                        existing_tag_value = [existing_tag_value]
                    new_tag_value = existing_tag_value + [text]
                    record[tag] = new_tag_value
                else:
                    record[tag] = text

    def clear_children(self, children, depth):
        """"""
        to_remove = []
        for child in children:
            child_depth = child[1]
            if child_depth > depth:
                to_remove.append(child)
        for child_to_remove in to_remove:
            children.remove(child_to_remove)
