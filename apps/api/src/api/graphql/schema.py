from __future__ import annotations

from typing import Any

import strawberry
from graphql import ASTValidationRule, GraphQLError, ValidationContext
from graphql.language import FieldNode
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.audit import AuthorizationError, require_authenticated_user_email
from api.db import operation
from api.models import Candidate, Note, ProjectCandidate, SourcingProject, User
from api.sourcing import (
    derive_project_name,
    discover_candidates_for_project,
    dumps_list,
    generate_sourcing_strategy,
    upsert_candidate,
    upsert_project_candidate,
)
from api.tasks.base import get_task_run_for_user, list_task_runs_for_user, spawn_tracked_task
from api.tasks.note_summary import summarize_note_for_user, summarize_notes_task

from .types import (
    ApproveSourcingCalibrationInput,
    ApproveSourcingCalibrationInputModel,
    CandidateType,
    CreateNoteInput,
    CreateNoteInputModel,
    CreateSourcingProjectInput,
    CreateSourcingProjectInputModel,
    CurrentUserType,
    NoteType,
    ProjectCandidateType,
    SetCandidateFeedbackInput,
    SetCandidateFeedbackInputModel,
    SourcingProjectType,
    TaskRunType,
    ViewerType,
    candidate_to_type,
    note_to_type,
    project_candidate_to_type,
    sourcing_project_to_type,
    task_run_to_type,
    user_email_to_viewer_type,
)


def _require_user_email(info: strawberry.Info[Any, Any], *, action: str) -> str:
    try:
        return require_authenticated_user_email(
            info.context.get("user_email"),
            action=action,
            resource="note",
        )
    except AuthorizationError as exc:
        raise GraphQLError(str(exc)) from exc


async def _find_user_by_email(session: AsyncSession, user_email: str) -> User | None:
    return (await session.execute(select(User).where(User.email == user_email))).scalar_one_or_none()


async def _get_or_create_user(session: AsyncSession, user_email: str) -> User:
    user = await _find_user_by_email(session, user_email)
    if user is not None:
        return user
    user = User(email=user_email)
    session.add(user)
    await session.flush()
    return user


async def _project_candidates_for_project(
    session: AsyncSession,
    project_id: str,
) -> list[tuple[ProjectCandidate, Candidate]]:
    rows = (
        await session.execute(
            select(ProjectCandidate, Candidate)
            .join(Candidate, Candidate.id == ProjectCandidate.candidate_id)
            .where(ProjectCandidate.project_id == project_id)
            .order_by(ProjectCandidate.fit_score.desc())
        )
    ).all()
    return [(project_candidate, candidate) for project_candidate, candidate in rows]


async def _associated_project_counts(session: AsyncSession, candidate_ids: list[str]) -> dict[str, int]:
    if not candidate_ids:
        return {}
    rows = (
        await session.execute(
            select(ProjectCandidate.candidate_id, func.count(ProjectCandidate.id))
            .where(ProjectCandidate.candidate_id.in_(candidate_ids))
            .group_by(ProjectCandidate.candidate_id)
        )
    ).all()
    return {str(candidate_id): int(count) for candidate_id, count in rows}


