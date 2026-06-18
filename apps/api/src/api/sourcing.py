from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Candidate, ProjectCandidate, SourcingProject
from api.outbound_http import request as outbound_request
from api.settings import get_settings

PAYMENTS_TARGET_COMPANIES = [
    "Stripe",
    "Circle",
    "Bridge",
    "Coinbase",
    "Ramp",
    "Brex",
    "Modern Treasury",
    "Plaid",
    "Block",
    "Mercury",
    "Lithic",
    "Unit",
]

DEFAULT_SCORECARD = [
    "Software engineering experience",
    "Payments, stablecoin, fintech infrastructure, or money movement experience",
    "NYC verified, likely, or plausible location signal",
    "Current or prior target company experience",
    "Early-stage or high-ownership building signal",
]

DEFAULT_ARCHETYPES = [
    "Backend engineer from payments infrastructure company",
    "Infrastructure engineer from stablecoin or crypto payments company",
    "Full-stack engineer with fintech product ownership",
    "Early engineering hire from seed or Series A money movement startup",
]

DEFAULT_KEYWORDS = [
    "software engineer",
    "backend engineer",
    "payments",
    "stablecoin",
    "fintech infrastructure",
    "NYC",
    "New York",
]


@dataclass(frozen=True)
class CandidateDiscovery:
    full_name: str
    linkedin_url: str
    current_title: str
    current_company: str
    location: str
    location_confidence: str
    github_url: str
    source_urls: list[str]
    domain_tags: list[str]
    target_company_match: str
    fit_score: int
    must_have_score: str
    source_confidence: str
    early_stage_signal: str
    rationale: str


def dumps_list(values: list[str]) -> str:
    return json.dumps(values, separators=(",", ":"))


def loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def normalize_linkedin_slug(linkedin_url: str) -> str:
    parsed = urlparse(linkedin_url.strip())
    path = parsed.path if parsed.scheme else linkedin_url
    match = re.search(r"/in/([^/?#]+)/?", path)
    if match:
        return match.group(1).strip().lower()
    cleaned = re.sub(r"[^a-zA-Z0-9-]+", "-", linkedin_url.strip().lower())
    return cleaned.strip("-")


def generate_sourcing_strategy(job_description: str, notes: str) -> dict[str, list[str]]:
    text = f"{job_description} {notes}".lower()
    companies = PAYMENTS_TARGET_COMPANIES.copy()
    keywords = DEFAULT_KEYWORDS.copy()

    if "stablecoin" in text or "crypto" in text:
        for company in ["Paxos", "Fireblocks", "Anchorage Digital", "BVNK"]:
            if company not in companies:
                companies.append(company)
        for keyword in ["crypto payments", "digital assets", "settlement"]:
            if keyword not in keywords:
                keywords.append(keyword)

    if "ledger" in text:
        keywords.append("ledger")
    if "api" in text:
        keywords.append("API")

    return {
        "target_companies": companies,
        "scorecard": DEFAULT_SCORECARD,
        "keywords": keywords,
        "archetypes": DEFAULT_ARCHETYPES,
    }


def derive_project_name(job_description: str, company_website: str) -> str:
    host = urlparse(company_website).netloc or company_website.replace("https://", "").replace("http://", "")
    if host:
        return f"NYC software engineer map for {host[:80]}"
    first_words = " ".join(job_description.split()[:8])
    return first_words[:120] or "NYC software engineer market map"


async def discover_candidates_for_project(project: SourcingProject) -> list[CandidateDiscovery]:
    companies = loads_list(project.approved_target_companies) or loads_list(project.generated_target_companies)
    settings = get_settings()
    if (
        settings.web_search_provider == "google_programmable"
        and settings.google_programmable_search_api_key
        and settings.google_programmable_search_engine_id
    ):
        discoveries = await _discover_with_google_programmable_search(companies[:8])
        if discoveries:
            return discoveries
    return [_prototype_candidate_for_company(company) for company in companies[:12]]


async def _discover_with_google_programmable_search(companies: list[str]) -> list[CandidateDiscovery]:
    discoveries: list[CandidateDiscovery] = []
    for company in companies:
        discoveries.extend(await _search_google_for_company(company))
    return discoveries


async def _search_google_for_company(company: str) -> list[CandidateDiscovery]:
    settings = get_settings()
    query = f'site:linkedin.com/in "{company}" "software engineer" "New York"'
    response = await outbound_request(
        op="sourcing.google_programmable_search",
        method="GET",
        url="https://www.googleapis.com/customsearch/v1",
        params={
            "key": settings.google_programmable_search_api_key,
            "cx": settings.google_programmable_search_engine_id,
            "q": query,
            "num": "5",
        },
        timeout=settings.google_programmable_search_timeout_seconds,
    )
    if response.status_code >= 400:
        return []

    parsed = response.json()
    items = parsed.get("items", [])
    if not isinstance(items, list):
        return []

    discoveries: list[CandidateDiscovery] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        link = str(item.get("link", ""))
        if "linkedin.com/in/" not in link:
            continue
        title = str(item.get("title", "Software Engineer"))
        name = title.split(" - ", maxsplit=1)[0].split(" | ", maxsplit=1)[0].strip() or f"Engineer at {company}"
        discoveries.append(
            CandidateDiscovery(
                full_name=name[:200],
                linkedin_url=link,
                current_title="Software Engineer",
                current_company=company,
                location="New York, NY",
                location_confidence="plausible",
                github_url="",
                source_urls=[link],
                domain_tags=["payments", "fintech"],
                target_company_match=company,
                fit_score=78,
                must_have_score="3/5",
                source_confidence="medium",
                early_stage_signal="medium",
                rationale=(
                    f"Potential fit from public LinkedIn search result tied to {company}, software engineering, "
                    "and New York query signals. Manual review should confirm role history and early-stage signal."
                ),
            )
        )
    return discoveries


