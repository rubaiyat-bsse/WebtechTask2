from sqlite3 import Connection

from app.domain.member import Member


class MemberRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def add(self, member: Member) -> Member:
        cursor = self.connection.execute(
            "INSERT INTO members (name, email) VALUES (?, ?)", (member.name, member.email)
        )
        member.id = cursor.lastrowid
        return member

    def get(self, member_id: int) -> Member | None:
        row = self.connection.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        if row is None:
            return None
        return Member(**dict(row))

    def get_by_email(self, email: str) -> Member | None:
        row = self.connection.execute("SELECT * FROM members WHERE email = ?", (email,)).fetchone()
        if row is None:
            return None
        return Member(**dict(row))

    def list(self) -> list[Member]:
        rows = self.connection.execute("SELECT * FROM members ORDER BY id").fetchall()
        return [Member(**dict(row)) for row in rows]

    def save(self, member: Member) -> None:
        self.connection.execute(
            "UPDATE members SET name = ?, email = ? WHERE id = ?",
            (member.name, member.email, member.id),
        )

    def delete(self, member_id: int) -> None:
        self.connection.execute("DELETE FROM members WHERE id = ?", (member_id,))
