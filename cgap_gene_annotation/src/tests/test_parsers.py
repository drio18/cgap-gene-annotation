import io
from types import GeneratorType
from unittest import mock
from xml.etree import ElementTree as ET

import pytest

from .. import parsers


SPLIT_FIELDS = [
    {
        parsers.SPLIT_FIELDS_NAME: "fu",
        parsers.SPLIT_FIELDS_CHARACTER: ".",
        parsers.SPLIT_FIELDS_INDEX: 0,
        parsers.SPLIT_FIELDS_FIELD: "foo",
    }
]
GENBANK_COMMENT_LINE = "This gene has been reviewed by RefSeq"
GENBANK_COMMENT_WORDS = GENBANK_COMMENT_LINE.split()
GENBANK_SUMMARY_CONTENTS = "The gene does something"
GENBANK_SUMMARY_LINE = "Summary: " + GENBANK_SUMMARY_CONTENTS
GENBANK_SUMMARY_WORDS = GENBANK_SUMMARY_LINE.split()
GENBANK_DEFINITION_CONTENT = "Homo sapiens gene on chromosome 1"
GENBANK_DEFINITION_WORDS = GENBANK_DEFINITION_CONTENT.split()
GENBANK_ACCESSION_CONTENT = "NG00001"
GENBANK_ACCESSION_WORDS = GENBANK_ACCESSION_CONTENT.split()
GENBANK_VERSION_CONTENT = "NG00001.1"
GENBANK_VERSION_WORDS = GENBANK_VERSION_CONTENT.split()
GENBANK_LOCUS_CONENT = "A section that isn't parsed"


@pytest.mark.parametrize(
    "file_contents",
    [
        "",
        "foo\nbar\n",
        "foobar\n\n",
    ],
)
def test_get_lines(file_contents):
    """Test retrieval of lines from a file, returned in a generator."""
    file_path = "foo/bar"
    mock_file = io.StringIO(file_contents)
    with mock.patch(
        "cgap_gene_annotation.src.parsers.FileHandler.get_handle",
        return_value=[mock_file],
        create=True,
    ) as mocked_file:
        result = parsers.get_lines(file_path)
        assert isinstance(result, GeneratorType)
        result = list(result)
        assert result == file_contents.split("\n")[:-1]
        mocked_file.assert_called_once_with(file_path, binary=False)


@pytest.mark.parametrize(
    "file_contents,delimiter,expected",
    [
        ("", ",", []),
        (",", ",", [["", ""]]),
        ("foo,bar", ",", [["foo", "bar"]]),
        ("foo,bar", "\t", [["foo,bar"]]),
        ("foo,bar\nfu,bur\n", ",", [["foo", "bar"], ["fu", "bur"]]),
        ('foo,"bar"', ",", [["foo", "bar"]]),
    ],
)
def test_read_lines(file_contents, delimiter, expected):
    """Test retrieval of lines from file with csv.reader."""
    file_path = "foo/bar"
    mock_file = io.StringIO(file_contents)
    with mock.patch(
        "cgap_gene_annotation.src.parsers.FileHandler.get_handle",
        return_value=[mock_file],
        create=True,
    ) as mocked_file:
        result = parsers.read_lines(file_path, delimiter=delimiter)
        assert isinstance(result, GeneratorType)
        result = list(result)
        mocked_file.assert_called_once_with(file_path, binary=False)
        assert result == expected


@pytest.mark.parametrize(
    "record,split_fields,expected",
    [
        ({}, [], {}),
        ({"foo": "bar"}, [], {"foo": "bar"}),
        ({}, [{}], {}),
        ({"foo": "bar"}, [{}], {"foo": "bar"}),
        ({}, SPLIT_FIELDS, {}),
        ({"foo": "bar"}, SPLIT_FIELDS, {"foo": "bar", "fu": "bar"}),
        ({"foo": "bar.1"}, SPLIT_FIELDS, {"foo": "bar.1", "fu": "bar"}),
    ],
)
def test_create_split_fields(record, split_fields, expected):
    """Test creation of new field in record from existing field using
    given parameters.
    """
    parsers.create_split_fields(record, split_fields)
    assert record == expected


