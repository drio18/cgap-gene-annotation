import argparse
import json

from ..src.annotations import GeneAnnotation


def run_create_annotation(file_path=None, metadata=None):
    """"""
    gene_annotation = GeneAnnotation(file_path)
    with open(metadata, "rb") as json_handle:
        annotation_metadata = json.load(json_handle)
    gene_annotation.create_annotation(annotation_metadata)
    gene_annotation.write_file()


def main():
    """"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "file", type=str, help="Path for the gene annotation file to create"
    )
    parser.add_argument(
        "metadata", type=str, help="Path to the JSON file with annotation metadata"
    )
    args = parser.parse_args()
    run_create_annotation(file_path=args.file, metadata=args.metadata)


if __name__ == "__main__":
    main()
