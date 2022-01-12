import json
import tempfile
from copy import deepcopy
from unittest import mock

import jsonschema
import pytest

from .. import constants
from ..annotations import GeneAnnotation, JSONInputError, SourceAnnotation

ANNOTATION_RECORD = {"field_1": "value_1", "field_2": ["value_2", "value_3"]}
PREFIX_1 = "Prefix_1"
PREFIX_2 = "Prefix_2"
ANNOTATION_METADATA_1 = {
    constants.FILES: ["foo/bar"],
    constants.PARSER: {
        constants.PARSER_CHOICE: list(constants.PARSERS_AVAILABLE.keys())[0]
    },
    constants.PREFIX: PREFIX_1,
    constants.SOURCE: True,
}
ANNOTATION_METADATA_2 = {
    constants.FILES: ["fu/bur"],
    constants.PARSER: {
        constants.PARSER_CHOICE: list(constants.PARSERS_AVAILABLE.keys())[0]
    },
    constants.PREFIX: PREFIX_2,
}
CREATE_JSON_VALID = [ANNOTATION_METADATA_1, ANNOTATION_METADATA_2]
CREATE_JSON_INVALID = [
    {  # Missing required fields, invalid type, & additional property
        constants.FILES: "foo/bar",
        constants.PARSER: {"foo": "bar"},
    }
]
UPDATE_JSON_VALID = {
    constants.ADD: CREATE_JSON_VALID,
    constants.REPLACE: CREATE_JSON_VALID,
    constants.REMOVE: [PREFIX_1, PREFIX_2],
}
UPDATE_JSON_INVALID = {
    constants.ADD: CREATE_JSON_INVALID,
    constants.REPLACE: CREATE_JSON_INVALID,
    constants.REMOVE: [{"foo": "bar"}],
}
FILE_PATH = "dir/file"
METADATA = {
    PREFIX_1: {
        "foo": "bar",
        "fu": "bur",
    },
    PREFIX_2: {"something": "else"},
}
ANNOTATIONS = [
    {PREFIX_1: [{"a": "b"}], PREFIX_2: ["c"]},
    {
        PREFIX_1: [{"d": "e"}],
    },
]
ANNOTATION_FILE_CONTENTS = {
    constants.METADATA: METADATA,
    constants.ANNOTATION: ANNOTATIONS,
}
ANNOTATIONS_TO_ADD = [
    {"foo": "bar"},
    {"fu": "bur"},
]


@pytest.fixture
def empty_annotation_source():
    """Empty class for tests."""
    return SourceAnnotation(None)


def record():
    """Record for testing.

    Not a fixture so can be used within parametrize call, and a
    deepcopy to prevent change of original.
    """
    return deepcopy(ANNOTATION_RECORD)


def simple_parser(records):
    """A parser with expected method name to return given records."""

    class SimpleParser:
        def __init__(self, records):
            self.records = records

        def get_records(self):
            for record in self.records:
                yield record

    return SimpleParser(records)


@pytest.fixture
def empty_gene_annotation():
    """Empty class for tests."""
    return GeneAnnotation(None)


