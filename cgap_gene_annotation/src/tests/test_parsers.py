import pytest

from types import GeneratorType
from unittest import mock

from ..parsers import get_lines, TSVParser, CSVParser, GenBankParser, UniProtDATParser


def test_get_lines():
    """"""
    pass


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
        ]
    )
    def test_remove_empty_fields(self, record, empty_fields, expected):
        """"""
        parser = TSVParser(None, empty_fields=empty_fields)
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
        ]
    )
    def test_parse_header(self, entry, comment_characters, expected):
        """"""
        parser = TSVParser(None, comment_characters=comment_characters)
        assert parser.parse_header(entry) == expected

    @pytest.mark.parametrize(
        "entry,header,strip_characters,list_identifier,expected",
        [
            ("", ["fu", "bur"], None, None, {}),
            ("\t".join(["foo", "bar"]), ["fu", "bur"], None, None, {"fu": "foo", "bur": "bar"}),
            ("\t".join(["foo", "bar"]), ["fu", "bur"], " '", None, {"fu": "foo", "bur": "bar"}),
            ("\t".join(["foo ", "'bar'"]), ["fu", "bur"], " '", None, {"fu": "foo", "bur": "bar"}),
            ("\t".join(["foo", "bar"]), ["fu", "bur"], None, "|", {"fu": "foo", "bur": "bar"}),
            ("\t".join(["foo", "bar|bor"]), ["fu", "bur"], None, "|", {"fu": "foo", "bur": ["bar", "bor"]}),
            ("\t".join(["foo", "'bar|bor'"]), ["fu", "bur"], " '", "|", {"fu": "foo", "bur": ["bar", "bor"]}),
        ]
    )
    def test_parse_entry(
        self, entry, header, strip_characters, list_identifier, expected
    ):
        """"""
        parser = TSVParser(
            None, header=header, strip_characters=strip_characters, list_identifier=list_identifier
        )
        assert parser.parse_entry(entry) == expected

    @pytest.mark.parametrize(
        "lines,header_line,header,expected_records,expected_header",
        [
            ([], None, None, [], None), 
            (["\t".join(["foo", "bar"])], None, None, [], ["foo", "bar"]),
            (["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"])], None, None, [{"foo": "fu", "bar": "bur"}], ["foo", "bar"]),
            (["\t".join(["#foo", "bar"]), "\t".join(["fu", "bur"])], None, None, [], ["fu", "bur"]),
            (["\t".join(["#foo", "bar"]), "\t".join(["fu", "bur"])], 0, None, [{"foo": "fu", "bar": "bur"}], ["foo", "bar"]),
            (["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"])], None, ["baz", "qux"], [{"baz": "foo", "qux": "bar"}, {"baz": "fu", "qux": "bur"}], ["baz", "qux"]),
            (["\t".join(["#foo", "bar"]), "\t".join(["fu", "bur"])], None, ["baz", "qux"], [{"baz": "fu", "qux": "bur"}], ["baz", "qux"]),
            (["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"])], 0, ["baz", "qux"], [{"baz": "foo", "qux": "bar"}, {"baz": "fu", "qux": "bur"}], ["baz", "qux"]),
            (["\t".join(["foo", "bar"]), "\t".join(["fu", "bur"]), ""], None, None, [{"foo": "fu", "bar": "bur"}], ["foo", "bar"]),
        ]
    )
    @mock.patch("cgap_gene_annotation.src.parsers.get_lines")
    def test_get_records(
        self, mock_get_lines, lines, header_line, header, expected_records, expected_header
    ):
        """"""
        mock_get_lines.return_value = lines
        parser = TSVParser(None, header_line=header_line, header=header)
        records = parser.get_records()
        assert isinstance(records, GeneratorType)
        records = [x for x in records]
        assert records == expected_records
        assert parser.header == expected_header
