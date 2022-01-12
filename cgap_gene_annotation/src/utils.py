"""Functions/classes shared across modules.

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


class FileHandler:
    """Class for opening files, locally or from S3.

    Provide handle within generator to keep file open until generator
    iteration finished, facilitating garbage collection at an
    appropriate time.

    If unable to properly open file, catch the exception, log it, and
    return an empty generator, so downstream code continues to run.

    :var handle: File handle within generator.
    :vartype handle: collections.Iterable(object)
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
        self.handle = self.get_handle(file_path, binary=binary)

    def get_handle(self, file_path, binary=False):
        """Determine if file is on S3 or local and route accordingly.

        :param file_path: The path to the file to open.
        :type file_path: str
        :param binary: Whether to open the file in text or binary mode.
            Default is text mode.
        :type binary: bool
        :returns: File handle generator (empty if file not opened).
        :rtype: collections.Iterable[object]
        """
        s3_bucket, s3_key = self.get_s3_parameters(file_path)
        if s3_bucket and s3_key:
            return self.stream_s3_file(s3_bucket, s3_key)
        else:
            return self.open_local_file(file_path, binary=binary)

    def open_local_file(self, file_path, binary=False):
        """Open local file and return handle within generator.

        :param file_path: The path to the file to open.
        :type file_path: str
        :param binary: Whether to open the file in text or binary mode.
            Default is text mode.
        :type binary: bool
        :returns: File handle generator (empty if file not opened).
        :rtype: collections.Iterable[object]
        """
        if file_path.endswith(self.GZIP_EXTENSION):
            open_function = gzip.open
        else:
            open_function = open
        try:
            if binary:
                with open_function(file_path, mode="rb") as file_handle:
                    yield file_handle
            else:
                with open_function(file_path, mode="rt", encoding="utf-8-sig") as file_handle:
                    yield file_handle
        except (FileNotFoundError, OSError):
            log.exception("Could not open file: %s" % file_path)

    def get_s3_parameters(self, file_path):
        """Check if file is on AWS S3.

        Looking for either S3 URI or object URL.

        :param file_path: The path to the file to open.
        :type file_path: str
        :returns: Names of bucket and key, if found.
        :rtype: (str or None, str or None)
        """
        bucket = None
        key = None
        if (
            file_path.startswith(S3_FILE_URI_SCHEME)
            or S3_FILE_URL_HOST_NAME in file_path
        ):
            try:
                parsed_file_path = urlparse(file_path)
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
                "File: %s\n" % (bucket, key)
            )
        except s3_client.exceptions.ClientError:
            log.exception(
                "Could not open a file on S3.\n"
                "Bucket: %s\n"
                "File: %s\n" % (bucket, key)
            )
