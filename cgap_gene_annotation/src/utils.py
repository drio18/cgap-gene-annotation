import gzip
import logging


def open_file(file_path, binary=False):
    """"""
    # TODO: S3 files
    if file_path.endswith(".gz"):
        open_function = gzip.open
    else:
        open_function = open
    try:
        if binary:
            with open_function(file_path, mode="rb") as file_handle:
                yield file_handle
        else:
            with open_function(file_path, mode="rt") as file_handle:
                yield file_handle
    except (FileNotFoundError, OSError):
        logging.exception("Could not open file: %s" % file_path)
