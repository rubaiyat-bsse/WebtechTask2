import logging

from app.domain.member import Member
from app.errors import Conflict, NotFound
from app.services.ports import MemberStore, UnitOfWork

log = logging.getLogger(__name__)


class MemberService:
    def __init__(self, unit_of_work: UnitOfWork):
        self.unit_of_work = unit_of_work

    @staticmethod
    def _require(repo: MemberStore, member_id: int) -> Member:
        member = repo.get(member_id)
        if member is None:
            raise NotFound(f"Member {member_id} does not exist")
        return member

    @staticmethod
    def _ensure_unique(repo: MemberStore, member: Member) -> None:
        existing = repo.get_by_email(member.email)
        if existing is not None and existing.id != member.id:
            raise Conflict("A member with this email already exists")

    def add_member(self, name: str, email: str) -> Member:
        member = Member(name, email)
        member.validate()
        with self.unit_of_work() as repos:
            self._ensure_unique(repos.members, member)
            saved = repos.members.add(member)
        log.info("member added id=%s", saved.id)
        return saved

    def get_member(self, member_id: int) -> Member:
        with self.unit_of_work() as repos:
            return self._require(repos.members, member_id)

    def list_members(self) -> list[Member]:
        with self.unit_of_work() as repos:
            return repos.members.list()

    def update_member(self, member_id: int, name: str, email: str) -> Member:
        with self.unit_of_work() as repos:
            self._require(repos.members, member_id)
            member = Member(name, email, member_id)
            member.validate()
            self._ensure_unique(repos.members, member)
            repos.members.save(member)
        log.info("member updated id=%s", member_id)
        return member

    def delete_member(self, member_id: int) -> None:
        with self.unit_of_work() as repos:
            self._require(repos.members, member_id)
            repos.members.delete(member_id)
        log.info("member deleted id=%s", member_id)
