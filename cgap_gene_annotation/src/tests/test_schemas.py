import jsonschema
import pytest

from .. import schemas

INVALID_SCHEMA = {
    "type": "object",
    "properties": {"foo": {"type": "string"}, "bar": {"type": "invalid_type"}},
}


@pytest.mark.parametrize(
    "schema,expect_error",
    [
        (schemas.ANNOTATION_SOURCE, False),
        (schemas.UPDATE_SCHEMA, False),
        (schemas.CREATE_SCHEMA, False),
        (INVALID_SCHEMA, True),
    ],
)
def test_schemas_are_valid(schema, expect_error):
    """Test schemas used for validating JSON input are themselves
    valid.
    """
    validator = jsonschema.Draft4Validator
    if expect_error:
        with pytest.raises(jsonschema.exceptions.SchemaError):
            validator.check_schema(schema)
    else:
        validator.check_schema(schema)
