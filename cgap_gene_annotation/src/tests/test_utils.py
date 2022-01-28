import gzip
import io
import os
from types import GeneratorType
from unittest import mock

import boto3
import moto
import pytest

from .. import utils


FILE_LINES = ["Testing", "OneTwo"]
FILE_CONTENTS = "\n".join(FILE_LINES)
S3_BUCKET = "test_bucket"
S3_KEY = "test_file.txt"
S3_KEY_GZ = "test_file.gz"


@pytest.mark.parametrize(
    "item,field,value,delete,expected",
    [
        ({}, "foo", None, False, {}),
        ({}, "foo", "bar", False, {"foo": "bar"}),
        ({}, "foo.fi", "bar", False, {"foo": {"fi": "bar"}}),
        ({"foo": "bar"}, "foo", None, False, {"foo": "bar"}),
        ({"foo": "bar"}, "foo", "bur", False, {"foo": "bur"}),
        ({"foo": "bar"}, "fu", "bur", False, {"foo": "bar", "fu": "bur"}),
        ({"foo": "bar"}, "foo", None, True, {}),
        ({"foo": {"fu": "bar"}}, "foo.fu", None, False, {"foo": {"fu": "bar"}}),
        ({"foo": {"fu": "bar"}}, "foo.fu", "bur", False, {"foo": {"fu": "bur"}}),
        ({"foo": {"fu": "bar"}}, "foo.fu", "bur", True, {"foo": {}}),
        ({"foo": {"fu": "bar"}}, "foo.fi", "bur", False, {"foo": {"fu": "bar", "fi":
            "bur"}}),
        ({"foo": {"fu": "bar"}}, "foo.fu", None, True, {"foo": {}}),
        ({"foo.fu": "bar"}, "foo.fu", "bur", False, {"foo.fu": "bur"}),
        ({"foo.fu": "bar"}, "foo.fu", None, True, {}),
    ]
)
def test_nested_setter(item, field, value, delete, expected):
    """Test setting/deleting values in potentially nested dict."""
    utils.nested_setter(item, field, value=value, delete_field=delete)
    assert item == expected


@pytest.mark.parametrize(
    "dict_item,field_to_get,string_return,expected",
    [
        ({}, "foo", False, []),
        ({}, "foo", True, None),
        ({}, "foo.bar", False, []),
        ({"foo": {"bar": "1"}}, "foo", False, {"bar": "1"}),
        ({"foo": {"bar": "1"}}, "foo", True, {"bar": "1"}),
        ({"foo": {"bar": "1"}}, "foo.bar", False, ["1"]),
        ({"foo": {"bar": "1"}}, "foo.bar", True, "1"),
        ({"foo": {"bar": ["1"]}}, "foo.bar", False, ["1"]),
        ({"foo": {"bar": ["1"]}}, "foo.bar", True, "1"),
        ({"foo": {"bar": ["1", "1"]}}, "foo.bar", False, ["1", "1"]),
        ({"foo": {"bar": ["1", "1"]}}, "foo.bar", True, ["1", "1"]),
        ({"foo": {"bar": ["1", "2"]}}, "foo.bar", False, ["1", "2"]),
        ({"foo": {"bar": ["1", "2"]}}, "foo.bar", True, ["1", "2"]),
        ({"foo": [{"bar": "1"}, {"bar": "2"}]}, "foo.bar", False, ["1", "2"]),
        ({"foo": [{"bar": "1"}, {"bar": "2"}]}, "foo.bar", True, ["1", "2"]),
        ({"foo": [{"bar": "1"}, {"bar": "1"}]}, "foo.bar", False, ["1"]),
        ({"foo": [{"bar": "1"}, {"bar": "1"}]}, "foo.bar", True, "1"),
        ({"foo": {"bar": {"something"}}}, "foo.bar", False, {"something"}),
        ({"foo": {"bar": 1}}, "foo.bar", False, 1),
        ({"foo": {"foo": {"bar": "something"}}}, "foo.bar", False, []),
    ],
)
def test_nested_getter(dict_item, field_to_get, string_return, expected):
    """Test nested fields retrieval from the given dictionary."""
    result = utils.nested_getter(dict_item, field_to_get, string_return=string_return)
    if isinstance(expected, list):
        assert isinstance(result, list)
        assert len(expected) == len(result)
        result = set(result)
        expected = set(expected)
    assert result == expected


@pytest.fixture
def file_content():
    """File-like object for mocked files."""
    return io.StringIO(FILE_CONTENTS)


