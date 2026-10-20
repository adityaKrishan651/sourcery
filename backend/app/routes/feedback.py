import sqlite3
from pathlib import Path

from fastapi import APIRouter

from .. import schemas

router = APIRouter()

DB_PATH = Path("feedback.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            sentence_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            verdict TEXT NOT NULL
        )
        """
    )
    return conn


@router.post("/feedback", response_model=schemas.FeedbackResponse)
def feedback(body: schemas.FeedbackRequest) -> schemas.FeedbackResponse:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO feedback (request_id, sentence_id, paper_id, verdict) VALUES (?, ?, ?, ?)",
            (str(body.request_id), body.sentence_id, body.paper_id, body.verdict.value),
        )
        conn.commit()
    finally:
        conn.close()
    return schemas.FeedbackResponse()