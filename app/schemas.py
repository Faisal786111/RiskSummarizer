"""Request and response models for the API."""
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RiskSummary(BaseModel):
    """The structured answer we ask the model to produce."""

    summary: str = Field(description="A concise summary of the document in at most 3 sentences.")
    risk_level: RiskLevel = Field(description="Overall risk level found in the document.")
    reasons: list[str] = Field(description="Short reasons that justify the risk level.")


class SummarizeRequest(BaseModel):
    """Provide exactly one of `text` or `url`."""

    text: Optional[str] = Field(default=None, description="Plain text to analyse.")
    url: Optional[str] = Field(default=None, description="Public http(s) page to fetch and analyse.")

    @model_validator(mode="after")
    def exactly_one_source(self):
        has_text = bool(self.text and self.text.strip())
        has_url = bool(self.url and self.url.strip())
        if has_text == has_url:
            raise ValueError("Provide exactly one of 'text' or 'url'.")
        return self


class SummarizeResponse(BaseModel):
    source: Literal["text", "url"]
    characters_analysed: int
    result: RiskSummary
