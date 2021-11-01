import pytest

from ..annotations import SourceAnnotation

TEST_ANNOTATION_RECORD = {"field_1": "value_1", "field_2": ["value_2", "value_3"]}


@pytest.fixture
def empty_annotation_source():
    """"""
    return SourceAnnotation(None)

def record():
    return {"field_1": "value_1", "field_2": ["value_2", "value_3"]}

def simple_parser(records):
    """"""
    class SimpleParser:
        def __init__(self, records):
            self.records = records

        def get_records(self):
            for record in self.records:
                yield record

    return SimpleParser(records)


class TestSourceAnnotation:

    @pytest.mark.parametrize(
        "filter_fields,expected",
        [
            ({}, record()),
            ({"field_1": ["value_1"]}, record()),
            ({"field_1": ["bar"]}, None),
            ({"field_2": ["value_2"]}, record()),
            ({"field_2": ["bar"]}, None),
            ({"field_1": ["value_1"], "field_2": ["bar"]}, None),
        ]
    )
    def test_filter_record(
        self, filter_fields, expected, empty_annotation_source
    ):
        """"""
        assert empty_annotation_source.filter_record(record(), filter_fields) == expected
        
    @pytest.mark.parametrize(
        "fields_to_keep,expected",
        [
            ([], {}),
            (["field_1"], {"field_1": "value_1"}),
            (["field_2"], {"field_2": ["value_2", "value_3"]}),
            (["field_1", "field_2"], record()),
        ]
    )
    def test_retain_fields(self, fields_to_keep, expected, empty_annotation_source):
        """"""
        assert empty_annotation_source.retain_fields(record(), fields_to_keep) == expected

    @pytest.mark.parametrize(
        "fields_to_drop,expected",
        [
            ([], record()),
            (["field_1"], {"field_2": ["value_2", "value_3"]}),
            (["field_2"], {"field_1": "value_1"}),
            (["field_1", "field_2"], {}),
        ]
    )
    def test_remove_fields(self, fields_to_drop, expected, empty_annotation_source):
        """"""
        assert empty_annotation_source.remove_fields(record(), fields_to_drop) == expected

    @pytest.mark.parametrize(
        "records,filter_fields,fields_to_keep,fields_to_drop,expected",
        [
            ([], None, None, None, []),
            ([record()], None, None, None, [record()]),
            ([record()], {"field_1": ["value_1"]}, None, None, [record()]),
            ([record()], {"field_1": ["bar"]}, None, None, []),
            ([record()], None, ["field_1", "field_2"], None, [record()]),
            ([record()], None, ["foo"], None, []),
            ([record()], None, None, ["field_1", "field_2"], []),
            ([record()], None, ["field_1", "field_2"], ["field_1"], [record()]),
        ]
    )
    def test_make_annotation(
        self, records, filter_fields, fields_to_keep, fields_to_drop, expected,
    ):
        """"""
        annotation_source = SourceAnnotation(
            simple_parser(records),
            filter_fields=filter_fields,
            fields_to_keep=fields_to_keep,
            fields_to_drop=fields_to_drop,
        )
        assert annotation_source.make_annotation() == expected


class TestGeneAnnotation:
    pass
