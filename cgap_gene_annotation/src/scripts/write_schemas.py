import json
from pathlib import Path

from cgap_gene_annotation.src import schemas


SRC_DIRECTORY = "src"
SCHEMA_PATHS = {  # Paths relative to src/
    "schemas/create.json": schemas.CREATE_SCHEMA,
    "schemas/update.json": schemas.UPDATE_SCHEMA,
}


def main():
    """Write schemas from python objects for ease of reading.

    Note: These written schemas are not the source for validation. The
    python objects are validated against, so this script should be run
    whenever the schema objects are updated to keep things in sync.
    """
    for relative_schema_path, schema in SCHEMA_PATHS.items():
        src_path = Path(__file__).parents[1]
        assert src_path.name == SRC_DIRECTORY
        schema_path = src_path.joinpath(relative_schema_path)
        with open(schema_path, "w+") as file_handle:
            json.dump(schema, file_handle, indent=4)


if __name__ == "__main__":
    main()
