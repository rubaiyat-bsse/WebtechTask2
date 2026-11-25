from typing import Annotated

from fastapi import APIRouter, Path, Response

from app.dependencies import BookServiceDependency
from app.schemas import ERROR_RESPONSES, BookRead, BookWrite

router = APIRouter(prefix="/books", tags=["Books"], responses=ERROR_RESPONSES)
BookId = Annotated[int, Path(gt=0)]


@router.post("", response_model=BookRead, status_code=201)
def create_book(payload: BookWrite, response: Response, service: BookServiceDependency):
    book = service.add_book(**payload.model_dump())
    response.headers["Location"] = f"/books/{book.id}"
    return book


@router.get("", response_model=list[BookRead])
def list_books(service: BookServiceDependency):
    return service.list_books()


@router.get("/{book_id}", response_model=BookRead)
def get_book(book_id: BookId, service: BookServiceDependency):
    return service.get_book(book_id)


@router.put("/{book_id}", response_model=BookRead)
def update_book(book_id: BookId, payload: BookWrite, service: BookServiceDependency):
    return service.update_book(book_id, **payload.model_dump())


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: BookId, service: BookServiceDependency):
    service.delete_book(book_id)
    return Response(status_code=204)


@router.post("/{book_id}/borrow", response_model=BookRead)
def borrow_book(book_id: BookId, service: BookServiceDependency):
    return service.borrow_book(book_id)


@router.post("/{book_id}/return", response_model=BookRead)
def return_book(book_id: BookId, service: BookServiceDependency):
    return service.return_book(book_id)