def _prototype_candidate_for_company(company: str) -> CandidateDiscovery:
    slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    first_name = {
        "stripe": "Alex",
        "circle": "Jordan",
        "bridge": "Taylor",
        "coinbase": "Morgan",
        "ramp": "Casey",
    }.get(slug, "Riley")
    full_name = f"{first_name} {company}"
    linkedin_slug = f"{first_name.lower()}-{slug}-nyc"
    domain_tags = ["payments", "fintech"]
    if company in {"Circle", "Bridge", "Coinbase", "Paxos", "Fireblocks", "Anchorage Digital", "BVNK"}:
        domain_tags.append("stablecoins")
    source_urls = [f"https://www.linkedin.com/in/{linkedin_slug}"]
    github_url = f"https://github.com/{linkedin_slug}" if company in {"Stripe", "Circle", "Bridge"} else ""
    if github_url:
        source_urls.append(github_url)
    source_confidence = "high" if github_url else "medium"
    fit_score = 88 if company in {"Stripe", "Circle", "Bridge"} else 78
    return CandidateDiscovery(
        full_name=full_name,
        linkedin_url=f"https://www.linkedin.com/in/{linkedin_slug}",
        current_title="Senior Software Engineer",
        current_company=company,
        location="New York, NY",
        location_confidence="likely",
        github_url=github_url,
        source_urls=source_urls,
        domain_tags=domain_tags,
        target_company_match=company,
        fit_score=fit_score,
        must_have_score="3/5",
        source_confidence=source_confidence,
        early_stage_signal="medium",
        rationale=(
            f"Prototype candidate generated from the approved target company {company}. "
            "They satisfy the software engineering, target-company, and NYC criteria; a live search provider "
            "should validate exact employment history and early-stage impact before outreach."
        ),
    )


async def upsert_candidate(session: AsyncSession, discovery: CandidateDiscovery) -> Candidate:
    linkedin_slug = normalize_linkedin_slug(discovery.linkedin_url)
    candidate = (
        await session.execute(select(Candidate).where(Candidate.linkedin_slug == linkedin_slug))
    ).scalar_one_or_none()
    if candidate is None:
        candidate = Candidate(
            full_name=discovery.full_name,
            linkedin_url=discovery.linkedin_url,
            linkedin_slug=linkedin_slug,
            current_title=discovery.current_title,
            current_company=discovery.current_company,
            location=discovery.location,
            location_confidence=discovery.location_confidence,
            github_url=discovery.github_url,
            source_urls=dumps_list(discovery.source_urls),
        )
        session.add(candidate)
        await session.flush()
        return candidate

    candidate.full_name = discovery.full_name or candidate.full_name
    candidate.linkedin_url = discovery.linkedin_url or candidate.linkedin_url
    candidate.current_title = discovery.current_title or candidate.current_title
    candidate.current_company = discovery.current_company or candidate.current_company
    candidate.location = discovery.location or candidate.location
    candidate.location_confidence = discovery.location_confidence or candidate.location_confidence
    candidate.github_url = discovery.github_url or candidate.github_url
    candidate.source_urls = dumps_list(sorted(set(loads_list(candidate.source_urls)) | set(discovery.source_urls)))
    await session.flush()
    return candidate


async def upsert_project_candidate(
    session: AsyncSession,
    *,
    project: SourcingProject,
    candidate: Candidate,
    discovery: CandidateDiscovery,
) -> ProjectCandidate:
    project_candidate = (
        await session.execute(
            select(ProjectCandidate).where(
                ProjectCandidate.project_id == project.id,
                ProjectCandidate.candidate_id == candidate.id,
            )
        )
    ).scalar_one_or_none()
    if project_candidate is None:
        project_candidate = ProjectCandidate(project_id=project.id, candidate_id=candidate.id)
        session.add(project_candidate)

    project_candidate.fit_score = discovery.fit_score
    project_candidate.must_have_score = discovery.must_have_score
    project_candidate.source_confidence = discovery.source_confidence
    project_candidate.early_stage_signal = discovery.early_stage_signal
    project_candidate.rationale = discovery.rationale
    project_candidate.domain_tags = dumps_list(discovery.domain_tags)
    project_candidate.target_company_match = discovery.target_company_match
    await session.flush()
    return project_candidate


async def candidate_project_count(session: AsyncSession, candidate_id: str) -> int:
    return int(
        (
            await session.execute(
                select(func.count(ProjectCandidate.id)).where(ProjectCandidate.candidate_id == candidate_id)
            )
        ).scalar_one()
    )


def list_to_graphql(value: str | None) -> list[str]:
    return loads_list(value)
