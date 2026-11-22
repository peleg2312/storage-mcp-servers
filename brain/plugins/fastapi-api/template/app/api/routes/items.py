from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Item
from app.schemas import ItemIn, ItemOut, ItemPage

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=ItemPage)
def list_items(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
               session: Session = Depends(get_session)) -> ItemPage:
    total = session.scalar(select(func.count()).select_from(Item)) or 0
    rows = session.scalars(select(Item).order_by(Item.id).limit(limit).offset(offset)).all()
    return ItemPage(items=[ItemOut.model_validate(r) for r in rows], total=total, limit=limit, offset=offset)


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(body: ItemIn, session: Session = Depends(get_session)) -> Item:
    item = Item(**body.model_dump())
    session.add(item)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(status_code=409, detail=f"an item named {body.name!r} exists") from e
    return item


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, session: Session = Depends(get_session)) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, session: Session = Depends(get_session)) -> Response:
    item = session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
