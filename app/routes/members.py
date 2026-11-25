from typing import Annotated

from fastapi import APIRouter, Path, Response

from app.dependencies import MemberServiceDependency
from app.schemas import ERROR_RESPONSES, MemberRead, MemberWrite

router = APIRouter(prefix="/members", tags=["Members"], responses=ERROR_RESPONSES)
MemberId = Annotated[int, Path(gt=0)]


@router.post("", response_model=MemberRead, status_code=201)
def create_member(payload: MemberWrite, response: Response, service: MemberServiceDependency):
    member = service.add_member(**payload.model_dump())
    response.headers["Location"] = f"/members/{member.id}"
    return member


@router.get("", response_model=list[MemberRead])
def list_members(service: MemberServiceDependency):
    return service.list_members()


@router.get("/{member_id}", response_model=MemberRead)
def get_member(member_id: MemberId, service: MemberServiceDependency):
    return service.get_member(member_id)


@router.put("/{member_id}", response_model=MemberRead)
def update_member(member_id: MemberId, payload: MemberWrite, service: MemberServiceDependency):
    return service.update_member(member_id, **payload.model_dump())


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: MemberId, service: MemberServiceDependency):
    service.delete_member(member_id)
    return Response(status_code=204)
