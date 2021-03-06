from copy import deepcopy

import pytest

from .. import constants
from ..merge import AnnotationMerge

EXISTING_ANNOTATION = [
    {"foo": "bar"},
    {"foo": {"bar": "one"}},
    {"foo": {"bar": "two"}},
    {"foo": {"bar": "three"}, "waldo": "fred"},
    {"foo": {"bar": "three"}},
    {"foo": {"bar": ["three", "four"]}},
    {"foo": {"bar": "five"}},
    {"foo": "bar", "fi": "one"},
]
NEW_ANNOTATION = [
    {"bur": "zero"},
    {"fu": {"bur": "one"}},
    {"fu": {"bur": ["one", "two"]}},
    {"fu": {"bur": "three"}, "thud": "fred"},
    {"fu": {"bur": "four"}},
    {"fu": {"bur": "five"}},
]
NEW_PREFIX = "Test"
PRIMARY_MERGE_FIELDS = (["foo.bar", "fi"], "fu.bur")
SECONDARY_MERGE_FIELDS = ("waldo", "thud")
MERGED_PRIMARY_FIELDS_MANY_TO_MANY = [
    EXISTING_ANNOTATION[0],
    {**EXISTING_ANNOTATION[1], **{NEW_PREFIX: [NEW_ANNOTATION[1], NEW_ANNOTATION[2]]}},
    {**EXISTING_ANNOTATION[2], **{NEW_PREFIX: [NEW_ANNOTATION[2]]}},
    {**EXISTING_ANNOTATION[3], **{NEW_PREFIX: [NEW_ANNOTATION[3]]}},
    {**EXISTING_ANNOTATION[4], **{NEW_PREFIX: [NEW_ANNOTATION[3]]}},
    {**EXISTING_ANNOTATION[5], **{NEW_PREFIX: [NEW_ANNOTATION[3], NEW_ANNOTATION[4]]}},
    {**EXISTING_ANNOTATION[6], **{NEW_PREFIX: [NEW_ANNOTATION[5]]}},
    {**EXISTING_ANNOTATION[7], **{NEW_PREFIX: [NEW_ANNOTATION[1], NEW_ANNOTATION[2]]}},
]
MERGED_PRIMARY_FIELDS_MANY_TO_ONE = [
    EXISTING_ANNOTATION[0],
    EXISTING_ANNOTATION[1],
    {**EXISTING_ANNOTATION[2], **{NEW_PREFIX: [NEW_ANNOTATION[2]]}},
    {**EXISTING_ANNOTATION[3], **{NEW_PREFIX: [NEW_ANNOTATION[3]]}},
    {**EXISTING_ANNOTATION[4], **{NEW_PREFIX: [NEW_ANNOTATION[3]]}},
    EXISTING_ANNOTATION[5],
    {**EXISTING_ANNOTATION[6], **{NEW_PREFIX: [NEW_ANNOTATION[5]]}},
    EXISTING_ANNOTATION[7],
]
MERGED_PRIMARY_FIELDS_ONE_TO_MANY = [
    EXISTING_ANNOTATION[0],
    EXISTING_ANNOTATION[1],
    EXISTING_ANNOTATION[2],
    EXISTING_ANNOTATION[3],
    EXISTING_ANNOTATION[4],
    {**EXISTING_ANNOTATION[5], **{NEW_PREFIX: [NEW_ANNOTATION[4]]}},
    {**EXISTING_ANNOTATION[6], **{NEW_PREFIX: [NEW_ANNOTATION[5]]}},
    EXISTING_ANNOTATION[7],
]
MERGED_PRIMARY_FIELDS_ONE_TO_ONE = [
    EXISTING_ANNOTATION[0],
    EXISTING_ANNOTATION[1],
    EXISTING_ANNOTATION[2],
    EXISTING_ANNOTATION[3],
    EXISTING_ANNOTATION[4],
    EXISTING_ANNOTATION[5],
    {**EXISTING_ANNOTATION[6], **{NEW_PREFIX: [NEW_ANNOTATION[5]]}},
    EXISTING_ANNOTATION[7],
]
MERGED_PRIMARY_AND_SECONDARY_FIELDS_MANY_TO_MANY = [
    EXISTING_ANNOTATION[0],
    EXISTING_ANNOTATION[1],
    EXISTING_ANNOTATION[2],
    {**EXISTING_ANNOTATION[3], **{NEW_PREFIX: [NEW_ANNOTATION[3]]}},
    EXISTING_ANNOTATION[4],
    EXISTING_ANNOTATION[5],
    EXISTING_ANNOTATION[6],
    EXISTING_ANNOTATION[7],
]
MERGED_PRIMARY_THEN_SECONDARY_FIELDS_ONE_TO_ONE = [
    EXISTING_ANNOTATION[0],
    EXISTING_ANNOTATION[1],
    EXISTING_ANNOTATION[2],
    {**EXISTING_ANNOTATION[3], **{NEW_PREFIX: [NEW_ANNOTATION[3]]}},
    EXISTING_ANNOTATION[4],
    EXISTING_ANNOTATION[5],
    {**EXISTING_ANNOTATION[6], **{NEW_PREFIX: [NEW_ANNOTATION[5]]}},
    EXISTING_ANNOTATION[7],
]


