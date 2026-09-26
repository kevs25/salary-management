from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.core.dependencies import BandServiceDep
from app.schemas.band import BandCreate, BandOut, BandQuery, BandUpdate
from app.schemas.common import ErrorResponse, Page

router = APIRouter(prefix="/bands", tags=["bands"])

_NOT_FOUND = {404: {"model": ErrorResponse}}
_WRITE_ERRORS = {409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}


@router.get("")
def list_bands(query: Annotated[BandQuery, Query()], service: BandServiceDep) -> Page[BandOut]:
    return service.list_bands(query)


@router.get("/{band_id}", responses=_NOT_FOUND)
def get_band(band_id: int, service: BandServiceDep) -> BandOut:
    return service.get_band(band_id)


@router.post("", status_code=status.HTTP_201_CREATED, responses=_WRITE_ERRORS)
def create_band(payload: BandCreate, service: BandServiceDep) -> BandOut:
    return service.create_band(payload)


@router.patch("/{band_id}", responses=_NOT_FOUND | _WRITE_ERRORS)
def update_band(band_id: int, payload: BandUpdate, service: BandServiceDep) -> BandOut:
    return service.update_band(band_id, payload)


@router.delete(
    "/{band_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND | {409: {"model": ErrorResponse}},
)
def delete_band(band_id: int, service: BandServiceDep) -> Response:
    """Only bands no salary record was ever priced against can be deleted."""
    service.delete_band(band_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