@strawberry.type
class Query:
    @strawberry.field
    async def current_user(self, info: strawberry.Info[Any, Any]) -> CurrentUserType:
        user_email = _require_user_email(info, action="me.read")
        return CurrentUserType(id=user_email, email=user_email)

    @strawberry.field
    async def viewer(self, info: strawberry.Info[Any, Any]) -> ViewerType:
        user_email = _require_user_email(info, action="viewer.read")
        return user_email_to_viewer_type(user_email)

    @strawberry.field
    async def notes(self, info: strawberry.Info[Any, Any]) -> list[NoteType]:
        user_email = _require_user_email(info, action="notes.list")
        async with operation("notes.list") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                return []
            notes = (
                await op.session.execute(select(Note).where(Note.user_id == user.id).order_by(Note.created_at.desc()))
            ).scalars()
            return [note_to_type(note) for note in notes]

    @strawberry.field
    async def sourcing_projects(self, info: strawberry.Info[Any, Any]) -> list[SourcingProjectType]:
        user_email = _require_user_email(info, action="sourcing.projects.list")
        async with operation("sourcing.projects.list") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                return []
            projects = (
                await op.session.execute(
                    select(SourcingProject)
                    .where(SourcingProject.user_id == user.id)
                    .order_by(SourcingProject.updated_at.desc())
                )
            ).scalars()
            project_types: list[SourcingProjectType] = []
            for project in projects:
                project_candidates = await _project_candidates_for_project(op.session, project.id)
                candidate_ids = [candidate.id for _, candidate in project_candidates]
                project_types.append(
                    await sourcing_project_to_type(
                        project,
                        project_candidates=project_candidates,
                        associated_project_counts=await _associated_project_counts(op.session, candidate_ids),
                    )
                )
            return project_types

    @strawberry.field
    async def sourcing_project(self, info: strawberry.Info[Any, Any], project_id: str) -> SourcingProjectType | None:
        user_email = _require_user_email(info, action="sourcing.projects.get")
        async with operation("sourcing.projects.get") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                return None
            project = (
                await op.session.execute(
                    select(SourcingProject).where(
                        SourcingProject.id == project_id,
                        SourcingProject.user_id == user.id,
                    )
                )
            ).scalar_one_or_none()
            if project is None:
                return None
            project_candidates = await _project_candidates_for_project(op.session, project.id)
            candidate_ids = [candidate.id for _, candidate in project_candidates]
            return await sourcing_project_to_type(
                project,
                project_candidates=project_candidates,
                associated_project_counts=await _associated_project_counts(op.session, candidate_ids),
            )

    @strawberry.field
    async def candidates(self, info: strawberry.Info[Any, Any]) -> list[CandidateType]:
        user_email = _require_user_email(info, action="sourcing.candidates.list")
        async with operation("sourcing.candidates.list") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                return []
            candidate_id_query = (
                select(ProjectCandidate.candidate_id)
                .join(SourcingProject, SourcingProject.id == ProjectCandidate.project_id)
                .where(SourcingProject.user_id == user.id)
            )
            rows = (
                await op.session.execute(
                    select(Candidate).where(Candidate.id.in_(candidate_id_query)).order_by(Candidate.updated_at.desc())
                )
            ).scalars()
            candidates = list(rows)
            counts = await _associated_project_counts(op.session, [candidate.id for candidate in candidates])
            return [
                await candidate_to_type(candidate, associated_project_count=counts.get(candidate.id, 0))
                for candidate in candidates
            ]

    @strawberry.field
    async def task_runs(self, info: strawberry.Info[Any, Any]) -> list[TaskRunType]:
        user_email = _require_user_email(info, action="tasks.list")
        async with operation("tasks.resolve_user") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                return []
        task_runs = await list_task_runs_for_user(user_id=user.id)
        return [task_run_to_type(task_run) for task_run in task_runs]

    @strawberry.field
    async def task_run(
        self,
        info: strawberry.Info[Any, Any],
        task_run_id: str,
    ) -> TaskRunType | None:
        user_email = _require_user_email(info, action="tasks.get")
        async with operation("tasks.resolve_user") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                return None
        task_run = await get_task_run_for_user(task_run_id=task_run_id, user_id=user.id)
        if task_run is None:
            return None
        return task_run_to_type(task_run)


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_note(
        self,
        info: strawberry.Info[Any, Any],
        input: CreateNoteInput,
    ) -> NoteType:
        user_email = _require_user_email(info, action="notes.create")
        try:
            payload = CreateNoteInputModel.model_validate({"title": input.title, "body": input.body})
        except ValidationError as exc:
            raise GraphQLError(exc.errors()[0]["msg"]) from exc

        async with operation("notes.create") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                user = User(email=user_email)
                op.session.add(user)
                await op.session.flush()

            note = Note(user_id=user.id, title=payload.title.strip(), body=payload.body.strip())
            op.session.add(note)
            await op.session.commit()
            await op.session.refresh(note)
            return note_to_type(note)

    @strawberry.mutation
    async def create_sourcing_project(
        self,
        info: strawberry.Info[Any, Any],
        input: CreateSourcingProjectInput,
    ) -> SourcingProjectType:
        user_email = _require_user_email(info, action="sourcing.projects.create")
        try:
            payload = CreateSourcingProjectInputModel.model_validate(
                {
                    "job_description": input.job_description,
                    "company_website": input.company_website,
                    "notes": input.notes,
                }
            )
        except ValidationError as exc:
            raise GraphQLError(exc.errors()[0]["msg"]) from exc

        strategy = generate_sourcing_strategy(payload.job_description, payload.notes)
        async with operation("sourcing.projects.create") as op:
            user = await _get_or_create_user(op.session, user_email)
            project = SourcingProject(
                user_id=user.id,
                name=derive_project_name(payload.job_description, payload.company_website),
                job_description=payload.job_description.strip(),
                company_website=payload.company_website.strip(),
                notes=payload.notes.strip(),
                status="awaiting_calibration",
                generated_target_companies=dumps_list(strategy["target_companies"]),
                generated_scorecard=dumps_list(strategy["scorecard"]),
                search_keywords=dumps_list(strategy["keywords"]),
                candidate_archetypes=dumps_list(strategy["archetypes"]),
            )
            op.session.add(project)
            await op.session.commit()
            await op.session.refresh(project)
            return await sourcing_project_to_type(project)

    @strawberry.mutation
    async def approve_sourcing_project_calibration(
        self,
        info: strawberry.Info[Any, Any],
        input: ApproveSourcingCalibrationInput,
    ) -> SourcingProjectType:
        user_email = _require_user_email(info, action="sourcing.projects.calibrate")
        try:
            payload = ApproveSourcingCalibrationInputModel.model_validate(
                {
                    "project_id": input.project_id,
                    "target_companies": input.target_companies,
                    "scorecard": input.scorecard,
                }
            )
        except ValidationError as exc:
            raise GraphQLError(exc.errors()[0]["msg"]) from exc

        target_companies = [company.strip() for company in payload.target_companies if company.strip()]
        scorecard = [criterion.strip() for criterion in payload.scorecard if criterion.strip()]
        if not target_companies or not scorecard:
            raise GraphQLError("Target companies and scorecard must both contain at least one item.")

        async with operation("sourcing.projects.calibrate") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                raise GraphQLError("User not found.")
            project = (
                await op.session.execute(
                    select(SourcingProject).where(
                        SourcingProject.id == payload.project_id,
                        SourcingProject.user_id == user.id,
                    )
                )
            ).scalar_one_or_none()
            if project is None:
                raise GraphQLError("Sourcing project not found.")

            project.approved_target_companies = dumps_list(target_companies)
            project.approved_scorecard = dumps_list(scorecard)
            project.status = "calibrated"
            await op.session.commit()
            await op.session.refresh(project)
            return await sourcing_project_to_type(project)

    @strawberry.mutation
    async def run_sourcing_project_search(
        self,
        info: strawberry.Info[Any, Any],
        project_id: str,
    ) -> SourcingProjectType:
        user_email = _require_user_email(info, action="sourcing.projects.search")
        async with operation("sourcing.projects.search.resolve") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                raise GraphQLError("User not found.")
            project = (
                await op.session.execute(
                    select(SourcingProject).where(
                        SourcingProject.id == project_id,
                        SourcingProject.user_id == user.id,
                    )
                )
            ).scalar_one_or_none()
            if project is None:
                raise GraphQLError("Sourcing project not found.")
            if project.status not in {"calibrated", "ready_for_review", "exported"}:
                raise GraphQLError("Approve target companies and scorecard before running search.")

        discoveries = await discover_candidates_for_project(project)

        async with operation("sourcing.projects.search.persist") as op:
            project = (
                await op.session.execute(select(SourcingProject).where(SourcingProject.id == project_id))
            ).scalar_one()
            for discovery in discoveries:
                candidate = await upsert_candidate(op.session, discovery)
                await upsert_project_candidate(
                    op.session,
                    project=project,
                    candidate=candidate,
                    discovery=discovery,
                )
            project.status = "ready_for_review"
            await op.session.commit()
            await op.session.refresh(project)
            project_candidates = await _project_candidates_for_project(op.session, project.id)
            candidate_ids = [candidate.id for _, candidate in project_candidates]
            return await sourcing_project_to_type(
                project,
                project_candidates=project_candidates,
                associated_project_counts=await _associated_project_counts(op.session, candidate_ids),
            )

    @strawberry.mutation
    async def set_sourcing_candidate_feedback(
        self,
        info: strawberry.Info[Any, Any],
        input: SetCandidateFeedbackInput,
    ) -> ProjectCandidateType:
        user_email = _require_user_email(info, action="sourcing.candidates.feedback")
        try:
            payload = SetCandidateFeedbackInputModel.model_validate(
                {
                    "project_candidate_id": input.project_candidate_id,
                    "feedback_status": input.feedback_status,
                }
            )
        except ValidationError as exc:
            raise GraphQLError(exc.errors()[0]["msg"]) from exc

        async with operation("sourcing.candidates.feedback") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                raise GraphQLError("User not found.")
            row = (
                await op.session.execute(
                    select(ProjectCandidate, Candidate)
                    .join(Candidate, Candidate.id == ProjectCandidate.candidate_id)
                    .join(SourcingProject, SourcingProject.id == ProjectCandidate.project_id)
                    .where(
                        ProjectCandidate.id == payload.project_candidate_id,
                        SourcingProject.user_id == user.id,
                    )
                )
            ).one_or_none()
            if row is None:
                raise GraphQLError("Project candidate not found.")
            project_candidate, candidate = row
            project_candidate.feedback_status = payload.feedback_status
            await op.session.commit()
            await op.session.refresh(project_candidate)
            return await project_candidate_to_type(
                project_candidate,
                candidate=candidate,
                associated_project_count=(await _associated_project_counts(op.session, [candidate.id])).get(
                    candidate.id,
                    0,
                ),
            )

    @strawberry.mutation
    async def summarize_note(self, info: strawberry.Info[Any, Any], note_id: str) -> NoteType:
        user_email = _require_user_email(info, action="notes.summarize")
        try:
            note = await summarize_note_for_user(note_id=note_id, user_email=user_email)
        except LookupError as exc:
            raise GraphQLError(str(exc)) from exc
        return note_to_type(note)

    @strawberry.mutation
    async def start_note_summary_run(self, info: strawberry.Info[Any, Any]) -> TaskRunType:
        user_email = _require_user_email(info, action="tasks.start")
        async with operation("tasks.resolve_user") as op:
            user = await _find_user_by_email(op.session, user_email)
            if user is None:
                raise GraphQLError("User not found.")

        task_run = await spawn_tracked_task(
            task_name="notes.summary_run",
            user_id=user.id,
            message="Queued note summary run",
            task_callable=lambda context: summarize_notes_task(context, user_id=user.id),
        )
        return task_run_to_type(task_run)


MAX_QUERY_DEPTH = 10


class DepthLimitRule(ASTValidationRule):
    """Reject queries deeper than MAX_QUERY_DEPTH to prevent resource exhaustion."""

    def __init__(self, context: ValidationContext) -> None:
        super().__init__(context)
        self._depth = 0

    def enter_field(self, node: FieldNode, *_args: Any) -> None:
        self._depth += 1
        if self._depth > MAX_QUERY_DEPTH:
            self.report_error(GraphQLError(f"Query depth exceeds maximum allowed depth of {MAX_QUERY_DEPTH}."))

    def leave_field(self, node: FieldNode, *_args: Any) -> None:
        self._depth -= 1


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[lambda: strawberry.extensions.AddValidationRules([DepthLimitRule])],
)
