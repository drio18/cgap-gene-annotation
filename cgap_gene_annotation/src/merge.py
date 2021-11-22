import logging

from . import constants


def nested_getter(item, fields_to_get):
    """"""
    result = []
    if item and isinstance(item, list):
        for sub_item in item:
            sub_result = nested_getter(sub_item, fields_to_get.copy())
            result += sub_result
        result = list(set(result))
    elif isinstance(item, dict):
        field = fields_to_get.pop(0)
        result = item.get(field, [])
        if fields_to_get:
            result = nested_getter(result, fields_to_get)
    if isinstance(result, str):
        result = [result]
    return result


class AnnotationMerge:
    """"""

    FIELD_SEPARATOR = "."

    def __init__(
        self, existing_annotation, new_annotation, prefix, merge_info, debug=False
    ):
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
        self.new_not_added = []
        self.existing_to_new_edges = []
        self.new_to_existing_edges = []

    def parse_merge_info(self, merge_info):
        """"""
        primary_merge_fields = merge_info.get(constants.MERGE_PRIMARY_FIELDS, [])
        secondary_merge_fields = merge_info.get(constants.MERGE_SECONDARY_FIELDS, [])
        (
            new_to_existing_unique,
            existing_to_new_unique,
        ) = self.convert_merge_type_to_bool(
            merge_info.get(
                constants.MERGE_CHOICE,
                (constants.MERGE_CHOICE_MANY, constants.MERGE_CHOICE_MANY))
        )
        return (
            primary_merge_fields,
            secondary_merge_fields,
            existing_to_new_unique,
            new_to_existing_unique,
        )

    def convert_merge_type_to_bool(self, merge_type_tuple):
        """"""
        result = [False, False]
        for idx, merge_type in enumerate(merge_type_tuple):
            if merge_type == constants.MERGE_CHOICE_ONE:
                result[idx] = True
        return result

    def merge_annotations(self):
        """"""
        logging.info(
            "Merging fields to existing annotation under following prefix: %s"
            % self.prefix
        )
        while self.primary_merge_fields:
            self.join_annotations(self.primary_merge_fields)
        self.intersect_edges(self.existing_to_new_edges)
        self.intersect_edges(self.new_to_existing_edges)
        self.add_merged_annotations()
        if self.existing_to_new_edges:
            logging.info(
                "%s existing annotations could not be matched to new annotations using"
                " primary fields given merge conditions"
                % len(self.existing_to_new_edges[0])
            )
        while self.existing_to_new_edges and self.secondary_merge_fields:
            self.join_annotations(self.secondary_merge_fields)
            self.intersect_edges(self.existing_to_new_edges)
            self.intersect_edges(self.new_to_existing_edges)
            self.add_merged_annotations()
        if self.existing_to_new_edges:
            logging.info(
                "%s existing annotations could not be matched to new annotations using"
                " primary and secondary fields given merge conditions"
                % len(self.existing_to_new_edges[0])
            )
            if self.debug:
                for existing_node, new_nodes in self.existing_to_new_edges[0].items():
                    existing_annotation = self.existing_annotation[existing_node]
                    new_annotations = []
                    for node in new_nodes:
                        new_annotations.append(self.new_annotation[node])
                    logging.debug(
                        "Could not match existing annotation with new annotation(s):"
                        " %s, %s" % (existing_annotation, new_annotations)
                    )
        self.new_annotation.clear()
        logging.info(
            "Finished merging new annotations to existing annotations under following"
            " prefix: %s" % self.prefix
        )

    def join_annotations(self, merge_fields):
        """"""
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
        """"""
        merge_fields = merge_field_list.pop(0)
        return [x.split(self.FIELD_SEPARATOR) for x in merge_fields]

    def match_value_to_annotation(self, annotation, key, indices=None):
        """"""
        matches = {}
        if key:
            if indices:
                for idx in indices:
                    item = annotation[idx]
                    item_value = nested_getter(item, key.copy())
                    self.add_values_to_sets(item_value, [idx], matches)
            else:
                for idx, item in enumerate(annotation):
                    item_value = nested_getter(item, key.copy())
                    self.add_values_to_sets(item_value, [idx], matches)
        return matches

    def match_annotations(self, existing_value_map, new_value_map):
        """"""
        existing_to_new = {}
        new_to_existing = {}
        for value in existing_value_map:
            new_annotation_idx = new_value_map.get(value)
            if new_annotation_idx:
                existing_annotation_idx = existing_value_map[value]
                self.add_values_to_sets(
                    existing_annotation_idx, new_annotation_idx, existing_to_new
                )
                self.add_values_to_sets(
                    new_annotation_idx, existing_annotation_idx, new_to_existing
                )
        return existing_to_new, new_to_existing

    @staticmethod
    def add_values_to_sets(list_of_keys, values_to_add, dictionary):
        """"""
        if values_to_add:
            for item in list_of_keys:
                if dictionary.get(item):
                    dictionary[item].update(values_to_add)
                else:
                    dictionary[item] = set(values_to_add)

    @staticmethod
    def intersect_edges(list_of_edges):
        """"""
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
        """"""
        pruned_new_to_existing, pruned_existing_to_new = self.prune_to_unique_edges()
        existing_to_new_edges = {}
        if self.existing_to_new_edges:
            existing_to_new_edges = self.existing_to_new_edges[0]
        for existing_node, new_nodes in existing_to_new_edges.items():
            existing_annotation = self.existing_annotation[existing_node]
            existing_annotation[self.prefix] = []
            for node in new_nodes:
                existing_annotation[self.prefix].append(self.new_annotation[node])
                if self.debug:
                    logging.debug(
                        "Merged a pair of annotations: %s, %s"
                        % (existing_annotation, self.new_annotation[node])
                    )
        if pruned_existing_to_new:
            self.existing_to_new_edges = [pruned_existing_to_new]
        else:
            self.existing_to_new_edges = []
        if pruned_new_to_existing:
            self.new_to_existing_edges = [pruned_new_to_existing]
        else:
            self.new_to_existing_edges = []

    def prune_to_unique_edges(self):
        """"""
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

    @staticmethod
    def prune_edges(all_edges, edges_to_prune):
        """"""
        for key, value in edges_to_prune.items():
            edge = all_edges.get(key)
            if edge:
                difference = edge.difference(value)
                if difference:
                    all_edges[key] = difference
                else:
                    del all_edges[key]
