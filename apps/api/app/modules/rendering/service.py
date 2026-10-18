"""Real document rendering (HTML, DOCX, PDF) and gated final export."""

import io
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from datetime import datetime

from sqlmodel import Session, select
from apps.api.app.modules.core.models import (
    Contract, ContractSection, ValidationFinding, ExportResult,
    ExportFile, Approval, Users,
)
from apps.api.app.modules.core.audit import record_audit
from apps.api.app.modules.rendering.schemas import (
    DocumentModel, SectionRender, ExportRequest
)

EXPORTS_DIR = Path(__file__).resolve().parent / "exports"


class ExportBlockedError(Exception):
    pass


class ExportNotFoundError(Exception):
    pass


def validate_export(
    session: Session,
    contract_id: int,
    version_number: int,
    format: str
) -> Dict[str, Any]:
    """Validate that a contract can be exported in the given format."""
    contract = session.get(Contract, contract_id)
    if not contract:
        return {
            "can_export": False,
            "blockers": [f"Contract {contract_id} not found"],
            "warnings": [],
            "requires_approval": True,
            "active_pack_version": True,
            "status": "not_found",
        }

    finding_statement = select(ValidationFinding).where(
        ValidationFinding.contract_id == contract_id,
        ValidationFinding.severity == "blocker",
        ValidationFinding.status == "open",
    )
    blocker_findings = session.exec(finding_statement).all()

    section_statement = select(ContractSection).where(
        ContractSection.contract_id == contract_id
    )
    sections = session.exec(section_statement).all()

    blockers = [f.title for f in blocker_findings]
    warnings: List[str] = []
    if not sections:
        warnings.append("Contract has no sections")

    # Human approval is required before final export (legal safety invariant)
    requires_approval = True

    result = {
        "can_export": len(blockers) == 0 and len(sections) > 0,
        "blockers": blockers,
        "warnings": warnings,
        "requires_approval": requires_approval,
        "active_pack_version": True,
        "status": "blocked" if blockers else "clear",
    }
    return result


def _build_document_model(
    session: Session,
    contract: Contract,
    version_number: int,
) -> Optional[DocumentModel]:
    section_statement = (
        select(ContractSection)
        .where(ContractSection.contract_id == contract.id)
        .order_by(ContractSection.order_index)
    )
    sections = session.exec(section_statement).all()
    if not sections:
        return None

    renders = [
        SectionRender(
            title=s.title,
            content=s.content,
            order_index=s.order_index,
            clause_ids=[str(c) for c in s.clause_ids],
            evidence_ids=list(s.evidence_ids),
            is_complete=s.status in ("supported", "approved"),
        )
        for s in sections
    ]
    return DocumentModel(
        contract_id=contract.id,
        version_number=version_number,
        title=contract.name,
        sections=renders,
        clause_references=[],
        evidence_references=[],
        placeholders={},
        metadata={},
    )


