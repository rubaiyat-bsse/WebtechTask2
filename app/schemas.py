"""HTTP input/output contracts; domain rules still run in services."""

from pydantic import BaseModel, ConfigDict, Field


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class BookWrite(InputModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    total_copies: int = Field(ge=0, examples=[2])


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    total_copies: int
    available_copies: int


class MemberWrite(InputModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254, examples=["reader@example.com"])


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    requestId: str
    errors: list[dict[str, str]] | None = None


# Keep Swagger's error media type consistent with the actual handlers.
ERROR_RESPONSES = {
    status: {
        "description": description,
        "content": {"application/problem+json": {"schema": Problem.model_json_schema()}},
    }
    for status, description in (
        (404, "Resource not found"),
        (409, "Request conflicts with current state"),
        (422, "Validation failed"),
        (500, "Internal server error"),
    )
}