@pytest.fixture
def aws_credentials():
    """Mocked credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def s3_client(aws_credentials):
    """Mocked S3 client via moto."""
    with moto.mock_s3():
        yield boto3.client("s3")


@pytest.fixture
def s3_files(s3_client):
    """Mocked S3 files via moto for testing streaming."""
    s3_client.create_bucket(Bucket=S3_BUCKET)
    s3_client.put_object(Bucket=S3_BUCKET, Key=S3_KEY, Body=FILE_CONTENTS)
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=S3_KEY_GZ,
        Body=gzip.compress(FILE_CONTENTS.encode("utf-8")),
    )


class TestFileHandler:
    @pytest.mark.parametrize(
        "file_path,binary,side_effect",
        [
            ("foo/bar", False, None),
            ("foo/bar", True, None),
            ("foo/bar", False, FileNotFoundError),
        ],
    )
    def test_open_file_local_uncompressed(
        self, file_path, binary, side_effect, file_content
    ):
        """Test opening local uncompressed file.

        Mocked file contents fixed.
        """
        mode = "rt"
        encoding = "utf-8-sig"
        if binary:
            mode = "rb"
            encoding = "utf-8"
        with mock.patch(
            "cgap_gene_annotation.src.utils.open",
            return_value=file_content,
            create=True,
            side_effect=side_effect,
        ) as mocked_file:
            result = utils.FileHandler(file_path, binary=binary).open_local_file()
            assert isinstance(result, GeneratorType)
            result = list(result)
            if side_effect:
                assert result == []
            else:
                assert result == [file_content]
            mocked_file.assert_called_once_with(file_path, mode=mode, encoding=encoding)

    @pytest.mark.parametrize(
        "file_path,binary,side_effect",
        [
            ("foo/bar.gz", False, None),
            ("foo/bar.gz", True, None),
            ("foo/bar.gz", False, FileNotFoundError),
            ("foo/bar.gz", False, OSError),
        ],
    )
    def test_open_file_local_compressed(
        self, file_path, binary, side_effect, file_content
    ):
        """Test opening local gzipped file.

        Mocked file contents fixed.
        """
        mode = "rt"
        encoding = "utf-8-sig"
        if binary:
            mode = "rb"
            encoding = "utf-8"
        with mock.patch(
            "cgap_gene_annotation.src.utils.gzip.open",
            return_value=file_content,
            create=True,
            side_effect=side_effect,
        ) as mocked_file:
            result = utils.FileHandler(file_path, binary=binary).open_local_file()
            assert isinstance(result, GeneratorType)
            result = list(result)
            if side_effect:
                assert result == []
            else:
                assert result == [file_content]
            mocked_file.assert_called_once_with(file_path, mode=mode, encoding=encoding)

    @pytest.mark.parametrize(
        "file_path,expected",
        [
            ("", (None, None)),
            ("foo/bar", (None, None)),
            (utils.S3_FILE_URI_SCHEME + "foo.bar", (None, None)),
            (utils.S3_FILE_URI_SCHEME + "//bucket/key", (None, None)),
            (utils.S3_FILE_URI_SCHEME + "://bucket/key", ("bucket", "key")),
            ("bucket." + utils.S3_FILE_URL_HOST_NAME + "/key", (None, None)),
            (
                "https://bucket." + utils.S3_FILE_URL_HOST_NAME + "/key",
                ("bucket", "key"),
            ),
        ],
    )
    def test_get_s3_parameters(self, file_path, expected):
        """Test retrieval of bucket and key from S3 file string."""
        assert utils.FileHandler(file_path).get_s3_parameters() == expected

    @pytest.mark.parametrize(
        "bucket,key,expected_lines",
        [
            ("Not_present", "Not_present", []),
            (S3_BUCKET, "Not_present", []),
            ("Not_present", S3_KEY, []),
            (S3_BUCKET, S3_KEY, FILE_LINES),
            (S3_BUCKET, S3_KEY_GZ, FILE_LINES),
        ],
    )
    def test_stream_s3_file(self, bucket, key, expected_lines, s3_files):
        """Test streaming of contents from S3 file.

        Utilizes mocked S3 system of moto established in fixtures
        above.
        """
        result = utils.FileHandler("").stream_s3_file(bucket, key)
        assert isinstance(result, GeneratorType)
        file_lines = []
        for handle in result:
            for line in handle:
                file_lines.append(line.strip())
        assert file_lines == expected_lines
