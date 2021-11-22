import io
from types import GeneratorType
from unittest import mock

import pytest

from .. import parsers


@pytest.mark.parametrize(
    "file_contents",
    [
        "",
        "foo\nbar\n",
        "foobar\n\n",
    ]
)
def test_get_lines(file_contents):
    """"""
    file_path = "foo/bar"
    mock_file = io.StringIO(file_contents)
    with mock.patch(
        "cgap_gene_annotation.src.parsers.open_file", return_value=[mock_file],
        create=True
    ) as mocked_file:
        result = parsers.get_lines(file_path)
        assert isinstance(result, GeneratorType)
        result = list(result)
        assert result == file_contents.split("\n")[:-1]
        mocked_file.assert_called_once_with(file_path)


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
        """"""
        parser = parsers.TSVParser(None, empty_fields=empty_fields)
        parser.remove_empty_fields(record)
        assert record == expected

    @pytest.mark.parametrize(
        "entry,comment_characters,expected",
        [
            ("\t".join(["foo", "bar"]), None, ["foo", "bar"]),
            ("\t".join([" foo", "bar "]), None, ["foo", "bar"]),
            ("\t".join(["foo", "bar"]), "#", ["foo", "bar"]),
            ("\t".join(["#foo", "bar"]), "#", ["foo", "bar"]),
            ("\t".join(["# foo", "bar"]), "#", ["foo", "bar"]),
            ("\t".join(["#", "foo", "bar"]), "#", ["foo", "bar"]),
        ],
    )
    def test_parse_header(self, entry, comment_characters, expected):
        """"""
        parser = parsers.TSVParser(None, comment_characters=comment_characters)
        assert parser.parse_header(entry) == expected

    @pytest.mark.parametrize(
        "entry,header,strip_characters,list_identifier,expected",
        [
            ("", ["fu", "bur"], None, None, {}),
            (
                "\t".join(["foo", "bar"]),
                ["fu", "bur"],
                None,
                None,
                {"fu": "foo", "bur": "bar"},
            ),
            (
                "\t".join(["foo", "bar"]),
                ["fu", "bur"],
                " '",
                None,
                {"fu": "foo", "bur": "bar"},
            ),
            (
                "\t".join(["foo ", "'bar'"]),
                ["fu", "bur"],
                " '",
                None,
                {"fu": "foo", "bur": "bar"},
            ),
            (
                "\t".join(["foo", "bar"]),
                ["fu", "bur"],
                None,
                "|",
                {"fu": "foo", "bur": "bar"},
            ),
            (
                "\t".join(["foo", "bar|bor"]),
                ["fu", "bur"],
                None,
                "|",
                {"fu": "foo", "bur": ["bar", "bor"]},
            ),
            (
                "\t".join(["foo", "'bar|bor'"]),
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
        """"""
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
            (["\t".join(["foo", "bar"])], None, None, [], ["foo", "bar"]),
            (
                ["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"])],
                None,
                None,
                [{"foo": "fu", "bar": "bur"}],
                ["foo", "bar"],
            ),
            (
                ["\t".join(["#foo", "bar"]), "\t".join(["fu", "bur"])],
                None,
                None,
                [],
                ["fu", "bur"],
            ),
            (
                ["\t".join(["#foo", "bar"]), "\t".join(["fu", "bur"])],
                0,
                None,
                [{"foo": "fu", "bar": "bur"}],
                ["foo", "bar"],
            ),
            (
                ["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"])],
                None,
                ["baz", "qux"],
                [{"baz": "foo", "qux": "bar"}, {"baz": "fu", "qux": "bur"}],
                ["baz", "qux"],
            ),
            (
                ["\t".join(["#foo", "bar"]), "\t".join(["fu", "bur"])],
                None,
                ["baz", "qux"],
                [{"baz": "fu", "qux": "bur"}],
                ["baz", "qux"],
            ),
            (
                ["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"])],
                0,
                ["baz", "qux"],
                [{"baz": "foo", "qux": "bar"}, {"baz": "fu", "qux": "bur"}],
                ["baz", "qux"],
            ),
            (
                ["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"]), ""],
                None,
                None,
                [{"foo": "fu", "bar": "bur"}],
                ["foo", "bar"],
            ),
        ],
    )
    @mock.patch("cgap_gene_annotation.src.parsers.get_lines")
    def test_get_records(
        self,
        mock_get_lines,
        lines,
        header_line,
        header,
        expected_records,
        expected_header,
    ):
        """"""
        mock_get_lines.return_value = lines
        parser = parsers.TSVParser(None, header_line=header_line, header=header)
        records = parser.get_records()
        assert isinstance(records, GeneratorType)
        records = list(records)
        assert records == expected_records
        assert parser.header == expected_header


class TestCSVParser:
    @pytest.mark.parametrize(
        "lines,header_line,header,expected_records,expected_header",
        [
            ([], None, None, [], None),
            ([",".join(["foo", "bar"])], None, None, [], ["foo", "bar"]),
            (
                [",".join(["foo", "bar"]), ",".join(["fu", "bur"])],
                None,
                None,
                [{"foo": "fu", "bar": "bur"}],
                ["foo", "bar"],
            ),
        ],
    )
    @mock.patch("cgap_gene_annotation.src.parsers.get_lines")
    def test_get_records(
        self,
        mock_get_lines,
        lines,
        header_line,
        header,
        expected_records,
        expected_header,
    ):
        """"""
        mock_get_lines.return_value = lines
        parser = parsers.CSVParser(None, header_line=header_line, header=header)
        records = parser.get_records()
        assert isinstance(records, GeneratorType)
        records = list(records)
        assert records == expected_records
        assert parser.header == expected_header


class TestGTFParser:
    @pytest.mark.parametrize(
        "entry,expected",
        [
            ("", {}),
            (
                "\t".join(
                    ["chrom", "foo", "gene", "1", "200", ".", "+", ".", 'fu "bar"']
                ),
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
                "\t".join(
                    [
                        "1",
                        "havana",
                        "gene",
                        "11869",
                        "14409",
                        ".",
                        "+",
                        ".",
                        'gene_id "ENSG00000223972"; gene_version "5"; gene_name "DDX11L1"; gene_source "havana"; gene_biotype "transcribed_unprocessed_pseudogene";',
                    ]
                ),
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
        """"""
        result = parsers.GTFParser(None).parse_entry(entry)
        assert result == expected


def make_uniprot_line(accession="P10000", database="PDB", database_id="foo"):
    """"""
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
        """"""
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
        """"""
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
        """"""
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
        """"""
        mock_get_lines.return_value = lines
        records = parsers.UniProtDATParser(None).get_records()
        assert isinstance(records, GeneratorType)
        records = list(records)
        assert records == expected
