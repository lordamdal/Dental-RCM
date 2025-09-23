import csv
import json
import os
import re
from typing import Dict, List, Optional

from .settings import settings
from .utils import append_csv, ensure_dir, now_iso, read_csv, uid, write_csv

CASES_CSV = os.path.join(settings.DATA_DIR, 'cases.csv')
MSGS_CSV = os.path.join(settings.DATA_DIR, 'messages.csv')
DOCS_CSV = os.path.join(settings.DATA_DIR, 'documents.csv')
WORKFLOW_STATE = os.path.join(settings.DATA_DIR, 'workflow_state.json')

CASE_FIELD_ORDER = [
    'case_id',
    'title',
    'patient_name',
    'payer',
    'status',
    'reimbursement_amount',
    'reimbursement_date',
    'workflow_stage',
    'workflow_status',
    'next_action',
    'risk_level',
    'created_at',
    'updated_at',
]

MESSAGE_FIELD_ORDER = ['msg_id', 'case_id', 'role', 'content', 'created_at']
DOCUMENT_FIELD_ORDER = ['doc_id', 'case_id', 'name', 'type', 'path', 'public_url', 'uploaded_at']

STAGE_DEFAULTS = {
    'awaiting_case_start': {
        'status': 'Awaiting kickoff',
        'workflow_status': 'Let the assistant know when you are ready to start the claim.',
        'next_action': 'Tell the assistant you want to start a new case.',
    },
    'awaiting_case_details': {
        'status': 'Collecting case details',
        'workflow_status': 'Awaiting patient demographics and payer information.',
        'next_action': 'Provide case ID, patient demographics, and payer details (upload a document or type them).',
    },
    'awaiting_procedure_documents': {
        'status': 'Eligibility review',
        'workflow_status': 'Eligibility looks good—need procedure specifics to continue.',
        'next_action': 'Upload the clinical notes with ADA CDT codes.',
    },
    'awaiting_resolution_choice': {
        'status': 'Reviewing procedure requirements',
        'workflow_status': 'Two reimbursement issues identified. Awaiting direction.',
        'next_action': 'Choose how to handle the documentation issue for D7471.',
    },
    'awaiting_additional_documentation': {
        'status': 'Gathering supporting documentation',
        'workflow_status': 'Need additional MD documentation for D7471.',
        'next_action': 'Upload the MD or operative documentation supporting D7471.',
    },
    'rcm_review_pending': {
        'status': 'RCM review in progress',
        'workflow_status': 'Waiting on RCM expert feedback about the duplicate alert.',
        'next_action': 'Hold for RCM expert response.',
    },
    'awaiting_rcm_user_confirmation': {
        'status': 'RCM feedback ready',
        'workflow_status': 'Confirm the RCM recommendation about the potential duplicate.',
        'next_action': 'Confirm whether you want to proceed with the multi-location clarification.',
    },
    'awaiting_final_confirmation': {
        'status': 'Ready for finalization',
        'workflow_status': 'Awaiting confirmation to generate SOAP note and signature package.',
        'next_action': 'Confirm that you want the SOAP note prepared for signature.',
    },
    'awaiting_signed_soap_note': {
        'status': 'Waiting on signature',
        'workflow_status': 'SOAP note drafted—awaiting signed upload.',
        'next_action': 'Download the SOAP note, obtain the signature, then upload the signed copy.',
    },
    'completed': {
        'status': 'Ready to submit',
        'workflow_status': 'All documents compiled and ready for payer submission.',
        'next_action': 'Download the final package and submit to the payer.',
    },
}


