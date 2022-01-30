"""Functions/classes required to merge new annotations to an existing
one.

Classes:
    - AnnotationMerge: Primary object called elsewhere in package when
        merging a new annotation.
"""

import json
import logging

from . import constants
from .utils import nested_getter


log = logging.getLogger(__name__)


class AnnotationMerge:
    """Class for merging a new annotation to an existing one.

    Primary method to call externally is merge_annotations(), with
    remaining methods mostly helpers to execute the merge or identify
    parameters for the merge.

    Algorithm here holds both the existing and new annotations in
    memory, and updates them in place rather than create copies.

    General idea is to create new dictionaries that match
    indices of existing --> new and new --> existing annotations based
    on whether the values are identical for the given field names the
    match is based on. With those dictionaries in hand, can add the
    matched new annotations to the existing annotations if the
    conditions for the type of join are met (i.e. a one-to-one mapping
    vs a many-to-many mapping). Can also further refine the matches
    by utilizing additional fields until match conditions are met if
    necessary and such secondary fields are provided.

    NOTE: Sort-merge algorithm here was attempted but is tricky due to
    prevalence of lists of values for some fields within annotations,
    which necessitates duplication of annotations and subsequent
    stitching back together. Also, annotations are generally not sorted
    by desired field values, so sort must be redone for each set of
    fields to match.

    :var existing_annotation: The annotation to merge to.
    :vartype existing_annotation: list(dict)
    :var new_annotation: The annotation to merge in.
    :vartype new_annotation: list(dict)
    :var prefix: The prefix term to use for the new annotation
        when merged in.
    :vartype prefix: str
    :var primary_merge_fields: The merge fields for which annotations
        must match.
    :vartype primary_merge_fields: list(list(str))
    :var secondary_merge_fields: The merge fields used to narrow down
        matched annotations to meet unique match constraints.
    :vartype secondary_merge_fields: list(list(str))
    :var existing_to_new_unique: Whether existing annotations can match
        more than one new annotation (i.e. one-to-one or many-to-one).
    :vartype existing_to_new_unique: bool
    :var new_to_existing_unique: Whether new annotations can match more
        than one existing annotation (i.e. one-to-one or one-to-many).
    :vartype new_to_existing_unique: bool
    :var existing_to_new_edges: Match lists in which the keys are
        existing annotation indices and values are sets of new
        annotation indices.
    :vartype existing_to_new_edges: list
    :var new_to_existing_edges: Match lists in which the keys are new
        annotation indices and values are sets of existing annotation
        indices.
    :vartype new_to_existing_edges: list
    :var debug: Whether to log debug information for this source.
    :vartype debug: bool
    """

    def __init__(
        self, existing_annotation, new_annotation, prefix, merge_info, debug=False
    ):
        """Create class and set attributes.

        :param existing_annotation: The annotation to merge to.
        :type existing_annotation: list(dict)
        :param new_annotation: The annotation to merge in.
        :type new_annotation: list(dict)
        :param prefix: The prefix term to use for the new annotation
            when merged in.
        :type prefix: str
        :param merge_info: The parameters for performing the merge.
        :type merge_info: dict
        :param debug: Whether to log debug information for this source.
        :type debug: bool
        """
        self.existing_annotation = existing_annotation
        self.new_annotation = new_annotation
        self.prefix = prefix
        self.debug = debug
        (
            self.primary_merge_fields,
            self.secondary_merge_fields,
            self.existing_to_new_unique,
            self.new_to_existing_unique,
        ) = self.parse_merge_info(merge_info)
        self.existing_to_new_edges = []
        self.new_to_existing_edges = []

    def parse_merge_info(self, merge_info):
        """Get select merge parameters.

        :param merge_info: The provided merge parameters.
        :type merge_info: dict
        :returns: Individual merge parameters.
        :rtype: (list, list, bool, bool)
        """
        primary_merge_fields = merge_info.get(constants.MERGE_PRIMARY_FIELDS, [])
        secondary_merge_fields = merge_info.get(constants.MERGE_SECONDARY_FIELDS, [])
        (
            new_to_existing_unique,
            existing_to_new_unique,
        ) = self.convert_merge_type_to_bool(
            merge_info.get(
                constants.MERGE_CHOICE,
                (constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_MANY),
            )
        )
        return (
            primary_merge_fields,
            secondary_merge_fields,
            existing_to_new_unique,
            new_to_existing_unique,
        )

    def convert_merge_type_to_bool(self, merge_type):
        """Convert the provided merge type parameters to usable bools.

        :param merge_type: The type of merge to perform.
        :type merge_type: list(string)
        :returns: Merge type as booleans.
        :rtype: list(bool)
        """
        result = [False, False]
        for idx, parameter in enumerate(merge_type):
            if parameter == constants.MERGE_CHOICE_ONE:
                result[idx] = True
        return result

    def merge_annotations(self):
        """Merge the new annotations to the existing ones given the
        merge parameters.

        This is the top-level method for merging the two sets of
        annotations.

        All primary merge fields are used to create annotation matches
        that match across all such fields, while secondary merge fields
        are only used to break "ties" when there's a unique mapping
        constraint for merging.

        General algorithm described above in class docstring.

        The existing annotations are modified in place, while the new
        annotations are eventually deleted to remove from memory.
        """
        log.info(
            "Merging fields to existing annotation under following prefix: %s",
            self.prefix,
        )
        while self.primary_merge_fields:
            self.join_annotations(self.primary_merge_fields)
        self.intersect_edges(self.existing_to_new_edges)
        self.intersect_edges(self.new_to_existing_edges)
        self.add_merged_annotations()
        while self.existing_to_new_edges and self.secondary_merge_fields:
            self.join_annotations(self.secondary_merge_fields)
            self.intersect_edges(self.existing_to_new_edges)
            self.intersect_edges(self.new_to_existing_edges)
            self.add_merged_annotations()
        if self.existing_to_new_edges:
            log.info(
                "%s existing annotations could not be matched to new annotations using"
                " given merge conditions for prefix: %s",
                len(self.existing_to_new_edges[0]),
                self.prefix,
            )
            if self.debug:
                for existing_node, new_nodes in self.existing_to_new_edges[0].items():
                    existing_annotation = self.existing_annotation[existing_node]
                    new_annotations = []
                    for node in new_nodes:
                        new_annotations.append(self.new_annotation[node])
                    log.debug(
                        "Could not match existing annotation with new annotation(s):"
                        "\n%s,\n%s",
                        json.dumps(existing_annotation, indent=4),
                        json.dumps(new_annotations, indent=4),
                    )
        self.new_annotation.clear()
        log.info(
            "Finished merging new annotations to existing annotations for prefix: %s",
            self.prefix,
        )

    def join_annotations(self, merge_fields):
        """Create the mappings of matched annotations for the first
        merge fields of the given list.

        If there's already an existing mapping, only use those indices
        for matching this set of merge fields as the edges will be
        intersected later.

        Update self.existing_to_new_edges and self.new_to_existing_edges
        with the appropriate mapping.

        :param merge_fields: The merge fields to match on.
        :type merge_fields: list(list(str))
        """
        existing_key, new_key = self.get_merge_fields(merge_fields)
        existing_indices = None
        new_indices = None
        if self.existing_to_new_edges:
            existing_indices = list(self.existing_to_new_edges[0].keys())
            new_indices = list(self.new_to_existing_edges[0].keys())
        existing_value_map = self.match_value_to_annotation(
            self.existing_annotation, existing_key, indices=existing_indices
        )
        new_value_map = self.match_value_to_annotation(
            self.new_annotation, new_key, indices=new_indices
        )
        existing_to_new_matches, new_to_existing_matches = self.match_annotations(
            existing_value_map, new_value_map
        )
        self.existing_to_new_edges.append(existing_to_new_matches)
        self.new_to_existing_edges.append(new_to_existing_matches)

    def get_merge_fields(self, merge_field_list):
        """Get the first set of merge fields from the merge field list.

        :param merge_field_list: The merge fields.
        :type merge_field_list: list(list(str))
        :returns: First merge fields off list.
        :rtype: list(str)
        """
        merge_fields = merge_field_list.pop(0)
        return [x.strip() for x in merge_fields]

    def match_value_to_annotation(self, annotation, field, indices=None):
        """Match annotation field values to annotation indices.

        :param annotation: Complete annotations.
        :type annotation: list(dict)
        :param field: The field to get from each annotation.
        :type field: str
        :param indices: Indices of the annotations for which to match
            field values.
        :type indices: list(int)
        :returns: Mapping of field values to the indices of annotations
            containing the field value.
        :rtype: dict
        """
        matches = {}
        if field:
            if indices:
                for idx in indices:
                    item = annotation[idx]
                    item_value = nested_getter(item, field)
                    self.add_values_to_sets(item_value, [idx], matches)
            else:
                for idx, item in enumerate(annotation):
                    item_value = nested_getter(item, field)
                    self.add_values_to_sets(item_value, [idx], matches)
        return matches

    def match_annotations(self, existing_value_map, new_value_map):
        """Match the existing and new annotations if the field values
        match.

        The match tables created are matches of the indices of the
        respective annotations, not the annotations themselves.

        Two match tables are created, with either the existing
        annotation indices as keys and the new annotation indices as
        values or vice versa, to facilitate identifying which matches
        do not meet the mapping constraints at later steps.

        :param existing_value_map: Map of field values to the indices
            of the existing annotations that have the values.
        :type existing_value_map: dict
        :param new_value_map: Map of field values to the indices of the
            new annotations that have the values.
        :type new_value_map: dict
        :returns: Matched mappings of indices to indices.
        :rtype: (dict, dict)
        """
        existing_to_new = {}
        new_to_existing = {}
        for key in existing_value_map:
            new_annotation_idx = new_value_map.get(key)
            if new_annotation_idx:
                existing_annotation_idx = existing_value_map[key]
                self.add_values_to_sets(
                    existing_annotation_idx, new_annotation_idx, existing_to_new
                )
                self.add_values_to_sets(
                    new_annotation_idx, existing_annotation_idx, new_to_existing
                )
        return existing_to_new, new_to_existing

    def add_values_to_sets(self, list_of_keys, values_to_add, dictionary):
        """Update dictionary keys with given values.

        Sets are utilized as the value type in the dictionary to
        facilitate later operations on the dictionary, such as occurs
        in the intersect_edges method below.

        :param list_of_keys: The keys in the dictionary to update with
            the given values.
        :type list_of_keys: list
        :param values_to_add: The values to add to the keys of the
            dictionary.
        :type values_to_add: list
        :param dictionary: The dictionary to update.
        :type dictionary: dict
        """
        if values_to_add:
            for item in list_of_keys:
                if dictionary.get(item):
                    dictionary[item].update(values_to_add)
                else:
                    dictionary[item] = set(values_to_add)

    def intersect_edges(self, list_of_edges):
        """Intersect lists of matches to single list, so all matches
        were present in all lists.

        Each match list typically comes from different annotation
        fields, so here we keep only those matches which occur across
        all fields.

        :param list_of_edges: All match lists to narrow down to one.
        :type list_of_edges: list(dict)
        """
        while len(list_of_edges) > 1:
            edge_list_1 = list_of_edges[0]
            edge_list_2 = list_of_edges[1]
            keys_to_delete = []
            for key, value_1 in edge_list_1.items():
                if key in edge_list_2:
                    value_2 = edge_list_2[key]
                    value_1 = value_1.intersection(value_2)
                    if not value_1:
                        keys_to_delete.append(key)
                    else:
                        edge_list_1[key] = value_1
                else:
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del edge_list_1[key]
            del list_of_edges[1]

    def add_merged_annotations(self):
        """Add the matched annotations that meet mapping constraints.

        Remove all matches that do not meet mapping constraints (and
        set them to be the new matches for subsuquent narrowing, if
        applicable).

        For matches that do meet mapping constraints, update the
        existing annotation with the new values.
        """
        merge_count = 0
        pruned_new_to_existing, pruned_existing_to_new = self.prune_to_unique_edges()
        existing_to_new_edges = {}
        if self.existing_to_new_edges:
            existing_to_new_edges = self.existing_to_new_edges[0]
        for existing_node, new_nodes in existing_to_new_edges.items():
            merge_count += 1
            existing_annotation = self.existing_annotation[existing_node]
            existing_annotation[self.prefix] = []
            for node in new_nodes:
                existing_annotation[self.prefix].append(self.new_annotation[node])
                if self.debug:
                    log.debug(
                        "Merged a pair of annotations:\n%s,\n%s",
                        json.dumps(existing_annotation, indent=4),
                        json.dumps(self.new_annotation[node], indent=4),
                    )
        log.info("Merged %s annotations for prefix: %s", merge_count, self.prefix)
        if pruned_existing_to_new:
            self.existing_to_new_edges = [pruned_existing_to_new]
        else:
            self.existing_to_new_edges = []
        if pruned_new_to_existing:
            self.new_to_existing_edges = [pruned_new_to_existing]
        else:
            self.new_to_existing_edges = []

    def prune_to_unique_edges(self):
        """Remove subset of matched edges based on expected merge
        mapping.

        If merge mapping contains a uniqueness constraint (e.g. a
        one-to-many), identify the matched edges that don't meet that
        constraint and remove then from both the existing-to-new and
        the new-to-existing match tables.

        :returns: The matched edges that did not meet the mapping
            constraints.
        :rtype: (list(dict), list(dict))
        """
        pruned_existing_to_new = {}
        pruned_new_to_existing = {}
        existing_to_new = {}
        new_to_existing = {}
        if self.existing_to_new_edges:
            existing_to_new = self.existing_to_new_edges[0]
        if self.new_to_existing_edges:
            new_to_existing = self.new_to_existing_edges[0]
        if self.existing_to_new_unique:
            for key, value in existing_to_new.items():
                if len(value) > 1:
                    self.add_values_to_sets([key], value, pruned_existing_to_new)
                    self.add_values_to_sets(value, [key], pruned_new_to_existing)
        if self.new_to_existing_unique:
            for key, value in new_to_existing.items():
                if len(value) > 1:
                    self.add_values_to_sets([key], value, pruned_new_to_existing)
                    self.add_values_to_sets(value, [key], pruned_existing_to_new)
        self.prune_edges(existing_to_new, pruned_existing_to_new)
        self.prune_edges(new_to_existing, pruned_new_to_existing)
        return pruned_new_to_existing, pruned_existing_to_new

    def prune_edges(self, all_edges, edges_to_prune):
        """Remove a subset of matched edges from set of all matched
        edges.

        Matches are removed from the values of the dict, and if no
        values remain, the key is also removed.

        :param all_edges: All matched edges, as key/value pairs with
            value as a set.
        :type all_edges: dict
        :param edges_to_prune: The matched edges to remove, as
            key/value pairs with value as a set.
        :type edges_to_prune: dict
        """
        for key, value in edges_to_prune.items():
            edge = all_edges.get(key)
            if edge:
                difference = edge.difference(value)
                if difference:
                    all_edges[key] = difference
                else:
                    del all_edges[key]
