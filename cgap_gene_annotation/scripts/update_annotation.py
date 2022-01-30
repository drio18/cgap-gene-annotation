import argparse
import json

from cgap_gene_annotation.src.annotations import GeneAnnotation
from cgap_gene_annotation.src.utils import configure_log


def run_update_annotation(file_path=None, metadata=None):
    """Update an existing annotation per given metadata.

    :param file_path: The path to the existing annotation file.
    :type file_path: str
    :param metadata: The path to the JSON metadata file.
    :type metadata: str
    """
    gene_annotation = GeneAnnotation(file_path)
    with open(metadata, "rb") as file_handle:
        update_metadata = json.load(file_handle)
    gene_annotation.update_annotation(update_metadata)
    gene_annotation.write_file()


def main():
    """Parse args and run the script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file", type=str, help="Path to the gene annotation file to update"
    )
    parser.add_argument(
        "metadata", type=str, help="Path to the JSON file with update metadata"
    )
    parser.add_argument("--log-file", "-f", type=str, help="Path for logging file")
    parser.add_argument(
        "--log-level",
        "-l",
        type=str,
        help="Logging level",
        choices=["debug", "info", "warning"],
        default="debug",
    )
    args = parser.parse_args()
    configure_log(args.log_file, args.log_level)
    run_update_annotation(file_path=args.file, metadata=args.metadata)


if __name__ == "__main__":
    main()
