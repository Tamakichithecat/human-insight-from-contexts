from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

SAFE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
CONTENT_HASH_PATTERN = r"^[a-f0-9]{64}$"

SafeId = Annotated[str, Field(min_length=1, max_length=128, pattern=SAFE_ID_PATTERN)]
ContentHash = Annotated[str, Field(pattern=CONTENT_HASH_PATTERN)]


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class GeneratorInfo(StrictBaseModel):
    model_id: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    pipeline_version: str = Field(min_length=1)


class SourceRef(StrictBaseModel):
    source_id: SafeId
    content_hash: ContentHash
