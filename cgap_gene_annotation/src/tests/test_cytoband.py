import io
import pytest

from unittest import mock

from .. import constants
from ..cytoband import get_cytoband_locations, add_cytoband_field


CYTOBAND_FILE_CONTENTS = "\n".join(
    [
        "\t".join(["chr1", "0", "2300000", "p36.33", "gneg"]),
        "\t".join(["chr1", "2300000", "5300000", "p36.34", "gpos25"]),
        "\t".join(["chr10_GL383545v1_alt", "0", "179254", "", "gneg"]),
        "\t".join(["chrX", "0", "4400000", "p22.33", "gneg"]),
    ]
)
EXPECTED_LOCATIONS = {
    "chr1": [(0, 2300000, "p36.33"), (2300000, 5300000, "p36.34")],
    "chrX": [(0, 4400000, "p22.33")],
}
PREFIX = "foo"
CHROMOSOME = "chr"
START = "start"
END = "end"
POSITION_INDEX = 0


def make_cytoband_metadata(
    chromosome=CHROMOSOME, start=START, end=END, position_index=POSITION_INDEX
):
    """"""
    return {
        constants.CHROMOSOME: chromosome,
        constants.START: start,
        constants.END: end,
        constants.POSITION_INDEX: position_index,
    }


def make_cytoband_record(
    prefix=PREFIX,
    chromosome="1",
    start="0",
    end="1000000",
    position_index=POSITION_INDEX,
):
    """"""
    return {
        prefix: {
            CHROMOSOME: chromosome,
            START: start,
            END: end,
            POSITION_INDEX: position_index,
        }
    }


@pytest.mark.parametrize(
    "reference_contents,expected",
    [
        ("", {}),
        (CYTOBAND_FILE_CONTENTS, EXPECTED_LOCATIONS),
    ],
)
def test_get_cytoband_locations(reference_contents, expected):
    """"""
    with mock.patch(
        "cgap_gene_annotation.src.parsers.FileHandler.get_handle",
        return_value=[io.StringIO(reference_contents)],
    ):
        result = get_cytoband_locations("foo/bar")
        assert result == expected


@pytest.mark.parametrize(
    "record,prefix,cytoband_metadata,expected",
    [
        ({}, PREFIX, make_cytoband_metadata(), {}),
        (
            make_cytoband_record(),
            PREFIX,
            make_cytoband_metadata(),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33"]},
                **make_cytoband_record(),
            },
        ),
        (
            make_cytoband_record(),
            "fu",
            make_cytoband_metadata(),
            make_cytoband_record(),
        ),
        (
            make_cytoband_record(chromosome="chr1"),
            PREFIX,
            make_cytoband_metadata(),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33"]},
                **make_cytoband_record(chromosome="chr1"),
            },
        ),
        (
            make_cytoband_record(chromosome="chromosome1"),
            PREFIX,
            make_cytoband_metadata(),
            make_cytoband_record(chromosome="chromosome1"),
        ),
        (
            make_cytoband_record(chromosome="2"),
            PREFIX,
            make_cytoband_metadata(),
            make_cytoband_record(chromosome="2"),
        ),
        (
            make_cytoband_record(end="10000000"),
            PREFIX,
            make_cytoband_metadata(),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33", "p36.34"]},
                **make_cytoband_record(end="10000000"),
            },
        ),
        (
            make_cytoband_record(end="2300000"),
            PREFIX,
            make_cytoband_metadata(),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33"]},
                **make_cytoband_record(end="2300000"),
            },
        ),
        (
            make_cytoband_record(),
            PREFIX,
            make_cytoband_metadata(chromosome="fu"),
            make_cytoband_record(),
        ),
        (
            make_cytoband_record(),
            PREFIX,
            make_cytoband_metadata(start="fu"),
            make_cytoband_record(),
        ),
        (
            make_cytoband_record(),
            PREFIX,
            make_cytoband_metadata(end="fu"),
            make_cytoband_record(),
        ),
        (
            make_cytoband_record(end="2300001"),
            PREFIX,
            make_cytoband_metadata(position_index=0),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33", "p36.34"]},
                **make_cytoband_record(end="2300001"),
            },
        ),
        (
            make_cytoband_record(start="1", end="2300001"),
            PREFIX,
            make_cytoband_metadata(position_index=1),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33"]},
                **make_cytoband_record(start="1", end="2300001"),
            },
        ),
        (
            make_cytoband_record(start="2300000", end="3300000"),
            PREFIX,
            make_cytoband_metadata(position_index=0),
            {
                constants.CYTOBAND: {PREFIX: ["p36.34"]},
                **make_cytoband_record(start="2300000", end="3300000"),
            },
        ),
        (
            make_cytoband_record(start="2300000", end="3300000"),
            PREFIX,
            make_cytoband_metadata(position_index=1),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33", "p36.34"]},
                **make_cytoband_record(start="2300000", end="3300000"),
            },
        ),
        (
            make_cytoband_record(start={"bar": "0"}),
            PREFIX,
            make_cytoband_metadata(start=(constants.START + ".bar")),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33"]},
                **make_cytoband_record(start={"bar": "0"}),
            },
        ),
        (
            make_cytoband_record(end={"bar": "10000"}),
            PREFIX,
            make_cytoband_metadata(end=(constants.END + ".bar")),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33"]},
                **make_cytoband_record(end={"bar": "10000"}),
            },
        ),
        (
            make_cytoband_record(start="fu"),
            PREFIX,
            make_cytoband_metadata(),
            make_cytoband_record(start="fu"),
        ),
        (
            make_cytoband_record(end="fu"),
            PREFIX,
            make_cytoband_metadata(),
            make_cytoband_record(end="fu"),
        ),
        (
            make_cytoband_record(start=["0"]),
            PREFIX,
            make_cytoband_metadata(),
            {
                constants.CYTOBAND: {PREFIX: ["p36.33"]},
                **make_cytoband_record(start=["0"]),
            },
        ),
        (
            make_cytoband_record(start=["0", "1"]),
            PREFIX,
            make_cytoband_metadata(),
            make_cytoband_record(start=["0", "1"]),
        ),
    ],
)
def test_add_cytoband_field(record, prefix, cytoband_metadata, expected):
    """Test"""
    add_cytoband_field(record, prefix, cytoband_metadata, EXPECTED_LOCATIONS)
    assert record == expected
