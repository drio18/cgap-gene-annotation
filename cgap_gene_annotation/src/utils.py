"""Functions/classes shared across modules.

Functions:
    - nested_getter: Recursively retrieves nested fields from within
        dicts.

Classes:
    - FileHandler: Open a local or S3 file (gzipped or not), providing
        a handle within generator to be used.
"""

import codecs
import gzip
import io
import logging
from contextlib import closing
from urllib.parse import urlparse

import boto3


log = logging.getLogger(__name__)

S3_FILE_URI_SCHEME = "s3"
S3_FILE_URL_HOST_NAME = "s3.amazonaws.com"
FIELD_SEPARATOR = "."


def nested_setter(item, field_to_set, value=None, delete_field=False):
    """Recursively set fields in dictionaries.

    Note: Not intended to loop through lists of dicts as nested_getter
    does.

    :param item: The dictionary of interest,
    :type item: dict
    :param field_to_set: The field(s) in the dictionary to set/delete.
    :type field_to_set: str
    :param value: The value to set for the field.
    :type value: str or None
    :param delete_field: Whether to delete the given field from the
        item (if present).
    :type delete_field: bool
    """
    fields = field_to_set.split(FIELD_SEPARATOR)
    if fields:
        # Field name may have FIELD_SEPARATOR within it, so check that first before
        # assuming nested field.
        high_level_item_value = item.get(field_to_set)
        if high_level_item_value is not None:
            if delete_field:
                item_value = item.get(field_to_set)
                if item_value is not None:
                    del item[field_to_set]
            elif value is not None:
                item[field_to_set] = value
        else:
            current_field = fields.pop(0)
            field_to_set = FIELD_SEPARATOR.join(fields)
            nested_item_value = item.get(current_field)
            if isinstance(nested_item_value, dict):
                nested_setter(
                    nested_item_value, field_to_set, value=value, delete_field=delete_field
                )
            elif nested_item_value is None and value is not None:
                if fields:
                    current_field_value = {}
                    item[current_field] = current_field_value
                    nested_setter(
                        current_field_value, field_to_set, value=value,
                        delete_field=delete_field
                    )
                else:
                    item[current_field] = value


def nested_getter(item, field_to_get, string_return=False):
    """Recursively retrieve fields from objects.

    As input files are expected to be text files, fields are expected
    to be either lists of strings or strings, with the item of interest
    only a dictionary upon first call of the function. If assumption
    fails to hold, update accordingly.

    :param item: The object of interest.
    :type item: dict or list or str
    :param field_to_get: The field name to be retrieved from the
        item.
    :type field_to_get: str
    :param string_return: Whether to try to return a string result or
        a list (default is list).
    :type: boolean
    :returns: Retrieved fields from item.
    :rtype: list(str) or str
    """
    result = []
    if item and isinstance(item, list):
        for sub_item in item:
            sub_result = nested_getter(sub_item, field_to_get)
            result += sub_result
        result = list(set(result))
    elif isinstance(item, dict):
        # Allow field names to contain FIELD_SEPARATOR in terminal
        # field but not higher-level field, e.g. can have an item with
        # {"foo.bar": "something"} and field_to_get "foo.bar", but not
        # item of {"foo.bar": {"fu": "bur"}} and field_to_get
        # "foo.bar.fu". Alternative to get around this would be to
        # set FIELD_SEPARATOR to something less likely to be in field
        # names or to have parsers not allow/change field names if they
        # contain FIELD_SEPARATOR.
        result = item.get(field_to_get)
        if result:
            field_to_get = ""
        if result is None and FIELD_SEPARATOR in field_to_get:
            field_terms = field_to_get.split(FIELD_SEPARATOR)
            first_term = field_terms.pop(0)
            result = item.get(first_term)
            if result:
                field_to_get = FIELD_SEPARATOR.join(field_terms)
        if result and field_to_get:
            result = nested_getter(result, field_to_get, string_return=string_return)
        elif result is None:
            if not string_return:
                result = []
    if isinstance(result, str) and not string_return:
        result = [result]
    elif isinstance(result, list) and len(result) == 1 and string_return:
        result = result[0]
    return result


