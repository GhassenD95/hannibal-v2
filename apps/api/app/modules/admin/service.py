"""Admin business logic: jurisdiction pack import/management, source and clause governance.

DEMO packs carry DEMO-labeled content only; the importer never fabricates legal text.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select, delete

from apps.api.app.modules.core.models import (
    JurisdictionPack, PackVersion, ContractType, IntakeSchema, IntakeField,
    SectionDefinition, LegalSource, LegalSourceVersion, SourceChunk,
    SourceReference, Clause, ValidationRule, RiskPlaybook,
)
from apps.api.app.modules.rag.service import search_sources

LEGAL_PACKS_ROOT = Path(__file__).resolve().parents[5] / "legal-packs"


def _resolve_pack_path(path: str) -> Path:
    """Guard: only allow files inside the legal-packs directory."""
    raw = Path(path).expanduser()
    if not raw.is_absolute():
        raw = (LEGAL_PACKS_ROOT / raw).resolve()
    root = LEGAL_PACKS_ROOT.resolve()
    if root not in raw.parents:
        raise ValueError("Pack import path must be inside legal-packs/")
    return raw


def _get(session: Session, model, **kwargs):
    statement = select(model)
    for key, value in kwargs.items():
        statement = statement.where(getattr(model, key) == value)
    return session.exec(statement).first()


def load_pack_data(session: Session, data: Dict[str, Any]) -> JurisdictionPack:
    """Idempotently import a versioned jurisdiction pack from validated JSON.

    Jurisdiction and the set of contract types the pack declares are stored in
    pack metadata so that packs for different jurisdictions can coexist even
    though ContractType names are globally unique.
    """
    pack_data = data["pack"]
    pack_jurisdiction = pack_data.get("jurisdiction") or "MA"
    declared_types = [ct["name"] for ct in data.get("contractTypes", [])]
    pack = _get(session, JurisdictionPack, name=pack_data["name"])
    if pack is None:
        pack = JurisdictionPack(name=pack_data["name"])
        session.add(pack)
    pack.description = pack_data.get("description")
    pack.version = pack_data.get("version", "1.0.0")
    pack.status = pack.status or "draft"
    pack.pack_metadata = {
        **pack_data.get("metadata", {}),
        "jurisdiction": pack_jurisdiction,
        "contract_types": ",".join(declared_types),
    }
    session.add(pack)
    session.commit()
    session.refresh(pack)

    pack_version = _get(
        session, PackVersion,
        pack_id=pack.id, version_number=pack_data.get("version", "1.0.0"),
    )
    if pack_version is None:
        pack_version = PackVersion(
            pack_id=pack.id,
            version_number=pack_data.get("version", "1.0.0"),
            status="draft",
        )
        session.add(pack_version)
    session.commit()
    session.refresh(pack_version)

    # Intake schemas first (contract types reference them)
    for schema_data in data.get("intakeSchemas", []):
        schema = _get(session, IntakeSchema, name=schema_data["name"])
        if schema is None:
            schema = IntakeSchema(name=schema_data["name"])
            session.add(schema)
        schema.description = schema_data.get("description")
        schema.pack_version_id = pack_version.id
        session.add(schema)
        session.commit()
        session.refresh(schema)
        existing = session.exec(
            select(IntakeField).where(IntakeField.schema_id == schema.id)
        ).all()
        existing_fields = {f.field_name: f for f in existing}
        for field_data in schema_data.get("fields", []):
            field = existing_fields.get(field_data["field_name"])
            if field is None:
                field = IntakeField(schema_id=schema.id,
                                    field_name=field_data["field_name"])
                session.add(field)
            field.field_label = field_data["field_label"]
            field.field_type = field_data["field_type"]
            field.is_required = field_data.get("is_required", False)
            field.options = field_data.get("options", [])
            field.order_index = field_data.get("order_index", 0)
            session.add(field)
        session.commit()

    # Contract types + section definitions
    #
    # ContractType names are globally unique, so a contract type row is a
    # jurisdiction-neutral template shared by all packs that declare it. Only
    # the pack version that first defines the type may write to that shared
    # template; later packs (e.g. TN alongside MA) reuse it.
    for ct_data in data.get("contractTypes", []):
        contract_type = _get(session, ContractType, name=ct_data["name"])
        if contract_type is None:
            contract_type = ContractType(name=ct_data["name"])
            session.add(contract_type)
            session.commit()
            session.refresh(contract_type)
        if contract_type.pack_version_id is not None and \
                contract_type.pack_version_id != pack_version.id:
            continue
        contract_type.description = ct_data.get("description")
        contract_type.pack_version_id = pack_version.id
        schema = _get(session, IntakeSchema, name=ct_data.get("intakeSchema", ""))
        contract_type.intake_schema_id = schema.id if schema else None
        session.add(contract_type)
        session.commit()
        session.refresh(contract_type)
        existing_sections = session.exec(
            select(SectionDefinition).where(
                SectionDefinition.contract_type_id == contract_type.id
            )
        ).all()
        section_map = {s.name: s for s in existing_sections}
        for sec_data in ct_data.get("sectionDefinitions", []):
            section = section_map.get(sec_data["name"])
            if section is None:
                section = SectionDefinition(
                    contract_type_id=contract_type.id, name=sec_data["name"])
                session.add(section)
            section.title = sec_data["title"]
            section.description = sec_data.get("description")
            section.is_required = sec_data.get("is_required", True)
            section.order_index = sec_data.get("order_index", 0)
            section.evidence_tags = sec_data.get("evidence_tags", [])
            section.default_clause_titles = sec_data.get("default_clause_titles", [])
            session.add(section)
        session.commit()

    # Clauses
    for clause_data in data.get("clauses", []):
        clause_jurisdiction = clause_data.get("jurisdiction") or pack_jurisdiction
        clause = _get(
            session, Clause,
            title=clause_data["title"], contract_type=clause_data["contract_type"],
            jurisdiction=clause_jurisdiction,
        )
        if clause is None:
            clause = Clause(title=clause_data["title"],
                            contract_type=clause_data["contract_type"],
                            jurisdiction=clause_jurisdiction)
            session.add(clause)
        clause.content = clause_data["content"]
        clause.clause_type = clause_data.get("clause_type", "optional")
        clause.jurisdiction = clause_jurisdiction
        clause.version = pack_data.get("version", "1.0.0")
        clause.pack_version_id = pack_version.id
        clause.description = clause_data.get("description")
        clause.status = "approved"
        session.add(clause)
    session.commit()

    # Validation rules
    for rule_data in data.get("validationRules", []):
        rule = _get(session, ValidationRule, name=rule_data["name"])
        if rule is None:
            rule = ValidationRule(name=rule_data["name"])
            session.add(rule)
        rule.description = rule_data.get("description")
        rule.rule_type = rule_data["rule_type"]
        rule.severity = rule_data["severity"]
        rule.applies_to = rule_data.get("applies_to", [])
        rule.config = rule_data.get("config", {})
        rule.is_active = True
        rule.pack_version_id = pack_version.id
        session.add(rule)
    session.commit()

    # Risk playbook
    rp_data = data.get("riskPlaybook", {})
    if rp_data:
        playbook = _get(session, RiskPlaybook,
                        pack_version_id=pack_version.id, name=rp_data.get("name"))
        if playbook is None:
            playbook = RiskPlaybook(pack_version_id=pack_version.id,
                                    name=rp_data.get("name"))
            session.add(playbook)
        playbook.rules = rp_data.get("rules", [])
        session.add(playbook)
    session.commit()

    # Legal sources + chunks + references
    auto_approve = bool(pack_data.get("autoApproveDemoSources", False))
    for source_data in data.get("sources", []):
        source = _get(session, LegalSource, title=source_data["title"])
        if source is None:
            source = LegalSource(title=source_data["title"])
            session.add(source)
        source.jurisdiction = source_data["jurisdiction"]
        source.source_type = source_data.get("source_type", "law")
        source.language = source_data.get("language", "fr")
        source.version = source_data["version"]
        source.effective_date = source_data.get("effective_date")
        source.description = source_data.get("description")
        source.source_metadata = source_data.get("metadata", {})
        is_demo = bool(source_data.get("metadata", {}).get("demo")) or auto_approve
        if source.status == "archived":
            raise ValueError(f"Cannot import into archived source: {source.title}")
        if source.status != "approved" and (auto_approve or is_demo):
            source.status = "approved"
        elif source.status != "approved":
            source.status = "draft"
        session.add(source)
        session.commit()
        session.refresh(source)

        version = _get(session, LegalSourceVersion,
                       source_id=source.id, version=source_data["version"])
        if version is None:
            version = LegalSourceVersion(source_id=source.id,
                                         version=source_data["version"])
            session.add(version)
        version.text = " ".join(
            c["content"] for c in source_data.get("chunks", [])
        )
        version.effective_date = source_data.get("effective_date")
        version.source_metadata = source_data.get("metadata", {})
        version.page_count = None
        session.add(version)
        session.commit()
        session.refresh(version)

        session.exec(delete(SourceChunk).where(SourceChunk.version_id == version.id))
        chunks = []
        for chunk_data in source_data.get("chunks", []):
            chunks.append(SourceChunk(
                version_id=version.id,
                content=chunk_data["content"],
                chunk_index=chunk_data.get("chunk_index", 0),
                article=chunk_data.get("article"),
                page_start=chunk_data.get("page_start"),
                page_end=chunk_data.get("page_end"),
            ))
        session.add_all(chunks)
        source.chunk_count = len(chunks)
        session.add(source)

        ref = _get(session, SourceReference, pack_version_id=pack_version.id,
                   source_id=source.id)
        if ref is None:
            session.add(SourceReference(pack_version_id=pack_version.id,
                                        source_id=source.id, relevance_score=1.0))
        session.commit()

    return pack


def import_pack(session: Session, path: str) -> JurisdictionPack:
    file_path = _resolve_pack_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Pack file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return load_pack_data(session, data)


def list_packs(session: Session) -> List[JurisdictionPack]:
    return list(session.exec(select(JurisdictionPack).order_by(
        JurisdictionPack.name)).all())


def pack_object(pack: JurisdictionPack, session: Session) -> Dict[str, Any]:
    from apps.api.app.modules.core.models import (
        PackVersion, ContractType, IntakeSchema, Clause, ValidationRule,
        RiskPlaybook, SourceReference,
    )
    version = session.exec(
        select(PackVersion).where(PackVersion.pack_id == pack.id).order_by(
            PackVersion.id.desc())
    ).first()
    declared_types = [
        s.strip() for s in (pack.pack_metadata.get("contract_types") or "").split(",")
        if s.strip()
    ]
    contract_types = [
        {"id": ct.id, "name": ct.name}
        for name in declared_types
        if (ct := session.exec(
            select(ContractType).where(ContractType.name == name)).first()) is not None
    ]
    return {
        "id": pack.id,
        "name": pack.name,
        "description": pack.description,
        "version": pack.version,
        "status": pack.status,
        "metadata": pack.pack_metadata,
        "contractTypes": contract_types,
        "clauseCount": len(session.exec(select(Clause)
                                        .where(Clause.pack_version_id == version.id)).all()) if version else 0,
        "sourceCount": len(session.exec(select(SourceReference)
                                        .where(SourceReference.pack_version_id == version.id)).all()) if version else 0,
        "validationRuleCount": len(session.exec(select(ValidationRule)
                                                .where(ValidationRule.pack_version_id == version.id)).all()) if version else 0,
        "riskPlaybookName": (
            session.exec(select(RiskPlaybook)
                         .where(RiskPlaybook.pack_version_id == version.id)).first().name
            if version and session.exec(select(RiskPlaybook)
                                        .where(RiskPlaybook.pack_version_id == version.id)).first()
            else None
        ),
    }


def validate_pack(session: Session, pack_id: int) -> Dict[str, Any]:
    pack = session.get(JurisdictionPack, pack_id)
    if pack is None:
        raise KeyError("Pack not found")
    issues: List[str] = []
    if not pack.pack_metadata.get("demo") and not pack.description:
        issues.append("Pack lacks documentation")
    version = session.exec(select(PackVersion).where(
        PackVersion.pack_id == pack_id).order_by(PackVersion.id.desc())).first()
    if version is None:
        issues.append("No pack version")
        return {"id": pack_id, "valid": False, "issues": issues}
    declared_types = [
        s.strip() for s in (pack.pack_metadata.get("contract_types") or "").split(",")
        if s.strip()
    ]
    contract_types = [
        ct for name in declared_types
        if (ct := session.exec(
            select(ContractType).where(ContractType.name == name)).first()) is not None
    ]
    clause_count = len(session.exec(select(Clause).where(
        Clause.pack_version_id == version.id)).all())
    source_refs = session.exec(select(SourceReference).where(
        SourceReference.pack_version_id == version.id)).all()
    source_ids = [r.source_id for r in source_refs]
    approved_sources = [
        sid for sid in source_ids
        if (s := session.get(LegalSource, sid)) and s.status == "approved"
    ]
    if not declared_types:
        issues.append("No contract types declared")
    if clause_count == 0:
        issues.append("No clauses defined")
    if not approved_sources:
        issues.append("No approved sources referenced")
    missing_sections = []
    for ct in contract_types:
        section_count = len(session.exec(select(SectionDefinition).where(
            SectionDefinition.contract_type_id == ct.id)).all())
        if section_count == 0:
            missing_sections.append(ct.name)
    if missing_sections:
        issues.append(f"Contract types missing section definitions: {missing_sections}")
    return {
        "id": pack_id,
        "valid": not issues,
        "issues": issues,
    }


def set_pack_status(session: Session, pack_id: int, status: str,
                    audit_events: Optional[list] = None) -> JurisdictionPack:
    pack = session.get(JurisdictionPack, pack_id)
    if pack is None:
        raise KeyError("Pack not found")
    if status == "active":
        validation = validate_pack(session, pack_id)
        if not validation["valid"]:
            raise ValueError(f"Pack invalid for activation: {validation['issues']}")
        for other in session.exec(select(JurisdictionPack).where(
                JurisdictionPack.status == "active")).all():
            other.status = "draft"
            session.add(other)
        pack.status = "active"
    else:
        pack.status = status
    session.add(pack)
    session.commit()
    session.refresh(pack)
    return pack


def pack_diff(session: Session, pack_id: int, path: Optional[str] = None) -> Dict[str, Any]:
    if path:
        file_path = _resolve_pack_path(path)
        with open(file_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        pack = session.get(JurisdictionPack, pack_id)
        if pack is None:
            raise KeyError("Pack not found")
        file_name = f"ma-{pack.name.lower().replace(' ', '-').replace('--', '-').replace('pack', '').strip('-')}.json"
        data = {}
    return {"pack_id": pack_id, "comparison": "summary", "data": data}


def create_source(session: Session, payload: Dict[str, Any]) -> LegalSource:
    source = LegalSource(
        title=payload["title"],
        jurisdiction=payload.get("jurisdiction", "MA"),
        source_type=payload.get("source_type", "law"),
        language=payload.get("language", "fr"),
        version=payload.get("version", "1.0.0"),
        effective_date=payload.get("effective_date"),
        status="draft",
        description=payload.get("description"),
        source_metadata=payload.get("metadata", {}),
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def set_source_status(session: Session, source_id: int, status: str) -> LegalSource:
    source = session.get(LegalSource, source_id)
    if source is None:
        raise KeyError("Source not found")
    if status == "approved" and source.effective_date and str(source.effective_date).startswith("1970"):
        raise ValueError("Source with bogus effective date cannot be approved")
    source.status = status
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


def source_chunks(session: Session, source_id: int) -> List[SourceChunk]:
    source = session.get(LegalSource, source_id)
    if source is None:
        raise KeyError("Source not found")
    version = session.exec(select(LegalSourceVersion).where(
        LegalSourceVersion.source_id == source.id).order_by(
        LegalSourceVersion.id.desc())).first()
    if version is None:
        return []
    return list(session.exec(select(SourceChunk).where(
        SourceChunk.version_id == version.id).order_by(SourceChunk.chunk_index)).all())


def test_retrieval(session: Session, query: str, **kwargs) -> Dict[str, Any]:
    hits = search_sources(session, query, limit=kwargs.get("top_k", 5))
    return {"query": query, "hits": hits}


def list_sources(session: Session) -> List[LegalSource]:
    return list(session.exec(select(LegalSource).order_by(LegalSource.title)).all())


def list_sections_for_type(session: Session, contract_type_id: int) -> List[SectionDefinition]:
    return list(session.exec(select(SectionDefinition).where(
        SectionDefinition.contract_type_id == contract_type_id
    ).order_by(SectionDefinition.order_index)).all())


def list_clauses(session: Session, contract_type: Optional[str] = None,
                 jurisdiction: Optional[str] = None,
                 status: Optional[str] = None) -> List[Clause]:
    statement = select(Clause)
    if contract_type:
        statement = statement.where(Clause.contract_type == contract_type)
    if jurisdiction:
        statement = statement.where(Clause.jurisdiction == jurisdiction)
    if status:
        statement = statement.where(Clause.status == status)
    return list(session.exec(statement.order_by(Clause.title)).all())


def create_clause(session: Session, payload: Dict[str, Any]) -> Clause:
    clause = Clause(
        title=payload["title"],
        content=payload["content"],
        clause_type=payload.get("clause_type", "optional"),
        jurisdiction=payload.get("jurisdiction", "MA"),
        contract_type=payload["contract_type"],
        version=payload.get("version", "1.0.0"),
        status=payload.get("status", "draft"),
        description=payload.get("description"),
    )
    session.add(clause)
    session.commit()
    session.refresh(clause)
    return clause


def list_pack_versions(session: Session, pack_id: int) -> List[PackVersion]:
    return list(session.exec(select(PackVersion).where(
        PackVersion.pack_id == pack_id)).order_by(PackVersion.id.desc()).all())