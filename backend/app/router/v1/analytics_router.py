from typing import Annotated

from fastapi import APIRouter, Query

from app.core.dependencies import AnalyticsServiceDep
from app.schemas.analytics import (
    AnalyticsFilter,
    BandComplianceQuery,
    Breakdown,
    BreakdownQuery,
    CompaRatioDistribution,
    CompaRatioQuery,
    OutOfBandEmployee,
    PaySummary,
)
from app.schemas.common import Page

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
def pay_summary(
    filters: Annotated[AnalyticsFilter, Query()], service: AnalyticsServiceDep
) -> PaySummary:
    """Headcount, payroll cost, base pay statistics, band compliance, median compa-ratio."""
    return service.summary(filters)


@router.get("/breakdown")
def pay_breakdown(
    query: Annotated[BreakdownQuery, Query()], service: AnalyticsServiceDep
) -> Breakdown:
    """The summary figures per department, country, level or role."""
    return service.breakdown(query)


@router.get("/compa-ratio")
def compa_ratio_distribution(
    query: Annotated[CompaRatioQuery, Query()], service: AnalyticsServiceDep
) -> CompaRatioDistribution:
    """Distribution of base pay / band mid per group: quartiles and a histogram."""
    return service.compa_ratio_distribution(query)


@router.get("/band-compliance")
def band_compliance(
    query: Annotated[BandComplianceQuery, Query()], service: AnalyticsServiceDep
) -> Page[OutOfBandEmployee]:
    """Employees paid below their band minimum or above its maximum, most severe first."""
    return service.band_compliance(query)