class FileHandler:
    """Class for opening files, locally or from S3.

    Provide handle within generator to keep file open until generator
    iteration finished, facilitating garbage collection at an
    appropriate time.

    If unable to properly open file, catch the exception, log it, and
    return an empty generator, so downstream code continues to run.

    :var file_path: The path to the file to open.
    :vartype file_path: str
    :var binary: Whether to open the file in text or binary mode.
        Default is text mode. Only applies to local files.
    :vartype binary: bool
    """

    GZIP_EXTENSION = ".gz"

    def __init__(self, file_path, binary=False):
        """Create class and set attribute.

        :param file_path: The path to the file to open.
        :type file_path: str
        :param binary: Whether to open the file in text or binary mode.
            Default is text mode. Only applies to local files.
        :type binary: bool
        """
        self.file_path = file_path
        self.binary = binary

    def get_handle(self):
        """Determine if file is on S3 or local and route accordingly.

        :param file_path: The path to the file to open.
        :type file_path: str
        :param binary: Whether to open the file in text or binary mode.
            Default is text mode.
        :type binary: bool
        :returns: File handle generator (empty if file not opened).
        :rtype: collections.Iterable[object]
        """
        s3_bucket, s3_key = self.get_s3_parameters()
        if s3_bucket and s3_key:
            return self.stream_s3_file(s3_bucket, s3_key)
        else:
            return self.open_local_file()

    def open_local_file(self):
        """Open local file and return handle within generator.

        :returns: File handle generator (empty if file not opened).
        :rtype: collections.Iterable[object]
        """
        if self.file_path.endswith(self.GZIP_EXTENSION):
            open_function = gzip.open
        else:
            open_function = open
        try:
            if self.binary:
                with open_function(
                    self.file_path, mode="rb", encoding="utf-8"
                ) as file_handle:
                    yield file_handle
            else:
                with open_function(
                    self.file_path, mode="rt", encoding="utf-8-sig"
                ) as file_handle:
                    yield file_handle
        except (FileNotFoundError, OSError):
            log.exception("Could not open file: %s", self.file_path)

    def get_s3_parameters(self):
        """Check if file is on AWS S3.

        Looking for either S3 URI or object URL.

        :returns: Names of bucket and key, if found.
        :rtype: (str or None, str or None)
        """
        bucket = None
        key = None
        if (
            self.file_path.startswith(S3_FILE_URI_SCHEME)
            or S3_FILE_URL_HOST_NAME in self.file_path
        ):
            try:
                parsed_file_path = urlparse(self.file_path)
                if parsed_file_path.scheme == S3_FILE_URI_SCHEME:
                    bucket = parsed_file_path.hostname
                    key = parsed_file_path.path
                elif S3_FILE_URL_HOST_NAME in parsed_file_path.hostname:
                    bucket = parsed_file_path.hostname.split(".")[0]
                    key = parsed_file_path.path
                if key.startswith("/"):
                    key = key[1:]
            except Exception:
                pass
        return bucket, key

    def stream_s3_file(self, bucket, key):
        """Get file stream from S3 and wrap in text generator.

        :param bucket: The S3 bucket.
        :type bucket: str
        :param key: The S3 key.
        :type key: str
        :returns: File text stream.
        :rtype: collections.Iterable()
        """
        encoding = "utf-8"
        s3_client = boto3.client("s3")
        try:
            stream = s3_client.get_object(Bucket=bucket, Key=key)["Body"]
            with closing(stream):
                if key.endswith(self.GZIP_EXTENSION):
                    stream = gzip.GzipFile(mode="rb", fileobj=stream)
                    yield io.TextIOWrapper(stream, encoding=encoding)
                else:
                    yield codecs.getreader(encoding)(stream)
        except s3_client.exceptions.NoSuchKey:
            log.exception(
                "Could not find a file on S3 in the given bucket.\n"
                "Bucket: %s\n"
                "File: %s\n",
                bucket, key
            )
        except s3_client.exceptions.ClientError:
            log.exception(
                "Could not open a file on S3.\n"
                "Bucket: %s\n"
                "File: %s\n",
                bucket, key
            )


def configure_log(file_path, log_level):
    """Set up logging.

    :param file_path: Path to log file.
    :type file_path: str
    :param log_level: Logging level.
    :type log_level: str
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % log_level)
    logging.basicConfig(
        filename=file_path, level=numeric_level,
        format="%(asctime)s %(levelname)s [%(name)s]\t%(message)s"
    )
