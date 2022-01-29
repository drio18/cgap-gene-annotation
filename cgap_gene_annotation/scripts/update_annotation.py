import argparse
import json

from cgap_gene_annotation.src.annotations import GeneAnnotation


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
    args = parser.parse_args()
    run_update_annotation(file_path=args.file, metadata=args.metadata)


if __name__ == "__main__":
    main()