@pytest.fixture
def basic_gene_annotation():
    """GeneAnnotation with a file path, metadata, and annotations."""
    gene_annotation = GeneAnnotation(FILE_PATH)
    gene_annotation.metadata = deepcopy(METADATA)
    gene_annotation.annotations = deepcopy(ANNOTATIONS)
    return gene_annotation


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
        ],
    )
    def test_filter_record(self, filter_fields, expected, empty_annotation_source):
        """Test entire record dropped or maintained when filtered by
        given filter_fields.
        """
        assert (
            empty_annotation_source.filter_record(record(), filter_fields) == expected
        )

    @pytest.mark.parametrize(
        "fields_to_keep,expected",
        [
            ([], {}),
            (["field_1"], {"field_1": "value_1"}),
            (["field_2"], {"field_2": ["value_2", "value_3"]}),
            (["field_1", "field_2"], record()),
        ],
    )
    def test_retain_fields(self, fields_to_keep, expected, empty_annotation_source):
        """Test fields kept in record only if in given fields_to_keep
        and in record.
        """
        assert (
            empty_annotation_source.retain_fields(record(), fields_to_keep) == expected
        )

    @pytest.mark.parametrize(
        "fields_to_drop,expected",
        [
            ([], record()),
            (["field_1"], {"field_2": ["value_2", "value_3"]}),
            (["field_2"], {"field_1": "value_1"}),
            (["field_1", "field_2"], {}),
        ],
    )
    def test_remove_fields(self, fields_to_drop, expected, empty_annotation_source):
        """Test fields dropped from record if in record and in given
        fields_to_drop.
        """
        assert (
            empty_annotation_source.remove_fields(record(), fields_to_drop) == expected
        )

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
        ],
    )
    def test_make_annotation(
        self,
        records,
        filter_fields,
        fields_to_keep,
        fields_to_drop,
        expected,
    ):
        """Test annotations created correctly from given records
        according to given parameters.

        Relies upon correct functioning of methods tested above.
        """
        annotation_source = SourceAnnotation(
            simple_parser(records),
            filter_fields=filter_fields,
            fields_to_keep=fields_to_keep,
            fields_to_drop=fields_to_drop,
        )
        assert annotation_source.make_annotation() == expected