class TestTSVParser:
    @pytest.mark.parametrize(
        "record,empty_fields,expected",
        [
            ({"foo": "bar"}, [], {"foo": "bar"}),
            ({"foo": "bar"}, ["", " "], {"foo": "bar"}),
            ({"foo": "bar"}, ["bar"], {}),
            ({"foo": "bar", "fu": "bar"}, ["bar"], {}),
            ({"foo": "bur", "fu": "bar"}, ["bar"], {"foo": "bur"}),
            ({"foo": "bur", "fu": "bar"}, ["bar", "bur"], {}),
        ],
    )
    def test_remove_empty_fields(self, record, empty_fields, expected):
        """Test removal of given empty field values from given record."""
        parser = parsers.TSVParser(None, empty_fields=empty_fields)
        parser.remove_empty_fields(record)
        assert record == expected

    @pytest.mark.parametrize(
        "entry,comment_characters,expected",
        [
            (["foo", "bar"], "", ["foo", "bar"]),
            ([" foo", "bar "], "", ["foo", "bar"]),
            (["#foo", "bar"], "", ["#foo", "bar"]),
            (["foo", "bar"], "#", ["foo", "bar"]),
            (["#foo", "bar"], "#", ["foo", "bar"]),
            (["# foo", "bar"], "#", ["foo", "bar"]),
        ],
    )
    def test_parse_header(self, entry, comment_characters, expected):
        """Test header conversion to list of field names."""
        parser = parsers.TSVParser(None, comment_characters=comment_characters)
        assert parser.parse_header(entry) == expected

    @pytest.mark.parametrize(
        "entry,header,strip_characters,list_identifier,expected",
        [
            ([], ["fu", "bur"], None, None, {}),
            (
                ["foo", "bar"],
                ["fu", "bur"],
                None,
                None,
                {"fu": "foo", "bur": "bar"},
            ),
            (
                ["foo", "bar"],
                ["fu", "bur"],
                " '",
                None,
                {"fu": "foo", "bur": "bar"},
            ),
            (
                ["foo ", "'bar'"],
                ["fu", "bur"],
                " '",
                None,
                {"fu": "foo", "bur": "bar"},
            ),
            (
                ["foo", "bar"],
                ["fu", "bur"],
                None,
                "|",
                {"fu": "foo", "bur": "bar"},
            ),
            (
                ["foo", "bar|bor"],
                ["fu", "bur"],
                None,
                "|",
                {"fu": "foo", "bur": ["bar", "bor"]},
            ),
            (
                ["foo", "'bar|bor'"],
                ["fu", "bur"],
                " '",
                "|",
                {"fu": "foo", "bur": ["bar", "bor"]},
            ),
        ],
    )
    def test_parse_entry(
        self, entry, header, strip_characters, list_identifier, expected
    ):
        """Test conversion of entry line to a dictionary with header
        field names as keys and line entries as values.
        """
        parser = parsers.TSVParser(
            None,
            header=header,
            strip_characters=strip_characters,
            list_identifier=list_identifier,
        )
        assert parser.parse_entry(entry) == expected

    @pytest.mark.parametrize(
        "lines,header_line,header,expected_records,expected_header",
        [
            ([], None, None, [], None),
            ([["foo", "bar"]], None, None, [], ["foo", "bar"]),
            (
                [["foo", "bar"], ["fu", "bur"]],
                None,
                None,
                [{"foo": "fu", "bar": "bur"}],
                ["foo", "bar"],
            ),
            (
                [["#foo", "bar"], ["fu", "bur"]],
                None,
                None,
                [],
                ["fu", "bur"],
            ),
            (
                [["#foo", "bar"], ["fu", "bur"]],
                0,
                None,
                [{"foo": "fu", "bar": "bur"}],
                ["foo", "bar"],
            ),
            (
                [["foo", "bar"], ["fu", "bur"]],
                None,
                ["baz", "qux"],
                [{"baz": "foo", "qux": "bar"}, {"baz": "fu", "qux": "bur"}],
                ["baz", "qux"],
            ),
            (
                [["#foo", "bar"], ["fu", "bur"]],
                None,
                ["baz", "qux"],
                [{"baz": "fu", "qux": "bur"}],
                ["baz", "qux"],
            ),
            (
                [["foo", "bar"], ["fu", "bur"]],
                0,
                ["baz", "qux"],
                [{"baz": "foo", "qux": "bar"}, {"baz": "fu", "qux": "bur"}],
                ["baz", "qux"],
            ),
            (
                [["foo", "bar"], ["fu", "bur"], [""]],
                None,
                None,
                [{"foo": "fu", "bar": "bur"}],
                ["foo", "bar"],
            ),
        ],
    )
    @mock.patch("cgap_gene_annotation.src.parsers.read_lines")
    def test_get_records(
        self,
        mock_get_lines,
        lines,
        header_line,
        header,
        expected_records,
        expected_header,
    ):
        """Test conversion of lines to annotation records.

        Test relies on helper methods tested above.
        """
        mock_get_lines.return_value = lines
        parser = parsers.TSVParser(None, header_line=header_line, header=header)
        records = parser.get_records()
        assert isinstance(records, GeneratorType)
        records = list(records)
        assert records == expected_records
        assert parser.header == expected_header


