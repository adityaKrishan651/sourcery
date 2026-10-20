from fastapi import APIRouter

from .. import mock_data, schemas

router = APIRouter()


@router.post("/analyze", response_model=schemas.AnalyzeResponse)
def analyze(request: schemas.AnalyzeRequest) -> schemas.AnalyzeResponse:
    # Mock phase: ignore the request, return the canned fixture.
    return mock_data.MOCK_RESPONSE