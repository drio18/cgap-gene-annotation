import argparse
import json
import logging

from cgap_gene_annotation.src.annotations import GeneAnnotation
from cgap_gene_annotation.src.utils import configure_log


def run_create_annotation(file_path=None, metadata=None):
    """Write new annotations as per given metadata.

    :param file_path: The path to the file to which the annotations are
        written.
    :type file_path: str
    :param metadata: The path to the JSON metadata file for the
        annotations to create.
    :type metadata: str
    """
    gene_annotation = GeneAnnotation(file_path)
    with open(metadata, "rb") as file_handle:
        annotation_metadata = json.load(file_handle)
    gene_annotation.create_annotation(annotation_metadata)
    gene_annotation.write_file()


def main():
    """Parse args and run the script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file", type=str, help="Path for the gene annotation file to create"
    )
    parser.add_argument(
        "metadata", type=str, help="Path to the JSON file with annotation metadata"
    )
    parser.add_argument("--log-file", "-f", type=str, help="Path for logging file")
    parser.add_argument(
        "--log-level",
        "-l",
        type=str,
        help="Logging level",
        choices=["debug", "info", "warning"],
        default="info",
    )
    args = parser.parse_args()
    configure_log(args.log_file, args.log_level)
    run_create_annotation(file_path=args.file, metadata=args.metadata)


if __name__ == "__main__":
    main()
