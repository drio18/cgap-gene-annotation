import argparse

from ..src import constants
from ..src.annotations import GeneAnnotation


def run_parse_file(input_file=None, metadata=None, all_records=False):
    """"""
    gene_annotation = GeneAnnotation(None)
    gene_annotation.validate_create_json(metadata)
    for annotation_metadata in metadata:
        parser_metadata = annotation_metadata[constants.PARSER]
        files = annotation_metadata[constants.FILES]
        for file_path in files:
            parser = gene_annotation.create_parser(file_path, parser_metadata)
            records = parser.get_records()
            header = parser.header
            if all_records:
                records = list(records)
                print(
                    "File: %s" % file_path,
                    "Header: %s" % header,
                    "Records:",
                    records,
                    sep="\n",
                )
            else:
                first_five = list(next(records) for _ in range(5))
                print(
                    "File: %s" % file_path,
                    "Header: %s" % header,
                    "First 5 records:",
                    first_five,
                    sep="\n",
                )


def main():
    """"""
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help="Path for the file to parse")
    parser.add_argument(
        "metadata", type=str, help="Path to the JSON file with annotation metadata"
    )
    parser.add_argument(
        "--all-records", action="store_true",
        help="Retrieve all records from files instead of first 5 records"
    )
    args = parser.parse_args()
    run_parse_file(input_file=args.file, metadata=args.metadata,
            all_records=args.all_records)


if __name__ == "__main__":
    main()
