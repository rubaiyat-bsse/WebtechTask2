from typing import Annotated

from fastapi import Depends, Request

from app.services.book_service import BookService
from app.services.member_service import MemberService


def get_book_service(request: Request) -> BookService:
    return request.app.state.book_service


def get_member_service(request: Request) -> MemberService:
    return request.app.state.member_service


BookServiceDependency = Annotated[BookService, Depends(get_book_service)]
MemberServiceDependency = Annotated[MemberService, Depends(get_member_service)]