@pytest.fixture
def empty_merge():
    """Empty class for tests."""
    return AnnotationMerge(None, None, None, {})


def existing_annotation():
    """The annotation to merge to.

    Not a fixture to use in parametrize call, and deepcopied to ensure
    identical every time called.
    """
    return deepcopy(EXISTING_ANNOTATION)


@pytest.fixture
def new_annotation():
    """The annotation to merge in.

    Deepcopied to ensure identical every time called.
    """
    return deepcopy(NEW_ANNOTATION)


@pytest.fixture
def merge_info():
    """Simple merge parameters in expected format."""
    return {constants.MERGE_PRIMARY_FIELDS: [PRIMARY_MERGE_FIELDS]}


@pytest.fixture
def basic_merge(new_annotation, merge_info):
    """Class with test loaded in."""
    return AnnotationMerge(
        existing_annotation(), new_annotation, NEW_PREFIX, merge_info
    )


def existing_to_new_primary_edges(remove_fields=None):
    """Expected mapping of existing to new annotations based upon test
    constants EXISTING_ANNOTATION and NEW_ANNOTATION.

    Not a fixture to allow customization and call within paramtrize.
    """
    edges = {1: {1, 2}, 2: {2}, 3: {3}, 4: {3}, 5: {3, 4}, 6: {5}, 7: {1, 2}}
    if remove_fields:
        for field in remove_fields:
            if field in edges:
                del edges[field]
    return edges


def new_to_existing_primary_edges(remove_fields=None):
    """Expected mapping of new to existing annotations based upon test
    constants EXISTING_ANNOTATION and NEW_ANNOTATION.

    Not a fixture to allow customization and call within paramtrize.
    """
    edges = {1: {1, 7}, 2: {1, 2, 7}, 3: {3, 4, 5}, 4: {5}, 5: {6}}
    if remove_fields:
        for field in remove_fields:
            if field in edges:
                del edges[field]
            for value in edges.values():
                if field in value:
                    value.remove(field)
    return edges