def canonical_case_row(raw: Dict[str, Optional[str]]) -> Optional[Dict[str, str]]:
    """Normalize legacy CSV rows into a consistent dictionary."""
    if raw is None:
        return None

    data: Dict[str, str] = {field: '' for field in CASE_FIELD_ORDER}

    case_id = (raw.get('case_id') or '').strip()
    status_value = (raw.get('status') or '').strip()

    fallback_stage = (raw.get('workflow_stage') or '').strip()
    fallback_next_action = (raw.get('next_action') or '').strip()
    created_hint = raw.get('created_at') or fallback_next_action or now_iso()
    updated_hint = raw.get('updated_at') or raw.get('created_at') or created_hint

    if not case_id and status_value.startswith('case_'):
        case_id = status_value
        status_value = fallback_stage or 'New'
        fallback_stage = ''
        fallback_next_action = ''

    if not case_id:
        # nothing to work with; drop the row
        return None

    data['case_id'] = case_id
    data['title'] = (raw.get('title') or raw.get('patient_name') or '').strip()
    data['patient_name'] = (raw.get('patient_name') if raw.get('case_id') else '').strip()
    data['payer'] = (raw.get('payer') or '').strip()
    data['status'] = status_value or 'New'
    data['reimbursement_amount'] = (raw.get('reimbursement_amount') or '').strip()
    data['reimbursement_date'] = (raw.get('reimbursement_date') or '').strip()
    data['workflow_stage'] = fallback_stage
    data['workflow_status'] = (raw.get('workflow_status') or '').strip()
    data['next_action'] = fallback_next_action
    data['risk_level'] = (raw.get('risk_level') or '').strip()

    data['created_at'] = created_hint.strip()
    data['updated_at'] = updated_hint.strip()

    if data['next_action'] == data['created_at']:
        data['next_action'] = ''

    return data


