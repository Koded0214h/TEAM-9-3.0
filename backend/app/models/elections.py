import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Election(Base):
    __tablename__ = "elections"
    __table_args__ = (UniqueConstraint("workspace_id", "name", "election_date"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    election_type: Mapped[str] = mapped_column(String(40))
    election_date: Mapped[date] = mapped_column(Date)
    jurisdiction: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PoliticalParty(Base):
    __tablename__ = "political_parties"
    __table_args__ = (UniqueConstraint("workspace_id", "code"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    code: Mapped[str] = mapped_column(String(30))
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class Contest(Base):
    __tablename__ = "contests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    office: Mapped[str] = mapped_column(String(60))
    form_type: Mapped[str] = mapped_column(String(10))
    geography_level: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="draft")


class Candidate(Base):
    __tablename__ = "candidates"
    __table_args__ = (UniqueConstraint("contest_id", "party_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contests.id", ondelete="CASCADE"), index=True
    )
    party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("political_parties.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    ballot_code: Mapped[str] = mapped_column(String(30))


class ElectionCoverage(Base):
    __tablename__ = "election_coverage"
    __table_args__ = (UniqueConstraint("election_id", "geography_node_id"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id", ondelete="CASCADE"), index=True
    )
    geography_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("geography_nodes.id", ondelete="CASCADE"), index=True
    )
