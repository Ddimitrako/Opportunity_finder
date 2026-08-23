import pytest
from pydantic import ValidationError

from app.models import ActivityRequest, NeedPatternRequest, Opportunity, ProcurementSearchRequest


def opportunity(index: int) -> Opportunity:
    return Opportunity(
        id=f"demo-{index}",
        source="demo",
        source_label="Demo",
        title=f"Opportunity {index}",
        summary="Bounded request test",
    )


def test_source_lists_reject_duplicates() -> None:
    with pytest.raises(ValidationError, match="sources must contain unique values"):
        ProcurementSearchRequest(sources=["khmdhs", "khmdhs"])
    with pytest.raises(ValidationError, match="sources must contain unique values"):
        ActivityRequest(sources=["ted", "ted"])


def test_heavy_opportunity_collections_are_bounded() -> None:
    NeedPatternRequest(opportunities=[opportunity(index) for index in range(100)])
    with pytest.raises(ValidationError):
        NeedPatternRequest(opportunities=[opportunity(index) for index in range(101)])
