import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_workspace_roles
from app.core.errors import AppError
from app.db.session import get_db
from app.models.elections import Candidate, Contest, Election, ElectionCoverage, PoliticalParty
from app.models.organisation import GeographyNode, Membership
from app.schemas.elections import (
    CandidateCreate,
    CandidateResponse,
    ContestCreate,
    ContestResponse,
    CoverageCreate,
    ElectionCreate,
    ElectionResponse,
    PartyCreate,
    PartyResponse,
)

router = APIRouter(prefix="/workspaces/{workspace_id}")
admin = Depends(require_workspace_roles("party_admin", "operations", require_mfa=True))
viewer = require_workspace_roles(
    "party_admin", "operations", "legal_compliance", "collation_officer"
)


def get_election(db: Session, workspace_id: uuid.UUID, election_id: uuid.UUID) -> Election:
    election = db.get(Election, election_id)
    if election is None or election.workspace_id != workspace_id:
        raise AppError("election_not_found", "Election was not found", 404)
    return election


@router.post("/elections", response_model=ElectionResponse, status_code=201, dependencies=[admin])
def create_election(
    workspace_id: uuid.UUID,
    payload: ElectionCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Election:
    election = Election(workspace_id=workspace_id, created_by_id=user.id, **payload.model_dump())
    db.add(election)
    db.commit()
    db.refresh(election)
    return election


@router.get("/elections", response_model=list[ElectionResponse])
def list_elections(
    workspace_id: uuid.UUID,
    _: Annotated[Membership, Depends(viewer)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Election]:
    return list(db.scalars(select(Election).where(Election.workspace_id == workspace_id)).all())


@router.post("/parties", response_model=PartyResponse, status_code=201, dependencies=[admin])
def create_party(
    workspace_id: uuid.UUID, payload: PartyCreate, db: Annotated[Session, Depends(get_db)]
) -> PoliticalParty:
    party = PoliticalParty(workspace_id=workspace_id, **payload.model_dump())
    db.add(party)
    db.commit()
    db.refresh(party)
    return party


@router.post(
    "/elections/{election_id}/contests",
    response_model=ContestResponse,
    status_code=201,
    dependencies=[admin],
)
def create_contest(
    workspace_id: uuid.UUID,
    election_id: uuid.UUID,
    payload: ContestCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Contest:
    get_election(db, workspace_id, election_id)
    contest = Contest(election_id=election_id, **payload.model_dump())
    db.add(contest)
    db.commit()
    db.refresh(contest)
    return contest


@router.post(
    "/elections/{election_id}/contests/{contest_id}/candidates",
    response_model=CandidateResponse,
    status_code=201,
    dependencies=[admin],
)
def create_candidate(
    workspace_id: uuid.UUID,
    election_id: uuid.UUID,
    contest_id: uuid.UUID,
    payload: CandidateCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Candidate:
    get_election(db, workspace_id, election_id)
    contest = db.get(Contest, contest_id)
    party = db.get(PoliticalParty, payload.party_id)
    if (
        contest is None
        or contest.election_id != election_id
        or party is None
        or party.workspace_id != workspace_id
    ):
        raise AppError(
            "invalid_candidate", "Contest and party must belong to this workspace election", 422
        )
    candidate = Candidate(contest_id=contest_id, **payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.put("/elections/{election_id}/coverage", status_code=204, dependencies=[admin])
def set_coverage(
    workspace_id: uuid.UUID,
    election_id: uuid.UUID,
    payload: CoverageCreate,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    get_election(db, workspace_id, election_id)
    nodes = db.scalars(
        select(GeographyNode).where(
            GeographyNode.id.in_(payload.geography_node_ids),
            GeographyNode.workspace_id == workspace_id,
        )
    ).all()
    if len(nodes) != len(set(payload.geography_node_ids)):
        raise AppError("invalid_coverage", "Every geography node must belong to the workspace", 422)
    db.query(ElectionCoverage).filter(ElectionCoverage.election_id == election_id).delete()
    db.add_all(
        [ElectionCoverage(election_id=election_id, geography_node_id=node.id) for node in nodes]
    )
    db.commit()


@router.post(
    "/elections/{election_id}/activate", response_model=ElectionResponse, dependencies=[admin]
)
def activate_election(
    workspace_id: uuid.UUID, election_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> Election:
    election = get_election(db, workspace_id, election_id)
    contest_count = (
        db.scalar(
            select(func.count()).select_from(Contest).where(Contest.election_id == election_id)
        )
        or 0
    )
    candidate_count = (
        db.scalar(
            select(func.count())
            .select_from(Candidate)
            .join(Contest)
            .where(Contest.election_id == election_id)
        )
        or 0
    )
    coverage_count = (
        db.scalar(
            select(func.count())
            .select_from(ElectionCoverage)
            .where(ElectionCoverage.election_id == election_id)
        )
        or 0
    )
    if not contest_count or candidate_count < 2 or not coverage_count:
        raise AppError(
            "election_not_ready",
            "Activation requires coverage, a contest, and at least two candidates",
            409,
        )
    election.status = "active"
    db.commit()
    db.refresh(election)
    return election
