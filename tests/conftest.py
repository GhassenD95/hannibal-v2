"""Shared test setup: ensure schema exists and minimal seed data is present.

Tests exercise the API against the real PostgreSQL database used by the
application (no separate test database), so the schema and a minimal
contract row are guaranteed here at import time.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select, text

from apps.api.app.modules.core.db import create_db_and_tables, engine
from apps.api.app.modules.core.models import (
    Contract, ContractSection, Organizations, Role, UserRole, Users
)
from apps.api.app.modules.auth.security import get_password_hash


REQUIRED_SECTION_TITLES = [
    "Parties",
    "Payment",
    "Termination",
    "Governing Law",
]

ADMIN_EMAIL = "admin@hannibal.local"
ADMIN_PASSWORD = "admin123"


def _ensure_auth_seed() -> None:
    with Session(engine) as session:
        org1 = session.get(Organizations, 1)
        if org1 is None:
            session.add(Organizations(id=1, name="Hannibal Demo",
                                      description="Demo organization"))
        org2 = session.get(Organizations, 2)
        if org2 is None:
            session.add(Organizations(id=2, name="OtherCo",
                                      description="Isolated organization"))
        session.commit()

        for name in ("admin", "reviewer", "drafter", "viewer"):
            role = session.exec(select(Role).where(Role.name == name)).first()
            if role is None:
                session.add(Role(name=name))

        users = [
            (ADMIN_EMAIL, ADMIN_PASSWORD, "Admin User", 1, ["admin", "reviewer"]),
            ("drafter@hannibal.local", "drafter123", "Drafter User", 1, ["drafter"]),
            ("reviewer@other.local", "reviewer123", "Reviewer Other", 2, ["reviewer"]),
        ]
        for email, password, full_name, org_id, roles in users:
            user = session.exec(select(Users).where(Users.email == email)).first()
            if user is None:
                user = Users(
                    email=email,
                    hashed_password=get_password_hash(password),
                    full_name=full_name,
                    organization_id=org_id,
                    is_active=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            existing_roles = session.exec(
                select(UserRole.role_id).where(UserRole.user_id == user.id)
            ).all()
            for role_name in roles:
                role = session.exec(select(Role).where(Role.name == role_name)).first()
                if role and role.id not in existing_roles:
                    session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()

        contract = session.get(Contract, 1)
        if contract is not None and contract.organization_id is None:
            contract.organization_id = 1
            session.add(contract)
            session.commit()


def _sync_id_sequences(session: Session) -> None:
    """Align postgres id sequences with rows inserted using explicit ids."""
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


def _ensure_contract_1() -> None:
    with Session(engine) as session:
        contract = session.get(Contract, 1)
        if contract is None:
            contract = Contract(
                id=1,
                name="Service Agreement",
                description="Service agreement for testing",
                contract_type="service_agreement",
                jurisdiction="MA",
                language="fr",
                status="draft",
            )
            session.add(contract)
            session.commit()
            session.refresh(contract)

        sections = session.exec(
            select(ContractSection).where(ContractSection.contract_id == 1)
        ).all()
        if not sections:
            for index, title in enumerate(REQUIRED_SECTION_TITLES):
                session.add(
                    ContractSection(
                        contract_id=1,
                        title=title,
                        content=f"{title} clause content for the service agreement.",
                        order_index=index,
                        clause_ids=[1, 2, 3],
                        evidence_ids=["src_1"],
                        status="supported",
                    )
                )
            session.commit()

        _sync_id_sequences(session)


def _ensure_active_pack() -> None:
    from apps.api.app.modules.admin.service import import_pack
    from apps.api.app.modules.core.models import PackVersion as PV
    with Session(engine) as session:
        for pack_file in ("ma-service-agreement.json", "ma-nda.json",
                          "tn-service-agreement.json", "tn-nda.json"):
            pack = import_pack(session, pack_file)
            pack.status = "active"
            session.add(pack)
            session.commit()
            session.refresh(pack)
            version = session.exec(
                select(PV).where(PV.pack_id == pack.id).order_by(PV.id.desc())
            ).first()
            version.status = "active"
            session.add(version)
            session.commit()


def _ensure_extra_columns() -> None:
    """Additive migrations for tables that predate the current models."""
    with Session(engine) as session:
        statements = [
            "ALTER TABLE contract ADD COLUMN IF NOT EXISTS organization_id INTEGER",
            "ALTER TABLE contractrequest ADD COLUMN IF NOT EXISTS organization_id INTEGER",
            "ALTER TABLE contract ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
            "ALTER TABLE contract ADD COLUMN IF NOT EXISTS created_at TIMESTAMP",
            "ALTER TABLE negotiationitem ADD COLUMN IF NOT EXISTS proposed_text TEXT",
        ]
        for statement in statements:
            session.connection().exec_driver_sql(statement)
        session.commit()


create_db_and_tables()
_ensure_extra_columns()
_ensure_auth_seed()
_ensure_active_pack()
_ensure_contract_1()