class TestAnnotationMerge:
    @pytest.mark.parametrize(
        "merge_info,expected",
        [
            ({}, ([], [], False, False)),
            (
                {
                    constants.MERGE_CHOICE: (
                        constants.MERGE_CHOICE_ONE,
                        constants.MERGE_CHOICE_ONE,
                    )
                },
                ([], [], True, True),
            ),
            (
                {
                    constants.MERGE_CHOICE: (
                        constants.MERGE_CHOICE_ONE,
                        constants.MERGE_CHOICE_MANY,
                    )
                },
                ([], [], False, True),
            ),
            (
                {
                    constants.MERGE_CHOICE: (
                        constants.MERGE_CHOICE_MANY,
                        constants.MERGE_CHOICE_ONE,
                    )
                },
                ([], [], True, False),
            ),
            (
                {
                    constants.MERGE_CHOICE: (
                        constants.MERGE_CHOICE_MANY,
                        constants.MERGE_CHOICE_MANY,
                    )
                },
                ([], [], False, False),
            ),
            (
                {
                    constants.MERGE_PRIMARY_FIELDS: [],
                    constants.MERGE_SECONDARY_FIELDS: [],
                },
                ([], [], False, False),
            ),
            (
                {
                    constants.MERGE_PRIMARY_FIELDS: [("foo.bar", "bar.foo")],
                    constants.MERGE_SECONDARY_FIELDS: [],
                },
                ([("foo.bar", "bar.foo")], [], False, False),
            ),
            (
                {
                    constants.MERGE_PRIMARY_FIELDS: [],
                    constants.MERGE_SECONDARY_FIELDS: [("foo.bar", "bar.foo")],
                },
                ([], [("foo.bar", "bar.foo")], False, False),
            ),
        ],
    )
    def test_parse_merge_info(self, merge_info, expected, empty_merge):
        """Test parsing of given merge information."""
        assert empty_merge.parse_merge_info(merge_info) == expected

    @pytest.mark.parametrize(
        "merge_type_tuple,expected",
        [
            (
                (constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_MANY),
                [False, False],
            ),
            ((constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_ONE), [False, True]),
            ((constants.MERGE_CHOICE_ONE, constants.MERGE_CHOICE_MANY), [True, False]),
            ((constants.MERGE_CHOICE_ONE, constants.MERGE_CHOICE_ONE), [True, True]),
        ],
    )
    def test_convert_merge_type_to_bool(self, merge_type_tuple, expected, empty_merge):
        """Test conversion of merge type constants to boolean values."""
        result = empty_merge.convert_merge_type_to_bool(merge_type_tuple)
        assert result == expected

    @pytest.mark.parametrize(
        "merge_type,primary_merge_fields,secondary_merge_fields,expected_merged_annotations",
        [
            (
                (constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_MANY),
                [],
                [],
                EXISTING_ANNOTATION,
            ),
            (
                (constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_MANY),
                [PRIMARY_MERGE_FIELDS],
                [],
                MERGED_PRIMARY_FIELDS_MANY_TO_MANY,
            ),
            (
                (constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_ONE),
                [PRIMARY_MERGE_FIELDS],
                [],
                MERGED_PRIMARY_FIELDS_MANY_TO_ONE,
            ),
            (
                (constants.MERGE_CHOICE_ONE, constants.MERGE_CHOICE_MANY),
                [PRIMARY_MERGE_FIELDS],
                [],
                MERGED_PRIMARY_FIELDS_ONE_TO_MANY,
            ),
            (
                (constants.MERGE_CHOICE_ONE, constants.MERGE_CHOICE_ONE),
                [PRIMARY_MERGE_FIELDS],
                [],
                MERGED_PRIMARY_FIELDS_ONE_TO_ONE,
            ),
            (
                (constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_MANY),
                [PRIMARY_MERGE_FIELDS, SECONDARY_MERGE_FIELDS],
                [],
                MERGED_PRIMARY_AND_SECONDARY_FIELDS_MANY_TO_MANY,
            ),
            (
                (constants.MERGE_CHOICE_ONE, constants.MERGE_CHOICE_ONE),
                [PRIMARY_MERGE_FIELDS],
                [SECONDARY_MERGE_FIELDS],
                MERGED_PRIMARY_THEN_SECONDARY_FIELDS_ONE_TO_ONE,
            ),
        ],
    )
    def test_merge_annotations(
        self,
        merge_type,
        primary_merge_fields,
        secondary_merge_fields,
        expected_merged_annotations,
        basic_merge,
    ):
        """Test overall merging of annotations given merge parameters.

        As method has many helpers, should only fail when a test of one
        of helper functions also fails.
        """
        merge_info = {
            constants.MERGE_CHOICE: merge_type,
            constants.MERGE_PRIMARY_FIELDS: primary_merge_fields,
            constants.MERGE_SECONDARY_FIELDS: secondary_merge_fields,
        }
        (
            basic_merge.primary_merge_fields,
            basic_merge.secondary_merge_fields,
            basic_merge.existing_to_new_unique,
            basic_merge.new_to_existing_unique,
        ) = basic_merge.parse_merge_info(merge_info)
        basic_merge.merge_annotations()
        assert basic_merge.existing_annotation == expected_merged_annotations

    @pytest.mark.parametrize(
        (
            "merge_fields,existing_to_new_edges,new_to_existing_edges"
            ",expected_existing_to_new_edges,expected_new_to_existing_edges"
        ),
        [
            ([("bar", "bar")], None, None, [{}], [{}]),
            ([("foo.bar", "bar")], None, None, [{}], [{}]),
            ([("bar", "fu.bur")], None, None, [{}], [{}]),
            (
                [("bar", "fu.bur")],
                [{1: {5}}],
                [{5: {1}}],
                [{1: {5}}, {}],
                [{5: {1}}, {}],
            ),
            (
                [PRIMARY_MERGE_FIELDS],
                None,
                None,
                [existing_to_new_primary_edges(None)],
                [new_to_existing_primary_edges(None)],
            ),
            (
                [PRIMARY_MERGE_FIELDS],
                [{1: {5}}],
                [{5: {1}}],
                [{1: {5}}, {}],
                [{5: {1}}, {}],
            ),
            (
                [PRIMARY_MERGE_FIELDS],
                [{6: {1}, 2: {2}}],
                [{5: {3}, 2: {2}}],
                [
                    {6: {1}, 2: {2}},
                    existing_to_new_primary_edges(remove_fields=[1, 3, 4, 5, 7]),
                ],
                [
                    {5: {3}, 2: {2}},
                    new_to_existing_primary_edges(remove_fields=[1, 3, 4, 7]),
                ],
            ),
        ],
    )
    def test_join_annotations(
        self,
        merge_fields,
        existing_to_new_edges,
        new_to_existing_edges,
        expected_existing_to_new_edges,
        expected_new_to_existing_edges,
        basic_merge,
    ):
        """Test creation of matched annotation mappings given the merge
        parameters.
        """
        if existing_to_new_edges:
            basic_merge.existing_to_new_edges = existing_to_new_edges
        if new_to_existing_edges:
            basic_merge.new_to_existing_edges = new_to_existing_edges
        basic_merge.join_annotations(merge_fields)
        assert basic_merge.existing_to_new_edges == expected_existing_to_new_edges
        assert basic_merge.new_to_existing_edges == expected_new_to_existing_edges

    @pytest.mark.parametrize(
        "merge_field_list,expected",
        [
            ([("foo", "bar")], [["foo"], ["bar"]]),
            ([("foo.bar", "bar.foo")], [["foo.bar"], ["bar.foo"]]),
            ([("foo", "bar"), ("bar", "foo")], [["foo"], ["bar"]]),
        ],
    )
    def test_get_merge_fields(self, merge_field_list, expected, empty_merge):
        """Test retrieval of first set of merge fields from the given
        list of merge fields.
        """
        assert empty_merge.get_merge_fields(merge_field_list) == expected

    @pytest.mark.parametrize(
        "annotation,key,indices,expected",
        [
            ([], [], None, {}),
            ([{"foo": "bar"}], [""], None, {}),
            ([{"foo": "bar"}], ["foo"], None, {"bar": {0}}),
            ([{"foo": "bar"}], ["fu"], None, {}),
            ([{"foo": "bar"}], ["foo", "fu"], None, {"bar": {0}}),
            ([{"foo": "bar"}, {"fu": "bar"}], ["foo"], None, {"bar": {0}}),
            ([{"foo": "bar"}, {"fu": "bar"}], ["foo", "fu"], None, {"bar": {0, 1}}),
            ([{"foo": "bar"}, {"foo": "bur"}], ["foo"], None, {"bar": {0}, "bur": {1}}),
            (
                [{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}],
                ["foo"],
                None,
                {"bar": {0, 2}, "bur": {1}},
            ),
            (
                [{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}],
                ["foo"],
                [0],
                {"bar": {0}},
            ),
            (
                [{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}],
                ["foo"],
                [0, 2],
                {"bar": {0, 2}},
            ),
            (
                [{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}],
                ["foo"],
                [0, 2],
                {"bar": {0, 2}},
            ),
            (
                [{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}],
                ["foo"],
                [1],
                {"bur": {1}},
            ),
            ([{"fu": "bar"}, {"foo": "bur"}, {"foo": "bar"}], ["foo"], [0], {}),
            (
                [{"fu": "bar"}, {"foo": "bur"}, {"foo": "bar"}],
                ["foo", "fu"],
                [0],
                {"bar": {0}},
            ),
        ],
    )
    def test_match_value_to_annotation(
        self, annotation, key, indices, expected, empty_merge
    ):
        """Test mapping of annotation field values to indices."""
        assert expected == empty_merge.match_value_to_annotation(
            annotation, key, indices=indices
        )

    @pytest.mark.parametrize(
        "existing_table,new_table,expected",
        [
            ({}, {}, ({}, {})),
            ({"foo": {1}}, {"bar": {1}}, ({}, {})),
            ({"foo": {1}}, {"foo": {1}}, ({1: {1}}, {1: {1}})),
            ({"foo": {1}, "bar": {2}}, {"foo": {1}}, ({1: {1}}, {1: {1}})),
            (
                {"foo": {1}, "bar": {2}},
                {"foo": {1}, "bar": {3}},
                ({1: {1}, 2: {3}}, {1: {1}, 3: {2}}),
            ),
            ({"foo": {1, 2}}, {"foo": {1}}, ({1: {1}, 2: {1}}, {1: {1, 2}})),
            ({"foo": {1}}, {"foo": {1, 2}}, ({1: {1, 2}}, {1: {1}, 2: {1}})),
            ({"foo": {1}}, {"foo": {1, 2}}, ({1: {1, 2}}, {1: {1}, 2: {1}})),
            ({"foo": {1}, "bar": {1}}, {"foo": {1}, "bar": {2}}, ({1: {1, 2}}, {1: {1},
                2: {1}})),
        ],
    )
    def test_match_annotations(self, existing_table, new_table, expected, empty_merge):
        """Test mapping of existing annotation's indices to new
        annotation's indices given value mappings for each annotation.
        """
        assert empty_merge.match_annotations(existing_table, new_table) == expected

    @pytest.mark.parametrize(
        "list_of_keys,values_to_add,dictionary,expected",
        [
            ([], [], {"foo": "bar"}, {"foo": "bar"}),
            (["foo"], [], {}, {}),
            (["foo"], ["bar"], {}, {"foo": {"bar"}}),
            (["foo"], ["bar"], {"fu": {"bar"}}, {"foo": {"bar"}, "fu": {"bar"}}),
            (["foo", "fu"], ["bar"], {}, {"foo": {"bar"}, "fu": {"bar"}}),
            (["foo"], ["bar"], {"foo": {"bar"}}, {"foo": {"bar"}}),
            (["foo"], ["bar"], {"foo": {"bur"}}, {"foo": {"bar", "bur"}}),
        ],
    )
    def test_add_values_to_sets(
        self, list_of_keys, values_to_add, dictionary, expected, empty_merge
    ):
        """Test addition of new values as sets to keys in dictionary."""
        empty_merge.add_values_to_sets(list_of_keys, values_to_add, dictionary)
        assert dictionary == expected

    @pytest.mark.parametrize(
        "list_of_edges,expected",
        [
            ([], []),
            ([{"a": {"1"}}], [{"a": {"1"}}]),
            ([{"a": {"1"}}, {"b": {"2"}}], [{}]),
            ([{"a": {"1"}}, {"a": {"1"}}], [{"a": {"1"}}]),
            ([{"a": {"1"}}, {"a": {"2"}}], [{}]),
            ([{"a": {"1"}}, {"a": {"1", "2"}}], [{"a": {"1"}}]),
            ([{"a": {"1", "2"}}, {"a": {"2"}}], [{"a": {"2"}}]),
            ([{"a": {"1"}, "b": {"2"}}, {"a": {"2"}}], [{}]),
            ([{"a": {"1", "2", "3"}}, {"a": {"2", "3"}}, {"a": {"3"}}], [{"a": {"3"}}]),
        ],
    )
    def test_intersect_edges(self, list_of_edges, expected, empty_merge):
        """Test list of edges are condensed to singe list of edges such
        that values in resulting list were present in all initial lists.
        """
        empty_merge.intersect_edges(list_of_edges)
        assert list_of_edges == expected

    @pytest.mark.parametrize(
        "existing_to_new_unique,new_to_existing_unique,expected_annotation",
        [
            (
                False,
                False,
                MERGED_PRIMARY_FIELDS_MANY_TO_MANY,
            ),
            (
                False,
                True,
                MERGED_PRIMARY_FIELDS_ONE_TO_MANY,
            ),
            (
                True,
                False,
                MERGED_PRIMARY_FIELDS_MANY_TO_ONE,
            ),
            (
                True,
                True,
                MERGED_PRIMARY_FIELDS_ONE_TO_ONE,
            ),
        ],
    )
    def test_add_merged_annotations(
        self,
        existing_to_new_unique,
        new_to_existing_unique,
        expected_annotation,
        basic_merge,
    ):
        """Test addition of matched annotations to existing annotation
        given merge uniqueness parameters.
        """
        basic_merge.existing_to_new_unique = existing_to_new_unique
        basic_merge.new_to_existing_unique = new_to_existing_unique
        basic_merge.existing_to_new_edges.append(existing_to_new_primary_edges())
        basic_merge.new_to_existing_edges.append(new_to_existing_primary_edges())
        basic_merge.add_merged_annotations()
        assert basic_merge.existing_annotation == expected_annotation
        if existing_to_new_unique or new_to_existing_unique:
            assert basic_merge.existing_to_new_edges
            assert basic_merge.new_to_existing_edges
        else:
            assert not basic_merge.existing_to_new_edges
            assert not basic_merge.new_to_existing_edges

    @pytest.mark.parametrize(
        "existing_to_new_unique,new_to_existing_unique,expected",
        [
            (False, False, ({}, {})),
            (
                False,
                True,
                (
                    {1: {1, 7}, 2: {1, 2, 7}, 3: {3, 4, 5}},
                    {1: {1, 2}, 7: {1, 2}, 2: {2}, 3: {3}, 4: {3}, 5: {3}},
                ),
            ),
            (
                True,
                False,
                (
                    {1: {1, 7}, 2: {1, 7}, 3: {5}, 4: {5}},
                    {1: {1, 2}, 5: {3, 4}, 7: {1, 2}}
                )
            ),
            (
                True,
                True,
                (
                    {1: {1, 7}, 2: {1, 2, 7}, 3: {3, 4, 5}, 4: {5}},
                    {1: {1, 2}, 2: {2}, 3: {3}, 4: {3}, 5: {3, 4}, 7: {1, 2}},
                ),
            ),
        ],
    )
    def test_prune_to_unique_edges(
        self,
        existing_to_new_unique,
        new_to_existing_unique,
        expected,
        empty_merge,
    ):
        """Test removal of matched edges based on merge uniqueness
        parameters.
        """
        existing_to_new = existing_to_new_primary_edges()
        new_to_existing = new_to_existing_primary_edges()
        empty_merge.existing_to_new_edges.append(existing_to_new)
        empty_merge.new_to_existing_edges.append(new_to_existing)
        empty_merge.existing_to_new_unique = existing_to_new_unique
        empty_merge.new_to_existing_unique = new_to_existing_unique
        assert empty_merge.prune_to_unique_edges() == expected

    @pytest.mark.parametrize(
        "all_edges,edges_to_prune,expected",
        [
            ({}, {}, {}),
            ({}, {1: {1}}, {}),
            ({1: {1}}, {}, {1: {1}}),
            ({1: {1}}, {1: {1}}, {}),
            ({1: {1, 2}}, {1: {2}}, {1: {1}}),
            ({1: {1, 2}}, {1: {2, 3}}, {1: {1}}),
            ({1: {1, 2}}, {1: {1, 2, 3}}, {}),
            ({1: {1, 2}, 2: {1}}, {2: {1}}, {1: {1, 2}}),
        ],
    )
    def test_prune_edges(self, all_edges, edges_to_prune, expected, empty_merge):
        """Test removal of subset of edges from all edges."""
        empty_merge.prune_edges(all_edges, edges_to_prune)
        assert all_edges == expected
