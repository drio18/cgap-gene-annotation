import logging

from . import constants
from .parsers import TSVParser
from .utils import nested_getter


log = logging.getLogger(__name__)

GIE_STAIN = "gieStain"
UCSC_CYTOBAND_HEADER = [
    constants.CHROMOSOME,
    constants.START,
    constants.END,
    constants.CYTOBAND,
    GIE_STAIN,
]
CHROMOSOME_START = "chr"


def get_cytoband_locations(reference_file_path):
    """Create cytoband locations from given reference file.

    Reference file MUST be in UCSC format (TSV with header above).

    :param reference_file_path: Path to UCSC cytoband file.
    :type reference_file_path: str
    :returns: Cytoband locations per chromosome.
    :rtype: dict
    """
    cytoband_locations = {}
    parser = TSVParser(reference_file_path, header=UCSC_CYTOBAND_HEADER)
    records = parser.get_records()
    for record in records:
        chromosome = record.get(constants.CHROMOSOME)
        start = record.get(constants.START)
        end = record.get(constants.END)
        cytoband = record.get(constants.CYTOBAND)
        if chromosome and start and end and cytoband:
            start = int(start)
            end = int(end)
            chromosome_stripped = chromosome.replace(CHROMOSOME_START, "")
            cytoband_record = (start, end, chromosome_stripped + cytoband)
            chromosome_locations = cytoband_locations.get(chromosome)
            if not chromosome_locations:
                cytoband_locations[chromosome] = [cytoband_record]
            else:
                chromosome_locations.append(cytoband_record)
    return cytoband_locations


def add_cytoband_field(record, prefix, cytoband_metadata, reference_locations):
    """Update/create cytoband entry in record if cytoband match found.

    Note: reference_locations input generated from
    get_cytoband_locations().

    :param record: Annotation of interest.
    :type record: dict
    :param prefix: Prefix for annotation source from which cytoband info
        is being parsed.
    :type prefix: str
    :param cytoband_metadata: Metadata provided in annotation creation
        according to schema
    :type cytoband_metadata: dict
    :param reference_locations: Cytoband positions generated from given
        UCSC reference file.
    :type: reference_locations: dict
    """
    cytobands = []
    prefix_record = record.get(prefix)
    chromosome_field = cytoband_metadata.get(constants.CHROMOSOME)
    start_field = cytoband_metadata.get(constants.START)
    end_field = cytoband_metadata.get(constants.END)
    position_index = cytoband_metadata.get(constants.POSITION_INDEX)
    chromosome = nested_getter(prefix_record, chromosome_field, string_return=True)
    if chromosome and not chromosome.startswith(CHROMOSOME_START):
        chromosome = CHROMOSOME_START + chromosome
    start = nested_getter(prefix_record, start_field, string_return=True)
    try:
        start = int(start) - position_index
    except (ValueError, TypeError):
        log.error("Unable to convert start value to integer: %s", start)
        start = None
    end = nested_getter(prefix_record, end_field, string_return=True)
    try:
        end = int(end) - position_index
    except (ValueError, TypeError):
        log.error("Unable to convert end value to integer: %s", end)
        end = None
    if prefix_record and chromosome and start is not None and end is not None:
        chromosome_cytobands = reference_locations.get(chromosome, [])
        if not chromosome_cytobands:
            log.debug(
                "Chromosome (%s) not found in cytobands from reference file for prefix"
                " (%s)",
                chromosome,
                prefix,
            )
        start_found = False
        for cytoband_start, cytoband_end, cytoband_name in chromosome_cytobands:
            if not start_found and cytoband_start <= start < cytoband_end:
                cytobands.append(cytoband_name)
                start_found = True
            elif start_found and cytoband_start < end:
                cytobands.append(cytoband_name)
            elif start_found and end <= cytoband_start:
                break
    else:
        log.debug(
            "Could not add cytoband information due to missing information for record:"
            " %s",
            record,
        )
    if cytobands:
        existing_cytoband_object = record.get(constants.CYTOBAND)
        if existing_cytoband_object:
            existing_cytoband_object[prefix] = cytobands
        else:
            record[constants.CYTOBAND] = {prefix: cytobands}
