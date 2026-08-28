from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.url import URL
from app.schemas.url import URLCreateRequest, URLResponse
from app.services import base62

router = APIRouter()


@router.post(
    "/shorten",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
)
def shorten(payload: URLCreateRequest, db: Session = Depends(get_db)) -> URL:
    original_url = str(payload.original_url)
    now = datetime.now(timezone.utc)

    if payload.custom_alias is not None:
        url = URL(
            short_code=payload.custom_alias,
            original_url=original_url,
            created_at=now,
        )
        db.add(url)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="alias already taken",
            )
        return url

    next_id = db.execute(text("SELECT nextval('urls_id_seq')")).scalar_one()
    url = URL(
        id=next_id,
        short_code=base62.encode(next_id),
        original_url=original_url,
        created_at=now,
    )
    db.add(url)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="short_code collision",
        )
    return url


@router.get("/{code}")
def resolve(code: str, db: Session = Depends(get_db)) -> RedirectResponse:
    url = db.execute(
        select(URL).where(URL.short_code == code)
    ).scalar_one_or_none()

    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if url.expires_at is not None and url.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="link expired")

    return RedirectResponse(url=url.original_url, status_code=status.HTTP_302_FOUND)