class TestGTFParser:
    @pytest.mark.parametrize(
        "entry,expected",
        [
            ([], {}),
            (
                ["chrom", "foo", "gene", "1", "200", ".", "+", ".", 'fu "bar"'],
                {
                    "seqname": "chrom",
                    "source": "foo",
                    "feature": "gene",
                    "start": "1",
                    "end": "200",
                    "score": ".",
                    "strand": "+",
                    "frame": ".",
                    "attribute": {"fu": "bar"},
                },
            ),
            (
                [
                    "1",
                    "havana",
                    "gene",
                    "11869",
                    "14409",
                    ".",
                    "+",
                    ".",
                    (
                        'gene_id "ENSG00000223972"; gene_version "5";'
                        ' gene_name "DDX11L1"; gene_source "havana";'
                        ' gene_biotype "transcribed_unprocessed_pseudogene";'
                    ),
                ],
                {
                    "seqname": "1",
                    "source": "havana",
                    "feature": "gene",
                    "start": "11869",
                    "end": "14409",
                    "score": ".",
                    "strand": "+",
                    "frame": ".",
                    "attribute": {
                        "gene_id": "ENSG00000223972",
                        "gene_version": "5",
                        "gene_name": "DDX11L1",
                        "gene_source": "havana",
                        "gene_biotype": "transcribed_unprocessed_pseudogene",
                    },
                },
            ),
        ],
    )
    def test_parse_entry(self, entry, expected):
        """Test conversion of entry to record, particularly parsing of
        nested 'attribute' field.
        """
        result = parsers.GTFParser(None).parse_entry(entry)
        assert result == expected


class TestGenBankParser:
    @pytest.mark.parametrize("section_words,expected", [])
    def test_create_record_from_sections(self, section_words, expected):
        """"""
        result = parsers.GenBankParser(None).create_record_from_sections(section_words)
        assert result == expected

    @pytest.mark.parametrize(
        "field_key,words,expected",
        [
            ("", [], {}),
            ("foo", [], {}),
            ("", ["bar"], {}),
            ("foo", ["bar"], {"foo": "bar"}),
            ("foo", ["bar", "fu"], {"foo": "bar fu"}),
        ],
    )
    def test_make_simple_field(self, field_key, words, expected):
        """Test creation of simple dictionary with value equal to
        words joined into a sentence-like string.
        """
        result = parsers.GenBankParser(None).make_simple_field(field_key, words)
        assert result == expected

    @pytest.mark.parametrize(
        "words,expected",
        [
            ([], {}),
            (
                GENBANK_COMMENT_WORDS,
                {parsers.GenBankParser.COMMENT_FIELD: GENBANK_COMMENT_LINE},
            ),
            (
                GENBANK_SUMMARY_WORDS,
                {parsers.GenBankParser.SUMMARY_FIELD: GENBANK_SUMMARY_CONTENTS},
            ),
            (
                GENBANK_COMMENT_WORDS + GENBANK_SUMMARY_WORDS,
                {
                    parsers.GenBankParser.COMMENT_FIELD: GENBANK_COMMENT_LINE,
                    parsers.GenBankParser.SUMMARY_FIELD: GENBANK_SUMMARY_CONTENTS,
                },
            ),
        ],
    )
    def test_parse_comment_section(self, words, expected):
        """"""
        result = parsers.GenBankParser(None).parse_comment_section(words)
        assert result == expected


def make_uniprot_line(accession="P10000", database="PDB", database_id="foo"):
    """Create an example line for a UniProt DAT file based on given
    kwargs.
    """
    return "\t".join([accession, database, database_id])


