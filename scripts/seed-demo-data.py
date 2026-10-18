#!/usr/bin/env python3
"""Seed demo data for Hannibal V2. Idempotent: safe to re-run."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime

from sqlmodel import Session, select, text

from apps.api.app.main import engine, create_db_and_tables
from apps.api.app.modules.core.models import (
    Users, Organizations, Role, UserRole,
    JurisdictionPack, PackVersion,
    ContractType, IntakeSchema, IntakeField,
    LegalSource, LegalSourceVersion, SourceChunk, SourceReference,
    Clause, ClausePreference,
    ContractRequest, Contract, ContractSection,
    ValidationFinding, RiskFinding,
    NegotiationItem, Approval, ExportFile, AuditEvent
)
from apps.api.app.modules.auth.security import get_password_hash


def sync_id_sequences(session: Session) -> None:
    """Align postgres id sequences with existing rows (explicit-id inserts desync them)."""
    tables = session.exec(text(
        "SELECT c.table_name FROM information_schema.columns c "
        "JOIN pg_tables t ON t.tablename = c.table_name AND t.schemaname = c.table_schema "
        "WHERE c.table_schema = 'public' AND c.column_name = 'id'"
    )).all()
    for (table,) in tables:
        seq = session.connection().exec_driver_sql(
            f"SELECT pg_get_serial_sequence('{table}', 'id')"
        ).scalar()
        if seq:
            session.connection().exec_driver_sql(
                f"SELECT setval('{seq}', "
                f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
            )
    session.commit()


def get_or_create(session: Session, model, defaults=None, **kwargs):
    statement = select(model)
    for key, value in kwargs.items():
        statement = statement.where(getattr(model, key) == value)
    instance = session.exec(statement).first()
    if instance:
        return instance
    params = {**(defaults or {}), **kwargs}
    instance = model(**params)
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def seed_demo_data():
    """Seed demo jurisdiction pack, sources, and contract types."""
    session = Session(engine)
    sync_id_sequences(session)

    # Organization
    org = get_or_create(
        session, Organizations,
        name="Hannibal Legal",
        defaults={"description": "Legal contract reasoning engine"},
    )

    # Roles
    for role_name in ("admin", "reviewer", "drafter", "viewer"):
        role = get_or_create(session, Role, name=role_name,
                             defaults={"description": role_name})

    # Admin user
    admin = get_or_create(
        session, Users,
        email="admin@hannibal.local",
        defaults={
            "hashed_password": get_password_hash("admin123"),
            "full_name": "Hannibal Admin",
            "organization_id": org.id,
            "is_active": True,
        },
    )
    for src in ("admin", "reviewer"):
        role = get_or_create(session, Role, name=src)
        if not session.exec(select(UserRole).where(
                UserRole.user_id == admin.id, UserRole.role_id == role.id)).first():
            session.add(UserRole(user_id=admin.id, role_id=role.id))
    session.commit()

    # Jurisdiction pack imported from versioned legal-packs JSON (docs/03)
    from apps.api.app.modules.admin.service import load_pack_data
    import json

    pack = None
    clauses = []
    sources = []
    for pack_file in (
        "ma-service-agreement.json",
        "ma-nda.json",
        "tn-service-agreement.json",
        "tn-nda.json",
    ):
        pack_path = Path(__file__).resolve().parents[1] / "legal-packs" / pack_file
        with open(pack_path, encoding="utf-8") as fh:
            data = json.load(fh)
        imported = load_pack_data(session, data)
        imported.status = "active"
        session.add(imported)
        session.commit()
        session.refresh(imported)
        pack = imported
        pv = session.exec(
            select(PackVersion).where(PackVersion.pack_id == imported.id).order_by(
                PackVersion.id.desc())
        ).first()
        pv.status = "active"
        session.add(pv)
        session.commit()
    clauses = session.exec(select(Clause).order_by(Clause.id)).all()
    sources = session.exec(select(LegalSource).order_by(LegalSource.id)).all()


    # Contract request sample
    cr = get_or_create(
        session, ContractRequest,
        name="Sample Service Agreement",
        defaults={
            "description": "12-month service agreement between TechCo and ServiceProvider",
            "contract_type": "service_agreement",
            "jurisdiction": "MA",
            "language": "fr",
            "facts": {
                "parties": "TechCo and ServiceProvider",
                "duration": "12 months",
                "amount": "20000 MAD",
                "currency": "MAD",
            },
            "selected_clauses": [c.id for c in clauses[:3]],
            "evidence_ids": [],
            "status": "complete",
        },
    )

    # Demo contract
    contract = get_or_create(
        session, Contract,
        name="Service Agreement - TechCo/ServiceProvider",
        defaults={
            "description": "12-month IT services agreement",
            "contract_type": "service_agreement",
            "jurisdiction": "MA",
            "language": "fr",
            "status": "draft",
            "request_id": cr.id,
        },
    )

    # Contract sections
    sections_data = [
        {"title": "Parties", "content": "Parties: TechCo and ServiceProvider"},
        {"title": "Scope", "content": "IT services for duration of 12 months"},
        {"title": "Payment", "content": "20,000 MAD per month, two installments"},
        {"title": "Confidentiality", "content": "Confidentiality obligations"},
        {"title": "IP", "content": "IP transfer terms"},
        {"title": "Termination", "content": "30-day termination notice"},
        {"title": "Liability", "content": "Liability limitations"},
        {"title": "Governing Law", "content": "Moroccan law governs this agreement"},
        {"title": "Signatures", "content": "Signatures of both parties"},
    ]
    sections = session.exec(
        select(ContractSection).where(ContractSection.contract_id == contract.id)
    ).all()
    if not sections:
        for i, sd in enumerate(sections_data, 1):
            session.add(ContractSection(
                contract_id=contract.id,
                title=sd["title"],
                content=sd["content"],
                order_index=i,
                clause_ids=[c.id for c in clauses[:3]],
                evidence_ids=[],
                status="supported" if i <= 4 else "needs_review",
            ))
        session.commit()

    # Validation findings
    get_or_create(
        session, ValidationFinding,
        contract_id=contract.id, rule_id="currency.consistent", title="Currency consistency",
        defaults={
            "severity": "blocker",
            "explanation": "Ensure amount and currency are consistent",
            "location": "payment",
            "recommendation": "Verify MAD amount matches currency field",
            "status": "open",
        },
    )
    get_or_create(
        session, ValidationFinding,
        contract_id=contract.id, rule_id="clause.approved", title="No approved clause in Liability section",
        defaults={
            "severity": "high",
            "explanation": "Liability section lacks approved clause",
            "location": "liability",
            "recommendation": "Select approved liability clause from library",
            "status": "open",
        },
    )

    # Risk finding
    get_or_create(
        session, RiskFinding,
        contract_id=contract.id, title="Liability is uncapped",
        defaults={
            "severity": "high",
            "explanation": "The current wording does not establish a maximum liability amount.",
            "location": "liability",
            "recommendation": "Use preferred clause with liability cap",
            "status": "open",
        },
    )

    # Negotiation item
    liability_section = session.exec(
        select(ContractSection).where(
            ContractSection.contract_id == contract.id,
            ContractSection.title == "Liability",
        )
    ).first()
    get_or_create(
        session, NegotiationItem,
        contract_id=contract.id,
        section_id=liability_section.id if liability_section else None,
        defaults={
            "counterparty_clause": "Liability capped at 10% of contract value",
            "hannibal_analysis": "Counterparty proposes capped liability",
            "status": "pending",
        },
    )

    # Approval
    get_or_create(
        session, Approval,
        contract_id=contract.id, approval_type="human",
        defaults={
            "approver_id": 1,
            "notes": "Initial review - blockers need resolution",
        },
    )

    # Export file record
    get_or_create(
        session, ExportFile,
        contract_id=contract.id, format="html",
        defaults={
            "storage_path": "/exports/service_agreement.html",
            "status": "pending",
        },
    )

    # Audit event
    get_or_create(
        session, AuditEvent,
        contract_id=contract.id, event_type="creation",
        defaults={
            "event_data": {"created": "seed_demo_data"},
            "user_id": 1,
        },
    )

    print("Demo data seeded successfully!")
    print(f"- Jurisdiction packs: Morocco 1.0.0, Tunisia 1.0.0")
    print(f"- Contract types: service_agreement, nda")
    print(f"- Approved clauses: {len(clauses)}")
    print(f"- Legal sources: {len(sources)} sources")
    print(f"- Contract: {contract.name} (ID: {contract.id})")
    print(f"- Sections: {len(sections_data)} section titles")

    session.close()


if __name__ == "__main__":
    create_db_and_tables()
    seed_demo_data()
