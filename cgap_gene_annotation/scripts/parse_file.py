import argparse
import json

from cgap_gene_annotation.src import constants
from cgap_gene_annotation.src.annotations import GeneAnnotation


def run_parse_file(metadata=None, all_records=False):
    """Parse files in metadata and print example records for each.

    :param metadata: The path to the JSON file containing metadata.
    :type metadata: str
    :param all_records: If true, print all records from each file in
        metadata instead of default 5 records per file.
    :type all_records: bool
    """
    gene_annotation = GeneAnnotation(None)
    with open(metadata, "rb") as file_handle:
        parsing_metadata = json.load(file_handle)
    gene_annotation.validate_create_json(parsing_metadata)
    for annotation_metadata in parsing_metadata:
        parser_metadata = annotation_metadata[constants.PARSER]
        files = annotation_metadata[constants.FILES]
        for file_path in files:
            parser = gene_annotation.create_parser(file_path, parser_metadata)
            records = parser.get_records()
            if all_records:
                records = list(records)
                print(
                    "File: %s" % file_path,
                    "Records:",
                    json.dumps(records, indent=4),
                    "\n",
                    sep="\n",
                )
            else:
                first_five = list(next(records) for _ in range(5))
                print(
                    "File: %s" % file_path,
                    "First 5 records:",
                    json.dumps(first_five, indent=4),
                    "\n",
                    sep="\n",
                )


def main():
    """Parse args and run the script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "metadata", type=str, help="Path to the JSON file with annotation metadata"
    )
    parser.add_argument(
        "--all-records",
        action="store_true",
        help="Retrieve all records from files instead of first 5 records",
    )
    args = parser.parse_args()
    run_parse_file(metadata=args.metadata, all_records=args.all_records)


if __name__ == "__main__":
    main()