class TestGeneAnnotation:
    @pytest.mark.parametrize(
        "json_input,raise_error",
        [
            ({"foo": "bar"}, False),
            ({"bar": "foo"}, True),
        ],
    )
    def test_validate_json(self, json_input, raise_error, empty_gene_annotation):
        """Test validation of input against fixed schema below, with
        errors raised appropriately if expected.
        """
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"foo": {"type": "string"}},
        }
        validator = jsonschema.Draft4Validator(schema)
        if raise_error:
            with pytest.raises(JSONInputError):
                empty_gene_annotation.validate_json(validator, json_input)
        else:
            empty_gene_annotation.validate_json(validator, json_input)

    @pytest.mark.parametrize(
        "json_input,raise_error",
        [
            ([], False),
            (CREATE_JSON_VALID, False),
            (CREATE_JSON_INVALID, True),
            ({}, True),
            (None, True),
        ],
    )
    def test_validate_create_json(self, json_input, raise_error, empty_gene_annotation):
        """Test validation of input against schemas.CREATE_SCHEMA,
        with errors raised if expected.
        """
        if raise_error:
            with pytest.raises(JSONInputError):
                empty_gene_annotation.validate_create_json(json_input)
        else:
            empty_gene_annotation.validate_create_json(json_input)

    @pytest.mark.parametrize(
        "json_input,raise_error",
        [
            ({}, False),
            (UPDATE_JSON_VALID, False),
            (UPDATE_JSON_INVALID, True),
            ([], True),
            (None, True),
        ],
    )
    def test_validate_update_json(self, json_input, raise_error, empty_gene_annotation):
        """Test validation of input against schemas.UPDATE_SCHEMA,
        with errors raised if expected.
        """
        if raise_error:
            with pytest.raises(JSONInputError):
                empty_gene_annotation.validate_update_json(json_input)
        else:
            empty_gene_annotation.validate_update_json(json_input)

    @pytest.mark.parametrize(
        "file_contents,expected_metadata,expected_annotations",
        [
            ({}, {}, []),
            ({constants.METADATA: METADATA}, METADATA, []),
            ({constants.ANNOTATION: ANNOTATIONS}, {}, ANNOTATIONS),
            (
                {constants.METADATA: METADATA, constants.ANNOTATION: ANNOTATIONS},
                METADATA,
                ANNOTATIONS,
            ),
        ],
    )
    def test_parse_file(
        self,
        file_contents,
        expected_metadata,
        expected_annotations,
        empty_gene_annotation,
    ):
        """Test parsing of existing annotation file.

        Mock out open_file() and json.load() to return given test data.
        """
        file_handle = "foo bar"
        open_file_value = (n for n in [file_handle])
        with mock.patch(
            "cgap_gene_annotation.src.annotations.FileHandler.get_handle",
            return_value=open_file_value,
        ) as mock_open_file:
            with mock.patch(
                "cgap_gene_annotation.src.annotations.json.load",
                return_value=file_contents,
            ) as mock_json_load:
                empty_gene_annotation.parse_file()
                mock_open_file.assert_called_once_with(None, binary=True)
                mock_json_load.assert_called_once_with(file_handle)
                assert empty_gene_annotation.metadata == expected_metadata
                assert empty_gene_annotation.annotations == expected_annotations

    def test_create_parser(self, empty_gene_annotation):
        """Test creation of all parsers available.

        For TSVParser, pass a parameter and ensure created parser
        took parameter into account.
        """
        tsv_header = ["foo", "bar"]
        for key, value in constants.PARSERS_AVAILABLE.items():
            parameters = {}
            if key == "TSV":
                parameters = {"header": tsv_header}
            parser_metadata = {
                constants.PARSER_CHOICE: key,
                constants.PARAMETERS: parameters,
            }
            parser = empty_gene_annotation.create_parser(FILE_PATH, parser_metadata)
            assert parser.file_path == FILE_PATH
            assert type(parser) == value
            if key == "TSV":
                assert parser.header == tsv_header

    def test_write_file(self, basic_gene_annotation):
        """Test write of metadata and annotations from a GeneAnnotation
        class to a temp file.
        """
        with tempfile.NamedTemporaryFile() as tmp:
            basic_gene_annotation.file_path = tmp.name
            basic_gene_annotation.write_file()
            assert json.load(tmp) == ANNOTATION_FILE_CONTENTS

    @pytest.mark.parametrize("identifier", [PREFIX_1, PREFIX_2, "foo"])
    def test_remove_identifier(self, identifier, basic_gene_annotation):
        """Test removal of given identifier from class' annotations
        and metadata dictionaries.
        """
        basic_gene_annotation.remove_identifier(identifier)
        assert identifier not in basic_gene_annotation.annotations
        assert identifier not in basic_gene_annotation.metadata

    @pytest.mark.parametrize(
        "prefix_list",
        [
            [""],
            [PREFIX_1],
            [PREFIX_2],
            [PREFIX_1, PREFIX_2],
        ],
    )
    def test_remove_annotations(self, prefix_list, basic_gene_annotation):
        """Test retrieval of given prefixes from metadata and
        subsequent removal from class metadata and annotations.
        """
        annotation_metadata = [{constants.PREFIX: prefix} for prefix in prefix_list]
        basic_gene_annotation.remove_annotations(annotation_metadata)
        for prefix in prefix_list:
            assert prefix not in basic_gene_annotation.metadata
            for annotation in basic_gene_annotation.annotations:
                assert prefix not in annotation

    def mocked_source_annotation(self, annotations_to_add):
        """Create a mock SourceAnnotation to return the given
        annotations_to_add.
        """
        make_annotations = mock.Mock()
        make_annotations.return_value = annotations_to_add
        source_annotation = mock.Mock()
        source_annotation.return_value.make_annotation = make_annotations
        return source_annotation

    @pytest.mark.parametrize(
        "annotation_metadata,annotations_to_add",
        [
            (ANNOTATION_METADATA_1, []),
            (ANNOTATION_METADATA_1, ANNOTATIONS_TO_ADD),
            (ANNOTATION_METADATA_2, []),
            (ANNOTATION_METADATA_2, ANNOTATIONS_TO_ADD),
        ],
    )
    def test_add_source(
        self, annotation_metadata, annotations_to_add, empty_gene_annotation
    ):
        """Test addition of annotations to a GeneAnnotation class.

        Mock SourceAnnotation and AnnotationMerge classes and ensure
        appropriate calls but not functionality.
        """
        prefix = annotation_metadata.get(constants.PREFIX)
        base_annotation = annotation_metadata.get(constants.SOURCE)
        with mock.patch(
            "cgap_gene_annotation.src.annotations.SourceAnnotation",
            new=self.mocked_source_annotation(annotations_to_add),
        ) as mock_source_annotation:
            with mock.patch(
                "cgap_gene_annotation.src.annotations.AnnotationMerge"
            ) as mock_merge:
                empty_gene_annotation.add_source(annotation_metadata)
                mock_source_annotation.assert_called_once()
                mock_source_annotation().make_annotation.assert_called_once_with()
                if base_annotation is True:
                    expected = [
                        {prefix: [annotation]} for annotation in annotations_to_add
                    ]
                    assert empty_gene_annotation.annotations == expected
                elif annotations_to_add:
                    mock_merge.assert_called_once()
                    mock_merge().merge_annotations.assert_called_once_with()
                else:
                    mock_merge.assert_not_called()

    @mock.patch("cgap_gene_annotation.src.annotations.GeneAnnotation.add_source")
    @mock.patch("cgap_gene_annotation.src.annotations.GeneAnnotation.remove_identifier")
    def test_replace_annotations(
        self, mock_remove_identifier, mock_add_source, basic_gene_annotation
    ):
        """Test replacement of existing annotations.

        Mock methods and ensure calls only.
        """
        annotation_metadata = CREATE_JSON_VALID
        basic_gene_annotation.replace_annotations(annotation_metadata)
        assert mock_remove_identifier.call_count == 2
        mock_remove_identifier.assert_any_call(PREFIX_1)
        mock_remove_identifier.assert_any_call(PREFIX_2)
        assert mock_add_source.call_count == 2
        mock_add_source.assert_any_call(ANNOTATION_METADATA_1)
        mock_add_source.assert_any_call(ANNOTATION_METADATA_2)

    @mock.patch("cgap_gene_annotation.src.annotations.GeneAnnotation.add_source")
    def test_add_annotations(self, mock_add_source, basic_gene_annotation):
        """Test addition of new annotations.

        Mock method and ensure calls only.
        """
        annotation_metadata = CREATE_JSON_VALID
        basic_gene_annotation.add_annotations(annotation_metadata)
        assert mock_add_source.call_count == 2
        mock_add_source.assert_any_call(ANNOTATION_METADATA_1)
        mock_add_source.assert_any_call(ANNOTATION_METADATA_2)

    @mock.patch("cgap_gene_annotation.src.annotations.GeneAnnotation.add_annotations")
    @pytest.mark.parametrize(
        "json_input,raise_error",
        [
            (CREATE_JSON_VALID, False),
            (CREATE_JSON_INVALID, True),
        ],
    )
    def test_create_annotation(
        self, mock_add_annotations, json_input, raise_error, empty_gene_annotation
    ):
        """Test new annotation creation, including validation of input.

        Mock method and ensure calls if no error expected.
        """
        if not raise_error:
            empty_gene_annotation.create_annotation(json_input)
            mock_add_annotations.assert_called_once_with(json_input)
        else:
            with pytest.raises(JSONInputError):
                empty_gene_annotation.create_annotation(json_input)
                mock_add_annotations.assert_not_called()

    @mock.patch("cgap_gene_annotation.src.annotations.GeneAnnotation.parse_file")
    @mock.patch(
        "cgap_gene_annotation.src.annotations.GeneAnnotation.remove_annotations"
    )
    @mock.patch(
        "cgap_gene_annotation.src.annotations.GeneAnnotation.replace_annotations"
    )
    @mock.patch("cgap_gene_annotation.src.annotations.GeneAnnotation.add_annotations")
    @pytest.mark.parametrize(
        "json_input,raise_error",
        [
            (UPDATE_JSON_VALID, False),
            (UPDATE_JSON_INVALID, True),
        ],
    )
    def test_update_annotation(
        self,
        mock_add_annotations,
        mock_replace_annotations,
        mock_remove_annotations,
        mock_parse_file,
        json_input,
        raise_error,
        empty_gene_annotation,
    ):
        """Test update of existing annotation, including schema
        validation.

        Mock methods and ensure calls if no error expected.
        """
        if not raise_error:
            empty_gene_annotation.update_annotation(json_input)
            mock_parse_file.assert_called_once_with()
            mock_remove_annotations.assert_called_once()
            mock_replace_annotations.assert_called_once()
            mock_add_annotations.assert_called_once()
        else:
            with pytest.raises(JSONInputError):
                empty_gene_annotation.update_annotation(json_input)
                mock_parse_file.assert_not_called()
                mock_remove_annotations.assert_not_called()
                mock_replace_annotations.assert_not_called()
                mock_add_annotations.assert_not_called()