class TestUniProDATParser:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("", ("", "", "")),
            ("\t".join(["P10000", "foo", "bar"]), ("P10000", "foo", "bar")),
            ("\t".join(["P10000-2", "foo", "bar"]), ("P10000", "foo", "bar")),
        ],
    )
    def test_get_line_values(self, line, expected):
        """Test conversion of line to values."""
        result = parsers.UniProtDATParser(None).get_line_values(line)
        assert result == expected

    @pytest.mark.parametrize(
        "records,args,expected",
        [
            ({}, ("", "", ""), {}),
            ({}, ("P10000", "foo", ""), {}),
            ({}, ("P10000", "foo", "-"), {}),
            ({}, ("P10000", "foo", "bar"), {"P10000": {"foo": {"bar"}}}),
            (
                {"P20000": {"fu": "bur"}},
                ("P10000", "foo", "bar"),
                {"P20000": {"fu": "bur"}, "P10000": {"foo": {"bar"}}},
            ),
            (
                {"P10000": {"fu": {"bur"}}},
                ("P10000", "foo", "bar"),
                {"P10000": {"fu": {"bur"}, "foo": {"bar"}}},
            ),
            (
                {"P10000": {"foo": {"bar"}}},
                ("P10000", "foo", "bar"),
                {"P10000": {"foo": {"bar"}}},
            ),
        ],
    )
    def test_add_to_record(self, records, args, expected):
        """Test addition of line values (args) to parser.records."""
        parser = parsers.UniProtDATParser(None)
        parser.records = records
        parser.add_to_record(args[0], args[1], args[2])
        assert parser.records == expected

    @pytest.mark.parametrize(
        "accession,record,expected",
        [
            (
                "P10000",
                {"foo": {"bar"}},
                {
                    parsers.UniProtDATParser.UNIPROT_ACCESSION_KEY: ["P10000"],
                    "foo": ["bar"],
                },
            ),
            (
                "P10000",
                {"foo": {"bar"}, "fu": {"bur"}},
                {
                    parsers.UniProtDATParser.UNIPROT_ACCESSION_KEY: ["P10000"],
                    "foo": ["bar"],
                    "fu": ["bur"],
                },
            ),
        ],
    )
    def test_reformat_record(self, accession, record, expected):
        """Test reformatting of record to annotation format."""
        result = parsers.UniProtDATParser(None).reformat_record(accession, record)
        assert result == expected

    @pytest.mark.parametrize(
        "lines,expected",
        [
            ([], []),
            ([""], []),
            (
                [make_uniprot_line(), make_uniprot_line(database="PDE")],
                [
                    {
                        parsers.UniProtDATParser.UNIPROT_ACCESSION_KEY: ["P10000"],
                        "PDB": ["foo"],
                        "PDE": ["foo"],
                    }
                ],
            ),
            (
                [
                    make_uniprot_line(),
                    make_uniprot_line(accession="P20000", database_id="fu"),
                ],
                [
                    {
                        parsers.UniProtDATParser.UNIPROT_ACCESSION_KEY: ["P10000"],
                        "PDB": ["foo"],
                    },
                    {
                        parsers.UniProtDATParser.UNIPROT_ACCESSION_KEY: ["P20000"],
                        "PDB": ["fu"],
                    },
                ],
            ),
        ],
    )
    @mock.patch("cgap_gene_annotation.src.parsers.get_lines")
    def test_get_records(self, mock_get_lines, lines, expected):
        """Test creation of records from a source file.

        Mock get_lines() from source value to return given lines.

        Test relies on helpers tested above.
        """
        mock_get_lines.return_value = lines
        records = parsers.UniProtDATParser(None).get_records()
        assert isinstance(records, GeneratorType)
        records = list(records)
        assert records == expected


