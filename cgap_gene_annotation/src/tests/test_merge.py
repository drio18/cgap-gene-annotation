import pytest

from ..merge import nested_getter, AnnotationMerge


@pytest.mark.parametrize(
    "dict_item,fields_to_get,expected",
    [
        ({}, ["foo"], []),
        ({}, ["foo", "bar"], []),
        ({"foo": {"bar": "1"}}, ["foo"], {"bar": "1"}),
        ({"foo": {"bar": "1"}}, ["foo", "bar"], ["1"]),
        ({"foo": {"bar": ["1", "2"]}}, ["foo", "bar"], ["1", "2"]),
        ({"foo": [{"bar": "1"}, {"bar": "2"}]}, ["foo", "bar"], ["1", "2"]),
        ({"foo": {"bar": {"something"}}}, ["foo", "bar"], {"something"}),
        ({"foo": {"bar": 1}}, ["foo", "bar"], 1),
        ({"foo": {"foo": {"bar": "something"}}}, ["foo", "bar"], []),
    ]
)
def test_nested_getter(dict_item, fields_to_get, expected):
    """"""
    result = nested_getter(dict_item, fields_to_get)
    if result and isinstance(result, list):
        result = set(result)
        expected = set(expected)
    assert result == expected


class TestAnnotationMerge:

    @pytest.fixture
    def empty_merge(self):
        return AnnotationMerge(None, None, None, {})

    @pytest.mark.parametrize(
        "merge_info,expected",
        [
            ({}, ([], [], False, False)),
            ({"type": ("one", "one")}, ([], [], True, True)),
            ({"type": ("one", "many")}, ([], [], False, True)),
            ({"type": ("many", "one")}, ([], [], True, False)),
            ({"type": ("many", "many")}, ([], [], False, False)),
            ({"merge_fields": {}}, ([], [], False, False)),
            (
                {"merge_fields": {"primary": [], "secondary": []}},
                ([], [], False, False)
            ),
            (
                {"merge_fields": {"primary": [("foo.bar", "bar.foo")], "secondary": []}},
                ([("foo.bar", "bar.foo")], [], False, False)
            ),
            (
                {"merge_fields": {"primary": [], "secondary": [("foo.bar", "bar.foo")]}},
                ([], [("foo.bar", "bar.foo")], False, False)
            ),
        ]
    )
    def test_parse_merge_info(self, merge_info, expected, empty_merge):
        """"""
        assert empty_merge.parse_merge_info(merge_info) == expected

    @pytest.mark.parametrize(
        "merge_field_list,expected",
        [
            ([("foo", "bar")], [["foo"], ["bar"]]),
            ([("foo.bar", "bar.foo")], [["foo", "bar"], ["bar", "foo"]]),
            ([("foo", "bar"), ("bar", "foo")], [["foo"], ["bar"]]),
        ]
    )
    def test_get_merge_fields(self, merge_field_list, expected, empty_merge):
        """"""
        assert empty_merge.get_merge_fields(merge_field_list) == expected

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
        ]
    )
    def test_intersect_edges(self, list_of_edges, expected, empty_merge):
        """"""
        empty_merge.intersect_edges(list_of_edges)
        assert list_of_edges == expected

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
        ]
    )
    def test_add_values_to_sets(
        self, list_of_keys, values_to_add, dictionary, expected, empty_merge
    ):
        """"""
        empty_merge.add_values_to_sets(list_of_keys, values_to_add, dictionary)
        assert dictionary == expected

    @pytest.mark.parametrize(
        "annotation,key,indices,expected",
        [
            ([], [], None, {}),
            ([{"foo": "bar"}], [], None, {}),
            ([{"foo": "bar"}], ["foo"], None, {"bar": {0}}),
            ([{"foo": "bar"}], ["fu"], None, {}),
            ([{"foo": "bar"}, {"fu": "bar"}], ["foo"], None, {"bar": {0}}),
            ([{"foo": "bar"}, {"foo": "bur"}], ["foo"], None, {"bar": {0}, "bur": {1}}),
            ([{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}], ["foo"], None, {"bar": {0, 2}, "bur": {1}}),
            ([{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}], ["foo"], [0], {"bar": {0}}),
            ([{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}], ["foo"], [0, 2], {"bar": {0, 2}}),
            ([{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}], ["foo"], [0, 2], {"bar": {0, 2}}),
            ([{"foo": "bar"}, {"foo": "bur"}, {"foo": "bar"}], ["foo"], [1], {"bur": {1}}),
            ([{"fu": "bar"}, {"foo": "bur"}, {"foo": "bar"}], ["foo"], [0], {}),
        ]
    )
    def test_match_value_to_annotation(
        self, annotation, key, indices, expected, empty_merge
    ):
        """"""
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
            ({"foo": {1}, "bar": {2}}, {"foo": {1}, "bar": {3}}, ({1: {1}, 2: {3}}, {1: {1}, 3: {2}})),
            ({"foo": {1, 2}}, {"foo": {1}}, ({1: {1}, 2: {1}}, {1: {1, 2}})),
            ({"foo": {1}}, {"foo": {1, 2}}, ({1: {1, 2}}, {1: {1}, 2: {1}})),
            ({"foo": {1}}, {"foo": {1, 2}}, ({1: {1, 2}}, {1: {1}, 2: {1}})),
        ]
    )
    def test_match_annotations(self, existing_table, new_table, expected, empty_merge):
        """"""
        assert empty_merge.match_annotations(existing_table, new_table) == expected

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
        ]
    )
    def test_prune_edges(self, all_edges, edges_to_prune, expected, empty_merge):
        """"""
        empty_merge.prune_edges(all_edges, edges_to_prune)
        assert all_edges == expected

    @pytest.fixture
    def annotation_edges(self):
        """"""
        existing_to_new = {1: {1, 2}, 2: {2}, 3: {3}, 4: {3}, 5: {3, 4}, 6: {5}}
        new_to_existing = {1: {1}, 2: {1, 2}, 3: {3, 4, 5}, 4: {5}, 5: {6}}
        return existing_to_new, new_to_existing

    @pytest.mark.parametrize(
        "existing_to_new_unique,new_to_existing_unique,expected",
        [
            (False, False, ({}, {})),
            (False, True, (
                {2: {1, 2}, 3: {3, 4, 5}},
                {1: {2}, 2: {2}, 3: {3}, 4: {3}, 5: {3}}
            )),
            (True, False, (
                {1: {1}, 2: {1}, 3: {5}, 4: {5}},
                {1: {1, 2}, 5: {3, 4}}
            )),
            (True, True, (
                {1: {1}, 2: {1, 2}, 3: {3, 4, 5}, 4: {5}},
                {1: {1, 2}, 2: {2}, 3: {3}, 4: {3}, 5: {3, 4}}
            )),
        ]
    )
    def test_prune_to_unique_edges(
        self, existing_to_new_unique, new_to_existing_unique, expected, empty_merge,
        annotation_edges,
    ):
        """"""
        existing_to_new, new_to_existing = annotation_edges
        empty_merge.existing_to_new_edges.append(existing_to_new)
        empty_merge.new_to_existing_edges.append(new_to_existing)
        empty_merge.existing_to_new_unique = existing_to_new_unique
        empty_merge.new_to_existing_unique = new_to_existing_unique
        assert empty_merge.prune_to_unique_edges() == expected

#    def test_add_merged_annotation(self, empty_merge):
#        """"""
#        empty_merge.existing_annotation = [
