import argparse
import json

from ..src.annotations import GeneAnnotation


def run_add_annotation(file_path=None, annotations=None):
    """"""
    gene_annotation = GeneAnnotation(file_path)
    with open(annotations, "rb") as json_handle:
        annotations = json.load(json_handle)
    gene_annotation.add_annotations(annotations)
    gene_annotation.write_file()

def main():
    """"""
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, help="Path to the gene annotation file")
    parser.add_argument(
        "annotations", type=str, help="Path to the JSON file for annotations to add"
    )
    args = parser.parse_args()
    run_add_annotation(file_path=args.file, annotations=args.annotations)


if __name__ == "__main__":
    main()
