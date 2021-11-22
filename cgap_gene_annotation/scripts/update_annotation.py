import argparse
import json

from ..src.annotations import GeneAnnotation


def run_update_annotation(file_path=None, metadata=None):
    """"""
    gene_annotation = GeneAnnotation(file_path)
    with open(metadata, "rb") as json_handle:
        update_metadata = json.load(json_handle)
    gene_annotation.update_annotation(update_metadata)
    gene_annotation.write_file()


def main():
    """"""
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help="Path to the gene annotation file to
            update")
    parser.add_argument(
        "metadata", type=str, help="Path to the JSON file with update metadata"
    )
    args = parser.parse_args()
    run_update_annotation(file_path=args.file, metadata=args.metadata)


if __name__ == "__main__":
    main()
