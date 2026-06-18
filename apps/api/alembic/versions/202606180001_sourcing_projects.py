"""add sourcing projects

Revision ID: 202606180001
Revises: 202602260001
Create Date: 2026-06-18 00:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606180001"
down_revision = "202602260001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sourcing_projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("company_website", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("generated_target_companies", sa.Text(), nullable=False),
        sa.Column("approved_target_companies", sa.Text(), nullable=False),
        sa.Column("generated_scorecard", sa.Text(), nullable=False),
        sa.Column("approved_scorecard", sa.Text(), nullable=False),
        sa.Column("search_keywords", sa.Text(), nullable=False),
        sa.Column("candidate_archetypes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sourcing_projects_user_id", "sourcing_projects", ["user_id"], unique=False)

    op.create_table(
        "candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("linkedin_url", sa.String(length=500), nullable=False),
        sa.Column("linkedin_slug", sa.String(length=200), nullable=False),
        sa.Column("current_title", sa.String(length=200), nullable=False),
        sa.Column("current_company", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=False),
        sa.Column("location_confidence", sa.String(length=40), nullable=False),
        sa.Column("github_url", sa.String(length=500), nullable=False),
        sa.Column("source_urls", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("linkedin_url"),
        sa.UniqueConstraint("linkedin_slug"),
    )
    op.create_index("ix_candidates_linkedin_slug", "candidates", ["linkedin_slug"], unique=False)

    op.create_table(
        "project_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("fit_score", sa.Integer(), nullable=False),
        sa.Column("must_have_score", sa.String(length=20), nullable=False),
        sa.Column("source_confidence", sa.String(length=40), nullable=False),
        sa.Column("early_stage_signal", sa.String(length=40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("domain_tags", sa.Text(), nullable=False),
        sa.Column("target_company_match", sa.String(length=200), nullable=False),
        sa.Column("feedback_status", sa.String(length=40), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["sourcing_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "candidate_id", name="uq_project_candidates_project_candidate"),
    )
    op.create_index("ix_project_candidates_candidate_id", "project_candidates", ["candidate_id"], unique=False)
    op.create_index("ix_project_candidates_project_id", "project_candidates", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_project_candidates_project_id", table_name="project_candidates")
    op.drop_index("ix_project_candidates_candidate_id", table_name="project_candidates")
    op.drop_table("project_candidates")
    op.drop_index("ix_candidates_linkedin_slug", table_name="candidates")
    op.drop_table("candidates")
    op.drop_index("ix_sourcing_projects_user_id", table_name="sourcing_projects")
    op.drop_table("sourcing_projects")
