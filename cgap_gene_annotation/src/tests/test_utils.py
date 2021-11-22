import io
from types import GeneratorType
from unittest import mock

import pytest

from .. import utils


MOCK_FILE = io.StringIO("something")


class TestOpenFile:

    @pytest.mark.parametrize(
        "file_path,binary,side_effect",
        [
            ("foo/bar", False, None),
            ("foo/bar", True, None),
            ("foo/bar", False, FileNotFoundError),
        ]
    )
    def test_open_file_local_uncompressed(self, file_path, binary, side_effect):
        """"""
        mock_file = io.StringIO("something")
        expected = [mock_file]
        if side_effect:
            expected = []
        mode = "rt"
        if binary:
            mode = "rb"
        with mock.patch(
            "cgap_gene_annotation.src.utils.open", return_value=mock_file, create=True,
            side_effect=side_effect
        ) as mocked_file:
            result = utils.open_file(file_path, binary=binary)
            assert isinstance(result, GeneratorType)
            result = list(result)
            assert result == expected
            mocked_file.assert_called_once_with(file_path, mode=mode)

    @pytest.mark.parametrize(
        "file_path,binary,side_effect",
        [
            ("foo/bar.gz", False, None),
            ("foo/bar.gz", True, None),
            ("foo/bar.gz", False, FileNotFoundError),
            ("foo/bar.gz", False, OSError),

        ]
    )
    def test_open_file_local_compressed(self, file_path, binary, side_effect):
        """"""
        mock_file = io.StringIO("something")
        expected = [mock_file]
        if side_effect:
            expected = []
        mode = "rt"
        if binary:
            mode = "rb"
        with mock.patch(
            "cgap_gene_annotation.src.utils.gzip.open", return_value=mock_file, create=True,
            side_effect=side_effect
        ) as mocked_file:
            result = utils.open_file(file_path, binary=binary)
            assert isinstance(result, GeneratorType)
            result = list(result)
            assert result == expected
            mocked_file.assert_called_once_with(file_path, mode=mode)
