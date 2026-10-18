from typing import List, Optional, Dict, Any
from datetime import datetime
import re

from sqlmodel import Session, select, text
from apps.api.app.modules.core.models import LegalSource
from apps.api.app.modules.rag.schemas import Evidence


def _or_tsquery(query: str) -> Optional[str]:
    """Build a sanitized OR tsquery from free text (tokens of len >= 2).

    OR keeps retrieval recall high and lets ts_rank order partial matches;
    AND-plainto matches nothing realistic for legal queries like
    'Payment MA service_agreement'.
    """
    tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) >= 2]
    if not tokens:
        return None
    return " | ".join(f"'{t}'" for t in tokens)


def search_sources(
    session: Session,
    query: str,
    jurisdiction: Optional[str] = None,
    contract_type: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Search legal sources using PostgreSQL full-text search.

    Vector (pgvector) similarity search is layered on top of this keyword
    search once chunk embeddings are indexed; see docs/implementation-plan.
    """
    tsq = _or_tsquery(query)
    if tsq is None:
        return []

    keyword_query = text("""
        SELECT
            ls.id as source_id,
            lsv.version as source_version,
            ls.title,
            ls.jurisdiction,
            ls.language,
            sc.article,
            sc.page_start,
            sc.page_end,
            sc.content,
            ts_rank(
                to_tsvector('simple', sc.content),
                to_tsquery('simple', :tsq)
            ) as rank
        FROM legalsource ls
        JOIN legalsourceversion lsv ON ls.id = lsv.source_id
        JOIN sourcechunk sc ON lsv.id = sc.version_id
        WHERE ls.status = 'approved'
            AND (ls.effective_date IS NULL OR ls.effective_date <= NOW())
            AND (ls.jurisdiction = :jurisdiction OR :jurisdiction IS NULL)
            AND (to_tsvector('simple', sc.content) @@ to_tsquery('simple', :tsq))
        ORDER BY rank DESC
        LIMIT :limit
    """)

    result = session.execute(
        keyword_query,
        {
            "tsq": tsq,
            "jurisdiction": jurisdiction,
            "limit": limit,
        },
    ).all()

    sources = []
    for row in result:
        sources.append({
            "source_id": row.source_id,
            "source_version": row.source_version,
            "title": row.title,
            "jurisdiction": row.jurisdiction,
            "language": row.language,
            "article": row.article,
            "page_start": row.page_start,
            "page_end": row.page_end,
            "content": row.content,
            "relevance": float(row.rank) if row.rank is not None else 0.5,
        })

    # Deduplicate by source
    seen = set()
    deduplicated = []
    for source in sources:
        key = source["source_id"]
        if key not in seen:
            seen.add(key)
            deduplicated.append(source)

    return deduplicated[:limit]


def get_evidence_for_section(
    session: Session,
    section_title: str,
    jurisdiction: str,
    contract_type: str,
    limit: int = 5
) -> List[Evidence]:
    """Get evidence for a specific contract section."""
    search_query = f"{section_title} {jurisdiction} {contract_type}"

    sources = search_sources(
        session,
        query=search_query,
        jurisdiction=jurisdiction,
        limit=limit
    )

    evidence = []
    for source in sources:
        evidence.append(Evidence(
            source_id=str(source["source_id"]),
            source_version=source["source_version"],
            title=source["title"],
            jurisdiction=source["jurisdiction"],
            language=source["language"],
            article=source.get("article"),
            page_start=source.get("page_start"),
            page_end=source.get("page_end"),
            excerpt=source.get("content", "")[:200] + ("..." if len(source.get("content", "")) > 200 else ""),
            relevance_reason=f"Supports {section_title.lower()} for {jurisdiction}",
            authority="official",
            status="valid"
        ))

    return evidence


def validate_source_status(
    session: Session,
    source_id: int
) -> Dict[str, str]:
    """Validate that a source is in a valid state for retrieval."""
    statement = select(LegalSource).where(LegalSource.id == source_id)
    source = session.exec(statement).first()

    if not source:
        return {"status": "not_found", "message": "Source not found"}

    if source.status != "approved":
        return {"status": "not_approved", "message": f"Source is in '{source.status}' status, not approved"}

    if source.effective_date and source.effective_date > datetime.utcnow():
        return {"status": "not_effective", "message": "Source is not yet effective"}

    return {"status": "valid", "message": "Source is valid for retrieval"}
