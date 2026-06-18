from __future__ import annotations

from datetime import datetime

import strawberry
from pydantic import BaseModel, Field

from api.models import Candidate, Note, ProjectCandidate, SourcingProject, TaskRun
from api.sourcing import list_to_graphql


@strawberry.type
class NoteType:
    id: str
    title: str
    body: str
    summary: str | None
    summary_provider: str | None
    summary_updated_at: str | None
    created_at: str


@strawberry.type
class CurrentUserType:
    id: str
    email: str


@strawberry.type
class ViewerType:
    email: str


@strawberry.type
class TaskRunType:
    id: str
    task_name: str
    status: str
    progress_current: int
    progress_total: int
    message: str | None
    error_message: str | None
    created_at: str
    updated_at: str
    finished_at: str | None


@strawberry.type
class CandidateType:
    id: str
    full_name: str
    linkedin_url: str
    linkedin_slug: str
    current_title: str
    current_company: str
    location: str
    location_confidence: str
    github_url: str
    source_urls: list[str]
    associated_project_count: int


@strawberry.type
class ProjectCandidateType:
    id: str
    candidate: CandidateType
    fit_score: int
    must_have_score: str
    source_confidence: str
    early_stage_signal: str
    rationale: str
    domain_tags: list[str]
    target_company_match: str
    feedback_status: str | None


@strawberry.type
class SourcingProjectType:
    id: str
    name: str
    status: str
    job_description: str
    company_website: str
    notes: str
    generated_target_companies: list[str]
    approved_target_companies: list[str]
    generated_scorecard: list[str]
    approved_scorecard: list[str]
    search_keywords: list[str]
    candidate_archetypes: list[str]
    project_candidates: list[ProjectCandidateType]
    created_at: str
    updated_at: str


@strawberry.input
class CreateNoteInput:
    title: str
    body: str = ""


class CreateNoteInputModel(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=5000)


@strawberry.input
class CreateSourcingProjectInput:
    job_description: str
    company_website: str
    notes: str = ""


class CreateSourcingProjectInputModel(BaseModel):
    job_description: str = Field(min_length=20, max_length=20000)
    company_website: str = Field(min_length=3, max_length=500)
    notes: str = Field(default="", max_length=5000)


@strawberry.input
class ApproveSourcingCalibrationInput:
    project_id: str
    target_companies: list[str]
    scorecard: list[str]


class ApproveSourcingCalibrationInputModel(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)
    target_companies: list[str] = Field(min_length=1, max_length=50)
    scorecard: list[str] = Field(min_length=1, max_length=8)


@strawberry.input
class SetCandidateFeedbackInput:
    project_candidate_id: str
    feedback_status: str


class SetCandidateFeedbackInputModel(BaseModel):
    project_candidate_id: str = Field(min_length=1, max_length=36)
    feedback_status: str = Field(pattern="^(good_fit|bad_fit|not_relevant)$")


def user_email_to_viewer_type(user_email: str) -> ViewerType:
    return ViewerType(email=user_email)


def note_to_type(note: Note) -> NoteType:
    created_at = note.created_at
    if isinstance(created_at, datetime):
        created_at_str = created_at.isoformat()
    else:
        created_at_str = str(created_at)
    summary_updated_at = note.summary_updated_at
    if isinstance(summary_updated_at, datetime):
        summary_updated_at_str = summary_updated_at.isoformat()
    elif summary_updated_at is None:
        summary_updated_at_str = None
    else:
        summary_updated_at_str = str(summary_updated_at)
    return NoteType(
        id=note.id,
        title=note.title,
        body=note.body,
        summary=note.summary,
        summary_provider=note.summary_provider,
        summary_updated_at=summary_updated_at_str,
        created_at=created_at_str,
    )


def task_run_to_type(task_run: TaskRun) -> TaskRunType:
    def _serialize(value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        if value is None:
            return None
        return str(value)

    return TaskRunType(
        id=task_run.id,
        task_name=task_run.task_name,
        status=task_run.status,
        progress_current=task_run.progress_current,
        progress_total=task_run.progress_total,
        message=task_run.message,
        error_message=task_run.error_message,
        created_at=_serialize(task_run.created_at) or "",
        updated_at=_serialize(task_run.updated_at) or "",
        finished_at=_serialize(task_run.finished_at),
    )


def _serialize_datetime(value: datetime | None) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


async def candidate_to_type(candidate: Candidate, *, associated_project_count: int | None = None) -> CandidateType:
    return CandidateType(
        id=candidate.id,
        full_name=candidate.full_name,
        linkedin_url=candidate.linkedin_url,
        linkedin_slug=candidate.linkedin_slug,
        current_title=candidate.current_title,
        current_company=candidate.current_company,
        location=candidate.location,
        location_confidence=candidate.location_confidence,
        github_url=candidate.github_url,
        source_urls=list_to_graphql(candidate.source_urls),
        associated_project_count=associated_project_count if associated_project_count is not None else 0,
    )


async def project_candidate_to_type(
    project_candidate: ProjectCandidate,
    *,
    candidate: Candidate,
    associated_project_count: int,
) -> ProjectCandidateType:
    return ProjectCandidateType(
        id=project_candidate.id,
        candidate=await candidate_to_type(candidate, associated_project_count=associated_project_count),
        fit_score=project_candidate.fit_score,
        must_have_score=project_candidate.must_have_score,
        source_confidence=project_candidate.source_confidence,
        early_stage_signal=project_candidate.early_stage_signal,
        rationale=project_candidate.rationale,
        domain_tags=list_to_graphql(project_candidate.domain_tags),
        target_company_match=project_candidate.target_company_match,
        feedback_status=project_candidate.feedback_status,
    )


async def sourcing_project_to_type(
    project: SourcingProject,
    *,
    project_candidates: list[tuple[ProjectCandidate, Candidate]] | None = None,
    associated_project_counts: dict[str, int] | None = None,
) -> SourcingProjectType:
    candidate_types: list[ProjectCandidateType] = []
    for project_candidate, candidate in project_candidates or []:
        candidate_types.append(
            await project_candidate_to_type(
                project_candidate,
                candidate=candidate,
                associated_project_count=(associated_project_counts or {}).get(candidate.id, 0),
            )
        )

    return SourcingProjectType(
        id=project.id,
        name=project.name,
        status=project.status,
        job_description=project.job_description,
        company_website=project.company_website,
        notes=project.notes,
        generated_target_companies=list_to_graphql(project.generated_target_companies),
        approved_target_companies=list_to_graphql(project.approved_target_companies),
        generated_scorecard=list_to_graphql(project.generated_scorecard),
        approved_scorecard=list_to_graphql(project.approved_scorecard),
        search_keywords=list_to_graphql(project.search_keywords),
        candidate_archetypes=list_to_graphql(project.candidate_archetypes),
        project_candidates=candidate_types,
        created_at=_serialize_datetime(project.created_at),
        updated_at=_serialize_datetime(project.updated_at),
    )