class TestXMLParser:

    TEST_XML_STRING = (
        '<?xml version="1.0"?>'
        "<data>"
        "<people>"
        "<body>"
        "<tissues>"
        '<tissue type="blood">'
        "<cell>RBC</cell>"
        "<cell>WBC</cell>"
        "</tissue>"
        '<tissue type="brain">'
        "<cell>Neuron</cell>"
        "<cell>Astrocyte</cell>"
        "</tissue>"
        "</tissues>"
        "<limbs>"
        "<arm>Left arm</arm>"
        "<arm>Right arm</arm>"
        "<leg>Left leg</leg>"
        "<leg>Right leg</leg>"
        "</limbs>"
        "</body>"
        "</people>"
        "</data>"
    )

    class Element(ET.Element):
        """"""

        def __init__(self, tag, text=None, attrib={}, **extra):
            super().__init__(tag, attrib, **extra)
            if text:
                self.text = text

    @pytest.mark.parametrize(
        "record_path,expected",
        [
            ("", []),
            ("foo", [("foo", None)]),
            ("foo[@name=bar]", [("foo", {"name": "bar"})]),
            ("foo/bar", [("foo", None), ("bar", None)]),
            (
                "foo[@id=buz]/bar[@name=fu][@id=bur]",
                [("foo", {"id": "buz"}), ("bar", {"name": "fu", "id": "bur"})],
            ),
        ],
    )
    def test_parse_record_path(self, record_path, expected):
        """"""
        parser = parsers.XMLParser(None)
        result = parser.parse_record_path(record_path)
        assert result == expected

    @pytest.mark.parametrize(
        "record_path,path,expected",
        [
            ("", [], False),
            ("foo", [], False),
            ("foo", [Element("bar")], False),
            ("foo", [Element("foo")], True),
            ("foo/bar", [Element("foo"), None], False),
            ("foo/bar", [Element("foo"), Element("bar")], True),
            ("foo/bar", [Element("foo"), Element("bur")], False),
            ("foo[@name=fu]/bar", [Element("foo"), Element("bar")], False),
            (
                "foo[@name=fu]/bar",
                [Element("foo", attrib={"name": "fu"}), Element("bar")],
                True,
            ),
            (
                "foo[@name=fu]/bar",
                [Element("foo", attrib={"name": "bur"}), Element("bar")],
                False,
            ),
        ],
    )
    def test_is_path_to_record(self, record_path, path, expected):
        """"""
        parser = parsers.XMLParser(None, record_path=record_path)
        result = parser.is_path_to_record(path)
        assert result == expected

    @pytest.mark.parametrize(
        "element,record,children,depth,expected",
        [
            (Element("foo"), {}, None, None, {}),
            (Element("foo", text="bar"), {}, None, None, {"foo": "bar"}),
            (
                Element("foo", text="bar"),
                {"fu": "bur"},
                None,
                None,
                {"fu": "bur", "foo": "bar"},
            ),
            (Element("foo", text="empty"), {}, None, None, {}),
            (
                Element("foo", text="item1;item2"),
                {},
                None,
                None,
                {"foo": ["item1", "item2"]},
            ),
            (
                Element("foo", text="bar"),
                {"foo": "bur"},
                None,
                None,
                {"foo": ["bur", "bar"]},
            ),
            (Element("foo", text="bar"), {}, {("fu", 2)}, 1, {}),
            (
                Element("foo", text="bar"),
                {"fu": "bur"},
                {("fu", 2)},
                1,
                {"foo": {"fu": "bur"}},
            ),
        ],
    )
    def test_add_element_to_record(self, element, record, children, depth, expected):
        """"""
        list_identifier = ";"
        empty_fields = ["empty"]
        parser = parsers.XMLParser(
            None, list_identifier=list_identifier, empty_fields=empty_fields
        )
        parser.add_element_to_record(element, record, children=children, depth=depth)
        assert record == expected

    @pytest.mark.parametrize(
        "children,depth,expected",
        [
            (set(), 1, set()),
            ({("foo", 2)}, 2, {("foo", 2)}),
            ({("foo", 2)}, 1, set()),
            ({("foo", 2), ("bar", 1)}, 1, {("bar", 1)}),
        ],
    )
    def test_clear_children(self, children, depth, expected):
        """"""
        parser = parsers.XMLParser(None)
        parser.clear_children(children, depth)
        assert children == expected

    @pytest.mark.parametrize(
        "record_path,expected",
        [
            ("foo", []),
            (
                "people/body/tissues/tissue",
                [{"cell": ["RBC", "WBC"]}, {"cell": ["Neuron", "Astrocyte"]}],
            ),
            ("people/body/tissues/tissue[@type=blood]", [{"cell": ["RBC", "WBC"]}]),
            (
                "people/body/tissues/tissue[@type=blood]/cell",
                [{"cell": "RBC"}, {"cell": "WBC"}],
            ),
            ("people/body/limbs/arm", [{"arm": "Left arm"}, {"arm": "Right arm"}]),
            (
                "people/body/limbs",
                [{"arm": ["Left arm", "Right arm"], "leg": ["Left leg", "Right leg"]}],
            ),
        ],
    )
    def test_get_records(self, record_path, expected):
        """"""
        with mock.patch(
            "cgap_gene_annotation.src.utils.open",
            mock.mock_open(read_data=self.TEST_XML_STRING),
        ):
            parser = parsers.XMLParser("", record_path=record_path)
            records = list(parser.get_records())
            assert records == expected