def load_cases() -> List[Dict[str, str]]:
    if not os.path.exists(CASES_CSV):
        return []
    with open(CASES_CSV, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows: List[Dict[str, str]] = []
        for raw_row in reader:
            if not any(raw_row):
                continue
            mapping = {header[i]: raw_row[i] for i in range(min(len(header), len(raw_row)))}
            normalized = canonical_case_row(mapping)
            if normalized:
                rows.append(normalized)
        return rows


def write_cases(rows: List[Dict[str, str]]):
    if not rows:
        # still ensure the file is cleared with just a header
        ensure_dir(os.path.dirname(CASES_CSV))
        with open(CASES_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CASE_FIELD_ORDER)
            writer.writeheader()
        return

    prepared: List[Dict[str, str]] = []
    for row in rows:
        base = {field: '' for field in CASE_FIELD_ORDER}
        for key, value in row.items():
            if key in base:
                base[key] = '' if value is None else str(value)
        prepared.append(base)
    write_csv(CASES_CSV, prepared, CASE_FIELD_ORDER)


def _load_states() -> Dict[str, Dict]:
    if not os.path.exists(WORKFLOW_STATE):
        return {}
    with open(WORKFLOW_STATE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _save_states(states: Dict[str, Dict]):
    ensure_dir(os.path.dirname(WORKFLOW_STATE))
    with open(WORKFLOW_STATE, 'w', encoding='utf-8') as f:
        json.dump(states, f, indent=2)


def get_state(case_id: str) -> Dict:
    return _load_states().get(case_id, {'stage': 'awaiting_case_start', 'context': {}})


def set_state(case_id: str, stage: str, context: Optional[Dict] = None):
    states = _load_states()
    states[case_id] = {
        'stage': stage,
        'context': context or states.get(case_id, {}).get('context', {}) or {},
    }
    _save_states(states)


def update_case(case_id: str, updates: Dict[str, Optional[str]]):
    rows = load_cases()
    updated = False
    for row in rows:
        if row.get('case_id') == case_id:
            for key, value in updates.items():
                row[key] = '' if value is None else str(value)
            row['updated_at'] = now_iso()
            updated = True
    if not updated:
        return
    write_cases(rows)


def record_message(case_id: str, role: str, content: str) -> Dict:
    msg = {
        'msg_id': uid('msg'),
        'case_id': case_id,
        'role': role,
        'content': content,
        'created_at': now_iso(),
    }
    append_csv(MSGS_CSV, msg, msg.keys())
    return msg


def create_case_record(case_id: str, title: str, patient_name: Optional[str], payer: Optional[str], now: str) -> Dict[str, str]:
    row = {field: '' for field in CASE_FIELD_ORDER}
    row['case_id'] = case_id
    row['title'] = title
    row['patient_name'] = patient_name or ''
    row['payer'] = payer or ''
    row['status'] = 'New'
    row['reimbursement_amount'] = ''
    row['reimbursement_date'] = ''
    row['workflow_stage'] = ''
    row['workflow_status'] = ''
    row['next_action'] = ''
    row['risk_level'] = ''
    row['created_at'] = now
    row['updated_at'] = now
    return row


def add_case(row: Dict[str, str]):
    rows = load_cases()
    rows.append(row)
    write_cases(rows)


def normalize_case_file():
    rows = load_cases()
    if rows:
        write_cases(rows)


def delete_case_data(case_id: str):
    # Remove case row
    cases = [row for row in load_cases() if row['case_id'] != case_id]
    write_cases(cases)

    # Remove workflow state
    state = _load_states()
    if case_id in state:
        state.pop(case_id, None)
        _save_states(state)

    # Remove associated messages
    if os.path.exists(MSGS_CSV):
        rows = read_csv(MSGS_CSV)
        remaining = [r for r in rows if r.get('case_id') != case_id]
        fieldnames = list(rows[0].keys()) if rows else MESSAGE_FIELD_ORDER
        write_csv(MSGS_CSV, remaining, fieldnames)

    # Remove associated documents + files
    if os.path.exists(DOCS_CSV):
        rows = read_csv(DOCS_CSV)
        keep_rows = []
        for r in rows:
            if r.get('case_id') == case_id:
                path = r.get('path')
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            else:
                keep_rows.append(r)
        fieldnames = list(rows[0].keys()) if rows else DOCUMENT_FIELD_ORDER
        write_csv(DOCS_CSV, keep_rows, fieldnames)

    # Remove uploads directory
    uploads_dir = os.path.join(settings.DATA_DIR, 'uploads', case_id)
    if os.path.isdir(uploads_dir):
        try:
            for root, _, files in os.walk(uploads_dir, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except OSError:
                        pass
                try:
                    os.rmdir(root)
                except OSError:
                    pass
        except OSError:
            pass

def apply_stage(case_id: str, stage: str, extra: Optional[Dict[str, Optional[str]]] = None):
    payload = dict(STAGE_DEFAULTS.get(stage, {}))
    payload['workflow_stage'] = stage
    if extra:
        for key, value in extra.items():
            payload[key] = value
    update_case(case_id, payload)


def initialize_case(case_id: str, title: str):
    states = _load_states()
    if case_id in states:
        return

    context = {
        'title': title,
        'eligibility': None,
        'issues': {
            'insufficient_documentation': True,
            'duplicate': True,
        },
        'documents': {},
        'rcm_review': None,
        'reimbursement': None,
    }
    set_state(case_id, 'awaiting_case_start', context)
    apply_stage(case_id, 'awaiting_case_start')
    record_message(
        case_id,
        'assistant',
        "Hi there! I'm your reimbursement copilot. Let me know when you'd like to start a new case and I'll guide you step by step."
    )


def _kw_match(text: str, *keywords: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in keywords)


def _simulate_eligibility(case_id: str) -> Dict:
    # Deterministic dummy data
    return {
        'status': 'Likely Eligible',
        'program': 'Medicare Part B',
        'notes': 'Patient meets age requirements; confirm procedure specifics to finalize reimbursement forecast.',
    }


def _simulate_conversion() -> Dict:
    return {
        'cdt_to_cpt': {
            'D7471': {'cpt': '21040', 'modifiers': ['LT']},
            'D7955': {'cpt': '21248', 'modifiers': []},
        },
        'issues': [
            {
                'code': 'D7471',
                'type': 'documentation',
                'message': 'Supporting operative documentation is incomplete for D7471. Additional MD notes recommended.',
            },
            {
                'code': 'D7955',
                'type': 'duplicate',
                'message': 'D7955 appears to duplicate a prior submission; verify if this occurred at a different location.',
            },
        ],
    }


def _simulate_rcm_response() -> Dict:
    return {
        'expert': 'Mila (RCM expert)',
        'response': 'Confirmed the procedure occurred at a different location; proceed if the multi-site detail is documented.',
        'instructions': 'Clarify in the reimbursement request and SOAP note that D7955 reflects a second location.',
    }


def _simulate_reimbursement_forecast() -> Dict:
    return {
        'amount': 4820.00,
        'timeline': '14-21 days',
        'risk': 'Low',
        'summary': 'Eligibility and documentation complete; expect partial payment in the next three weeks.',
    }


def _generate_case_file(case_id: str, filename: str, content: str, doc_type: str = 'generated') -> Dict:
    case_dir = os.path.join(settings.DATA_DIR, 'uploads', case_id)
    ensure_dir(case_dir)
    path = os.path.join(case_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    rec = {
        'doc_id': uid('doc'),
        'case_id': case_id,
        'name': filename,
        'type': doc_type,
        'path': path,
        'uploaded_at': now_iso(),
        'public_url': f"/uploads/{case_id}/{filename}",
    }
    append_csv(DOCS_CSV, rec, rec.keys())
    return rec


def _generate_pdf(case_id: str, filename: str, text: str) -> Dict:
    # Minimal PDF writer (not full featured, but viewable)
    case_dir = os.path.join(settings.DATA_DIR, 'uploads', case_id)
    ensure_dir(case_dir)
    path = os.path.join(case_dir, filename)
    safe_text = text.replace('(', r'\(').replace(')', r'\)')
    content_stream = f"BT /F1 12 Tf 72 720 Td ({safe_text}) Tj ET"
    pdf = "\n".join([
        '%PDF-1.4',
        '1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj',
        '2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj',
        '3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >> endobj',
        f'4 0 obj << /Length {len(content_stream)} >> stream',
        content_stream,
        'endstream endobj',
        '5 0 obj << /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica >> endobj',
        'xref',
        '0 6',
        '0000000000 65535 f ',
        '0000000010 00000 n ',
        '0000000060 00000 n ',
        '0000000118 00000 n ',
        '0000000276 00000 n ',
        '0000000385 00000 n ',
        'trailer << /Size 6 /Root 1 0 R >>',
        'startxref',
        '458',
        '%%EOF',
    ])
    with open(path, 'wb') as f:
        f.write(pdf.encode('latin-1'))
    rec = {
        'doc_id': uid('doc'),
        'case_id': case_id,
        'name': filename,
        'type': 'generated-pdf',
        'path': path,
        'uploaded_at': now_iso(),
        'public_url': f"/uploads/{case_id}/{filename}",
    }
    append_csv(DOCS_CSV, rec, rec.keys())
    return rec


def handle_user_message(case_id: str, content: str) -> List[Dict]:
    state = get_state(case_id)
    stage = state.get('stage', 'awaiting_case_start')
    ctx = state.get('context', {})
    responses: List[Dict] = []

    if stage == 'awaiting_case_start':
        if _kw_match(content, 'start', 'new case', 'begin'):
            set_state(case_id, 'awaiting_case_details', ctx)
            apply_stage(case_id, 'awaiting_case_details')
            responses.append(record_message(case_id, 'assistant',
                "Perfect—let's get the case set up. Please share the case ID, patient demographics, and payer information. You can upload the patient intake document if you have it."))
        else:
            responses.append(record_message(case_id, 'assistant',
                "Whenever you're ready, just let me know you want to start a new case and we'll walk through it together."))

    elif stage == 'awaiting_case_details':
        responses.append(record_message(case_id, 'assistant',
            "I'm ready to load the patient information once you upload or enter it. The case tracker will stay in sync as we go."))

    elif stage == 'awaiting_procedure_documents':
        responses.append(record_message(case_id, 'assistant',
            "Once you upload the clinical notes with ADA CDT codes, I'll convert them to CPT and run the reimbursement checks."))

    elif stage == 'awaiting_resolution_choice':
        choice = None
        if _kw_match(content, 'option 1', 'upload', 'more documentation', 'additional documentation'):
            choice = 'upload'
        elif _kw_match(content, 'option 2', 'remove'):
            choice = 'remove'
        elif _kw_match(content, 'option 3', 'submit without'):
            choice = 'submit_without'
        elif _kw_match(content, 'option 4', 'exit', 'restart', 'later'):
            choice = 'exit'

        if choice == 'upload':
            set_state(case_id, 'awaiting_additional_documentation', ctx)
            apply_stage(case_id, 'awaiting_additional_documentation')
            responses.append(record_message(case_id, 'assistant',
                "Great choice. Please upload the MD or operative documentation that supports procedure D7471."))
        elif choice == 'remove':
            ctx.setdefault('actions', {})['removed_procedure'] = True
            set_state(case_id, 'awaiting_rcm_user_confirmation', ctx)
            responses.append(record_message(case_id, 'assistant',
                "Understood. I'll note that procedure D7471 will be removed. For D7955, I'll still loop in Mila from the RCM team to double-check the duplicate risk."))
            responses.extend(_complete_rcm_review(case_id, ctx))
        elif choice == 'submit_without':
            ctx.setdefault('actions', {})['submit_without_support'] = True
            set_state(case_id, 'awaiting_rcm_user_confirmation', ctx)
            responses.append(record_message(case_id, 'assistant',
                "Okay, I'll proceed without supplemental documentation, but let's have an RCM expert weigh in on the duplicate concern before we finalize."))
            responses.extend(_complete_rcm_review(case_id, ctx))
        elif choice == 'exit':
            set_state(case_id, 'awaiting_case_start', ctx)
            apply_stage(case_id, 'awaiting_case_start', {
                'status': 'On hold',
                'workflow_status': 'Paused—let me know when you want to restart the case.',
                'next_action': 'Tell the assistant when you are ready to continue.',
            })
            responses.append(record_message(case_id, 'assistant',
                "No problem. The case is paused. Let me know when you are ready to pick it back up."))
        else:
            responses.append(record_message(case_id, 'assistant',
                "To keep things moving, choose one of the options: upload more documentation, remove the procedure, submit as-is, or pause the case."))

    elif stage == 'awaiting_additional_documentation':
        responses.append(record_message(case_id, 'assistant',
            "Upload the MD documentation for D7471 when ready and I'll take another look."))

    elif stage == 'awaiting_rcm_user_confirmation':
        if _kw_match(content, 'yes', 'proceed', 'ok', 'okay', 'confirm'):
            forecast = _simulate_reimbursement_forecast()
            ctx['reimbursement'] = forecast
            set_state(case_id, 'awaiting_final_confirmation', ctx)
            apply_stage(case_id, 'awaiting_final_confirmation', {
                'reimbursement_amount': forecast['amount'],
                'reimbursement_date': f"{forecast['timeline']} (projected)",
                'risk_level': forecast['risk'],
            })
            msg = (
                f"Based on the documentation and RCM feedback, the projected reimbursement is ${forecast['amount']:,.2f} with an expected payment window of {forecast['timeline']} (risk level: {forecast['risk']}). "
                "Shall I prepare the SOAP note for final review and signatures?"
            )
            responses.append(record_message(case_id, 'assistant', msg))
        elif _kw_match(content, 'no', 'not yet'):
            responses.append(record_message(case_id, 'assistant',
                "Okay, I'll hold. Let me know when you're ready to move forward with the RCM recommendation."))
        else:
            responses.append(record_message(case_id, 'assistant',
                "Please confirm if you're okay proceeding with the RCM expert's recommendation so we can wrap this up."))

    elif stage == 'awaiting_final_confirmation':
        if _kw_match(content, 'yes', 'proceed', 'ok', 'okay', 'confirm'):
            soap = _generate_case_file(
                case_id,
                'Deborah SOAP Note for Dr Review.doc',
                "SOAP Note Draft\nPatient: Deborah McCormick\nSummary: Auto-generated draft for physician review.",
                doc_type='generated-soap',
            )
            ctx['documents']['soap_note'] = soap['doc_id']
            set_state(case_id, 'awaiting_signed_soap_note', ctx)
            apply_stage(case_id, 'awaiting_signed_soap_note')
            responses.append(record_message(case_id, 'assistant',
                "I've generated the SOAP note for Dr. review. Download it from the documents panel, get it signed, and upload the signed version when it's ready."))
        elif _kw_match(content, 'no', 'not yet'):
            responses.append(record_message(case_id, 'assistant',
                "No problem—just let me know when you'd like me to prepare the SOAP note."))
        else:
            responses.append(record_message(case_id, 'assistant',
                "Should I generate the SOAP note for doctor review and signature now?"))

    elif stage == 'awaiting_signed_soap_note':
        responses.append(record_message(case_id, 'assistant',
            "Once the signed SOAP note is uploaded, I'll generate the remaining submission package automatically."))

    elif stage == 'completed':
        responses.append(record_message(case_id, 'assistant',
            "This case is ready to submit. Let me know if you need any additional summaries or follow-up steps."))

    else:
        responses.append(record_message(case_id, 'assistant',
            "I'm tracking the workflow—let me know if you need help with the next action listed in the dashboard."))

    state = get_state(case_id)
    state['context'] = ctx
    set_state(case_id, state.get('stage', stage), ctx)
    return responses


def _complete_rcm_review(case_id: str, ctx: Dict) -> List[Dict]:
    responses: List[Dict] = []
    set_state(case_id, 'rcm_review_pending', ctx)
    apply_stage(case_id, 'rcm_review_pending')
    responses.append(record_message(case_id, 'assistant',
        "Routing the case to Mila from the RCM team to confirm the duplicate alert. I'll update you as soon as I hear back."))

    rcm = _simulate_rcm_response()
    ctx['rcm_review'] = rcm
    system_note = (
        f"RCM Expert {rcm['expert']} responded: {rcm['response']} Recommendation: {rcm['instructions']}"
    )
    responses.append(record_message(case_id, 'system', system_note))

    set_state(case_id, 'awaiting_rcm_user_confirmation', ctx)
    apply_stage(case_id, 'awaiting_rcm_user_confirmation')
    responses.append(record_message(case_id, 'assistant',
        "Mila confirmed the procedure happened at a different location. Are you okay moving forward by clarifying that multiple sites were involved in the reimbursement submission and SOAP note?"))
    return responses


def handle_document_upload(case_id: str, doc: Dict) -> List[Dict]:
    state = get_state(case_id)
    stage = state.get('stage', 'awaiting_case_start')
    ctx = state.get('context', {})
    responses: List[Dict] = []

    if stage == 'awaiting_case_details':
        ctx.setdefault('documents', {})['patient_info'] = doc['doc_id']
        ctx['case_details_provided'] = True
        eligibility = _simulate_eligibility(case_id)
        ctx['eligibility'] = eligibility
        set_state(case_id, 'awaiting_procedure_documents', ctx)
        apply_stage(case_id, 'awaiting_procedure_documents')
        responses.append(record_message(case_id, 'assistant',
            "Patient information has been loaded into the dashboard. As you keep adding documents the status will stay updated automatically."))
        responses.append(record_message(case_id, 'assistant',
            "I'll start with a Medicare eligibility check now."))
        responses.append(record_message(case_id, 'system',
            f"Medicare eligibility check complete: {eligibility['status']} ({eligibility['notes']})"))
        responses.append(record_message(case_id, 'assistant',
            "The patient appears eligible, but I need the clinical notes and ADA CDT codes to project reimbursement and spot any issues."))

    elif stage == 'awaiting_procedure_documents':
        ctx.setdefault('documents', {})['clinical_notes'] = doc['doc_id']
        conversion = _simulate_conversion()
        ctx['conversion'] = conversion
        set_state(case_id, 'awaiting_resolution_choice', ctx)
        apply_stage(case_id, 'awaiting_resolution_choice')
        responses.append(record_message(case_id, 'assistant',
            "Thanks for the notes. I've converted the ADA CDT codes to CPT and applied the Medicare policy rules."))
        responses.append(record_message(case_id, 'system',
            "Reimbursement rules check flag: D7471 requires additional supporting documentation; D7955 may be a duplicate."))
        responses.append(record_message(case_id, 'assistant',
            "Two items need attention before we finalize: 1) D7471 may lack sufficient supporting documentation. 2) D7955 might be a duplicate.\n"
            "For the first item, choose one of the following options:\n"
            "1. Upload additional clinical documentation\n2. Remove the procedure from the reimbursement request\n3. Submit without fully supporting it (higher risk)\n4. Exit the case and restart later"))

    elif stage == 'awaiting_additional_documentation':
        ctx.setdefault('documents', {})['additional_md'] = doc['doc_id']
        set_state(case_id, 'rcm_review_pending', ctx)
        apply_stage(case_id, 'rcm_review_pending')
        responses.append(record_message(case_id, 'assistant',
            "The additional documentation looks good and covers the D7471 requirements."))
        responses.append(record_message(case_id, 'assistant',
            "Regarding the duplicate alert on D7955, I'm looping in Mila from the RCM team for a quick review. The case will stay paused until we hear back."))
        responses.extend(_complete_rcm_review(case_id, ctx))

    elif stage == 'awaiting_signed_soap_note':
        ctx.setdefault('documents', {})['signed_soap'] = doc['doc_id']
        package_pdf = _generate_pdf(case_id, 'Deborah_McCormick_1500.pdf', 'CMS 1500 package ready for submission')
        package_summary = _generate_case_file(
            case_id,
            'Deborah SOAP Note for Dr Review - Final Package.txt',
            "Final package includes: Signed SOAP note, Operative note, CMS 1500/837I summary.",
            doc_type='generated-summary',
        )
        ctx.setdefault('documents', {})['final_package'] = package_pdf['doc_id']
        ctx.setdefault('documents', {})['final_summary'] = package_summary['doc_id']
        set_state(case_id, 'completed', ctx)
        apply_stage(case_id, 'completed')
        responses.append(record_message(case_id, 'assistant',
            "Signed SOAP note received—thank you."))
        responses.append(record_message(case_id, 'assistant',
            "I've generated the full reimbursement package including the CMS 1500/837 output. It's ready to submit to the payer when you are."))

    else:
        responses.append(record_message(case_id, 'assistant',
            "Document received. I'll keep it on file."))

    set_state(case_id, get_state(case_id).get('stage'), ctx)
    return responses