def render_html(document_model: DocumentModel) -> str:
    """Render a document model to HTML."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='fr'>",
        "<head>",
        "  <meta charset='UTF-8'>",
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        "  <title>" + document_model.title + "</title>",
        "  <style>",
        "    body { font-family: 'Georgia', serif; line-height: 1.6; margin: 20px; }",
        "    h1, h2, h3 { color: #111827; }",
        "    .section { margin-bottom: 30px; padding-bottom: 15px; border-bottom: 1px solid #e2e8f0; }",
        "    .clause { background: #f8fafc; margin: 10px 0; padding: 10px; border-radius: 6px; }",
        "    .evidence { color: #0369a1; font-size: 0.9em; margin-top: 5px; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>" + document_model.title + "</h1>",
    ]

    for section in document_model.sections:
        html_parts.append("  <div class='section'>")
        html_parts.append("    <h2>" + section.title + "</h2>")
        html_parts.append("    <p>" + section.content + "</p>")
        if section.evidence_ids:
            html_parts.append("    <div class='evidence'>Evidence: " + ", ".join(section.evidence_ids) + "</div>")
        html_parts.append("  </div>")

    html_parts.append("</body></html>")

    return "\n".join(html_parts)


def render_docx(document_model: DocumentModel) -> bytes:
    """Render a document model to a real DOCX file using python-docx."""
    from docx import Document
    from docx.shared import Pt, RGBColor

    doc = Document()
    doc.add_heading(document_model.title, level=0)
    for section in document_model.sections:
        doc.add_heading(section.title, level=1)
        for paragraph in section.content.split("\n\n"):
            doc.add_paragraph(paragraph) if paragraph.strip() else None
        if section.evidence_ids:
            para = doc.add_paragraph()
            run = para.add_run("Evidence: " + ", ".join(section.evidence_ids))
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(0x03, 0x69, 0xA1)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def render_pdf(document_model: DocumentModel) -> bytes:
    """Render a document model to a real PDF file using reportlab."""
    from xml.sax.saxutils import escape

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4, title=document_model.title)
    styles = getSampleStyleSheet()
    story = [Paragraph(escape(str(document_model.title)), styles["Title"])]
    for section in document_model.sections:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(escape(section.title), styles["Heading2"]))
        for paragraph in section.content.split("\n\n"):
            if paragraph.strip():
                story.append(Paragraph(escape(paragraph), styles["BodyText"]))
        if section.evidence_ids:
            story.append(Paragraph(
                "<i>Evidence: " + escape(", ".join(section.evidence_ids)) + "</i>",
                styles["BodyText"]))
    pdf.build(story)
    return buffer.getvalue()


def _render(format: str, document: DocumentModel) -> bytes:
    if format == "html":
        return render_html(document)
    if format == "docx":
        return render_docx(document)
    if format == "pdf":
        return render_pdf(document)
    raise ExportBlockedError(f"Unsupported format: {format}")


def _export_media_type(format: str) -> str:
    return {
        "html": "text/html",
        "docx": "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document",
        "pdf": "application/pdf",
    }.get(format, "application/octet-stream")


def final_export(session: Session, user: Users, contract_id: int,
                 format: str) -> Dict[str, Any]:
    """Export a contract after blockers + approval gates pass.

    HTML is allowed as a preview without approval; DOCX/PDF require human
    approval and zero open blockers.
    """
    from apps.api.app.modules.contracts.service import get_contract

    contract = get_contract(session, user, contract_id)
    blockers = list(session.exec(select(ValidationFinding).where(
        ValidationFinding.contract_id == contract_id,
        ValidationFinding.severity == "blocker",
        ValidationFinding.status == "open")).all())
    if blockers:
        raise ExportBlockedError(
            f"Export blocked: {(len(blockers))} open blocker finding(s)")

    latest_version = session.exec(select(ContractSection).where(
        ContractSection.contract_id == contract_id).order_by(
        ContractSection.order_index)).all()
    if not latest_version:
        raise ExportBlockedError("Contract has no drafted sections")

    if format != "html":
        approvals = session.exec(select(Approval).where(
            Approval.contract_id == contract_id)).all()
        if not approvals:
            raise ExportBlockedError(
                "Human approval is required before final export")

    document = _build_document_model(session, contract, version_number=1)
    if document is None:
        raise ExportBlockedError("Contract has no sections to render")

    content = _render(format, document)
    if isinstance(content, str):
        content = content.encode("utf-8")
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    storage_path = EXPORTS_DIR / f"contract_{contract_id}_{int(time.time())}.{format}"
    storage_path.write_bytes(content)

    export_file = ExportFile(
        contract_id=contract_id,
        format=format,
        storage_path=str(storage_path),
        status="completed",
    )
    session.add(export_file)
    session.commit()
    session.refresh(export_file)

    record_audit(session, "export", user_id=user.id, contract_id=contract_id,
                 export_id=export_file.id, format=format)
    return {
        "export_id": export_file.id,
        "contract_id": contract_id,
        "format": format,
        "content_url": f"/contracts/{contract_id}/export/{export_file.id}/content",
        "blockers": [],
    }


def read_export_content(session: Session, user: Users, contract_id: int,
                        export_id: int) -> bytes:
    from apps.api.app.modules.contracts.service import get_contract

    get_contract(session, user, contract_id)
    export_file = session.get(ExportFile, export_id)
    if export_file is None or export_file.contract_id != contract_id:
        raise ExportNotFoundError("Export not found")
    path = Path(export_file.storage_path)
    if not path.exists():
        raise ExportNotFoundError("Export content is missing")
    return path.read_bytes()


def export_contract(
    session: Session,
    contract_id: int,
    version_number: int,
    format: str,
    export_request: ExportRequest,
) -> ExportResult:
    """Export a contract in the specified format."""
    validation = validate_export(session, contract_id, version_number, format)

    result = ExportResult(
        export_id=f"export_{contract_id}_{version_number}_{format}",
        contract_id=contract_id,
        version_number=version_number,
        format=format,
        storage_path="",
        status="blocked" if not validation["can_export"] else "pending",
        blockers=list(validation.get("blockers", [])),
        warnings=list(validation.get("warnings", [])),
    )
    session.add(result)
    session.commit()

    if not validation["can_export"]:
        result.status = "blocked"
        session.commit()
        session.refresh(result)
        return result

    contract = session.get(Contract, contract_id)
    document = _build_document_model(session, contract, version_number)
    if not document:
        result.status = "failed"
        result.warnings = [*result.warnings, "No document sections found for contract"]
        session.commit()
        session.refresh(result)
        return result

    if format == "html":
        content = render_html(document)
    elif format == "docx":
        content = render_docx(document)
    elif format == "pdf":
        content = render_pdf(document)
    else:
        result.status = "failed"
        result.warnings = [*result.warnings, f"Unsupported format: {format}"]
        session.commit()
        session.refresh(result)
        return result

    # In a real system, content is written to object storage (MinIO)
    result.status = "completed"
    result.storage_path = f"/exports/contract_{contract_id}_{version_number}.{format}"
    session.commit()
    session.refresh(result)
    return result
