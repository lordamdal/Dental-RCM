import csv
import json
import logging
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

ADA_CODES_FILE = os.path.join(settings.DATA_DIR, 'ada_codes.csv')
ADA_CODE_PATTERN = re.compile(r'\bD\d{4}\b', re.IGNORECASE)

logger = logging.getLogger(__name__)

_ADA_CODES_CACHE: Dict[str, str] = {}
_ADA_CODES_MTIME: float | None = None

SOAP_SAMPLE = """VINCENT W. H. WANG DDS INC\n572 E Green St, Ste 205, Pasadena, CA 91101\n\nPatient Name: MCCORMICK, DEBORAH A.\nDOB: 12/18/1951\nGender: Female\nPrimary Payor: Medicare CA - Southern California\nMBI/Primary #: 4VR1M50JQ34\nService Date (DOS): 10/06/2023\nMR/Chart ID / Patient Account #: M98593279\nReferring/Attending Provider: Vincent W. H. Wang, DDS (NPI 1366503385)\n\nSOAP NOTE (Operative Visit)\n\nS - Subjective\n- Chief Complaint: "My jaw hurts and my bite feels off. Hard to chew on the left."\n- HPI: 72-year-old female with chronic jaw pain and malocclusion, progressively worsening over ~12 months. Pain 6/10 with mastication; improved with soft diet and OTC ibuprofen. Intermittent left maxillary sinus pressure. Denies fever, trismus, dysphagia, or recent dental abscess.\n- ROS: Negative for chest pain, dyspnea, bleeding disorders. Positive for intermittent sinus pressure as above; otherwise non-contributory.\n- PMH (training assumption): Hypertension (controlled), hyperlipidemia; no history of bleeding disorder; no bisphosphonate use; no prior head & neck radiation. ASA class II.\n- Meds (training assumption): Lisinopril 10 mg daily; Atorvastatin 20 mg nightly; Vitamin D/calcium; Ibuprofen 200 mg as needed.\n- Allergies: No known drug allergies (NKDA).\n- Social: Non-smoker; occasional wine; lives independently.\n\nO - Objective\n- Vitals (pre-op): BP 128/76 mmHg, HR 74 bpm, Temp 98.1 F, SpO2 98% RA, BMI not assessed.\n- Exam findings:\n  * Maxillary ridge deficiency with tenderness along the right edentulous ridge.\n  * Mandibular alveolar irregularities with two lateral exostoses causing occlusal interference and mucosal irritation.\n  * Left posterior mandible with palpable submucosal foreign material; mucosa intact without purulence.\n  * Occlusion: malocclusion with reduced vertical dimension; no trismus.\n  * Imaging/Studies: Prior panoramic/CBCT consistent with ridge atrophy, mandibular exostoses, and left maxillary sinus changes; no acute osteomyelitis.\n\nAnesthesia & Peri-op Management (training assumption)\n- Technique: Local anesthesia with minimal sedation.\n- Local: 2% lidocaine with 1:100,000 epi (4 cartridges, 7.2 mL) via infiltrations + IAN block; 0.5% bupivacaine with 1:200,000 epi (1 cartridge, 1.8 mL) for post-op analgesia.\n- Sedation: Oral triazolam 0.25 mg pre-procedure + nitrous oxide 30% titrated; continuous pulse oximetry; BP every 5 minutes; suction/oxygen available; NPO 6 hours confirmed.\n- Antisepsis: 0.12% chlorhexidine rinse pre-op; sterile drape; PPE per protocol.\n\nO - Procedures Performed (CPT with analogous CDT mapping)\n- 21210: Bone graft, maxilla (right ridge) (CDT D7950).\n  * Decortication; placement of allogeneic cortico-cancellous particulate graft (~1.5 cc) with resorbable collagen membrane (15x20 mm). Primary closure with 4-0 chromic.\n- 21209: Chin augmentation with bone graft (CDT D7994; distinct site).\n  * Onlay augmentation using autogenous shavings (bone scraper) blended with allograft; secured to symphysis; layered closure with 4-0 Vicryl.\n- 21026 x2: Excision of mandibular exostoses (CDT D7472).\n  * Removal of two separate bony prominences causing prosthetic/occlusal interference.\n- 10120 x2: Removal of foreign body, subcutaneous/osseous (CDT D7296).\n  * Two retained fragments excised from left posterior mandible via separate incision; copious irrigation.\n- 31020: Surgical sinusotomy, left maxillary (CDT D7953 analog).\n  * Restored ostial patency and sinus floor support to aid graft integration; hemostasis achieved.\n- 40800: Excision of vestibule of mouth (anterior mandible) (CDT D7471).\n  * Limited vestibuloplasty/soft-tissue excision for prosthetic preparation; straightforward closure.\n\nOther Intra-op Details\n- Estimated Blood Loss: ~20 mL.\n- Fluids: PO as tolerated post-op.\n- Specimens: None submitted.\n- Complications: None.\n- Counts: Instruments/gauze/sutures correct at case end.\n\nA - Assessment\n- R68.84: Jaw pain.\n- M26.4: Malocclusion of teeth.\n- Post-op condition stable; pain controlled; no immediate complications.\n\nP - Plan\n- Medications:\n  * Amoxicillin 500 mg PO TID x7 days.\n  * Ibuprofen 600 mg PO every 6 hours as needed (max 2400 mg/day); may alternate with Acetaminophen 500 mg every 6 hours as needed (max 3000 mg/day).\n  * Chlorhexidine 0.12% rinse 15 mL BID for 7-10 days (avoid eating/drinking for 30 minutes after use).\n- Post-op Instructions: Ice 20 minutes on/off first 24 hours; head elevation; soft diet for 48-72 hours; avoid vigorous rinsing or straws for 24 hours; no smoking. For sinusotomy: no nose blowing for 10 days, sneeze with mouth open, use OTC saline spray as needed. Call for fever >101.5 F, uncontrolled pain/bleeding, or expanding swelling. Written instructions provided.\n- Follow-Up: 10-14 days for suture check and healing evaluation; sooner as needed.\n- Return Precautions: As above; 24-hour on-call number provided.\n- Billing/Coding Summary: 21210; 21209; 21026 x2; 10120 x2; 31020; 40800 linked to R68.84, M26.4.\n\nProvider: Vincent W. H. Wang, DDS\nSignature: _________________________\nDate: _________________________"""

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
    'submitted': {
        'status': 'Submitted',
        'workflow_status': 'Claim has been submitted to the payer.',
        'next_action': 'Monitor for payer response and EOB.',
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


def _choice_from_text(text: str) -> Optional[str]:
    """Map user freeform text to a numbered resolution choice.
    Returns one of: 'upload', 'remove', 'submit_without', 'exit' or None.
    Accepts: 1/2/3/4, 'option 1', 'one', unicode numerals, etc.
    """
    if not text:
        return None
    s = text.strip().lower()
    # quick win: extract leading digit
    import re
    m = re.match(r"\s*(?:option\s*)?(\d)[\).\s]*", s)
    if m:
        d = m.group(1)
        if d == '1':
            return 'upload'
        if d == '2':
            return 'remove'
        if d == '3':
            return 'submit_without'
        if d == '4':
            return 'exit'
    # spelled numbers / unicode circled
    if s in {'one', '①', '❶'}:
        return 'upload'
    if s in {'two', '②', '❷'}:
        return 'remove'
    if s in {'three', '③', '❸'}:
        return 'submit_without'
    if s in {'four', '④', '❹'}:
        return 'exit'
    return None


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
    case_dir = os.path.join(settings.DATA_DIR, 'uploads', case_id)
    ensure_dir(case_dir)
    path = os.path.join(case_dir, filename)

    lines = text.splitlines()
    text_commands = ["BT", "/F1 11 Tf", "16 TL", "72 760 Td"]
    for line in lines:
        safe = line.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')
        text_commands.append(f"({safe}) Tj")
        text_commands.append("T*")
    text_commands.append("ET")

    signature_y = 140
    signature_commands = [
        "BT",
        "/F1 11 Tf",
        f"72 {signature_y + 40} Td",
        "(Provider: Vincent W. H. Wang, DDS) Tj",
        "T*",
        "(Signature: _________________________) Tj",
        "T*",
        "(Date: _________________________) Tj",
        "ET",
        f"72 {signature_y} m",
        "360 {signature_y} l",
        "S",
    ]

    content_stream = "\n".join(text_commands + signature_commands)
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
        '0000000426 00000 n ',
        'trailer << /Size 6 /Root 1 0 R >>',
        'startxref',
        '498',
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


def _get_ada_codes() -> Dict[str, str]:
    global _ADA_CODES_CACHE, _ADA_CODES_MTIME
    try:
        current_mtime = os.path.getmtime(ADA_CODES_FILE)
    except FileNotFoundError:
        if _ADA_CODES_CACHE:
            logger.warning("ADA codes file missing at %s", ADA_CODES_FILE)
        _ADA_CODES_CACHE = {}
        _ADA_CODES_MTIME = None
        return {}

    if _ADA_CODES_CACHE and _ADA_CODES_MTIME == current_mtime:
        return _ADA_CODES_CACHE

    codes: Dict[str, str] = {}
    try:
        with open(ADA_CODES_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get('code') or row.get('Code') or '').strip().upper()
                description = (row.get('description') or row.get('Description') or '').strip()
                if not code or not description:
                    continue
                codes[code] = description
    except Exception as exc:
        logger.error("Failed to load ADA codes: %%s", exc)
        codes = {}

    _ADA_CODES_CACHE = codes
    _ADA_CODES_MTIME = current_mtime
    return codes


def _ada_code_responses(case_id: str, content: str) -> List[Dict]:
    codes_lookup = _get_ada_codes()
    matches = {code.upper() for code in ADA_CODE_PATTERN.findall(content or '')}
    if not matches:
        return []

    known = sorted(code for code in matches if code in codes_lookup)
    unknown = sorted(code for code in matches if code not in codes_lookup)
    responses: List[Dict] = []

    if known:
        lines = "\n".join(f"- {code}: {codes_lookup[code]}" for code in known)
        message = "Here is what I have on the ADA codes you mentioned:\n" + lines
        responses.append(record_message(case_id, 'assistant', message))

    if unknown:
        note = "I do not have details on the following codes yet: " + ", ".join(unknown) + ". If you have clinical notes for them, upload those and I can keep the case moving."
        responses.append(record_message(case_id, 'assistant', note))

    return responses


def handle_user_message(case_id: str, content: str) -> List[Dict]:
    state = get_state(case_id)
    stage = state.get('stage', 'awaiting_case_start')
    ctx = state.get('context', {})
    responses: List[Dict] = []

    responses.extend(_ada_code_responses(case_id, content))

    if stage == 'awaiting_case_start':
        if _kw_match(content, 'start', 'new case', 'begin', 'ready', "i'm ready", 'i am ready', 'new patient', 'file a claim', 'medicare', 'help'):
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
        choice = _choice_from_text(content)
        if not choice:
            if _kw_match(content, 'option 1', 'upload', 'more documentation', 'additional documentation'):
                choice = 'upload'
            elif _kw_match(content, 'option 2', 'remove'):
                choice = 'remove'
            elif _kw_match(content, 'option 3', 'submit without'):
                choice = 'submit_without'
            elif _kw_match(content, 'option 4', 'exit', 'restart', 'later', 'pause'):
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
                'Deborah SOAP Note for Dr Review.txt',
                SOAP_SAMPLE,
                doc_type='generated-soap',
            )
            soap_pdf = _generate_pdf(
                case_id,
                'Deborah SOAP Note for Dr Review.pdf',
                SOAP_SAMPLE,
            )
            ctx['documents']['soap_note'] = soap['doc_id']
            ctx['documents']['soap_note_pdf'] = soap_pdf['doc_id']
            set_state(case_id, 'awaiting_signed_soap_note', ctx)
            apply_stage(case_id, 'awaiting_signed_soap_note')
            text_path = soap.get('public_url') or soap.get('path') or ''
            pdf_path = soap_pdf.get('public_url') or soap_pdf.get('path') or ''
            responses.append(record_message(case_id, 'assistant',
                "I've generated the SOAP note for Dr. review. Download it from the documents panel" +
                (f" (Text: {text_path} | PDF: {pdf_path})" if text_path or pdf_path else '') +
                ", get it signed, and upload the signed version when it's ready."))
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
        if _kw_match(content, 'submit', 'please submit', 'file it', 'send it', 'go ahead'):
            set_state(case_id, 'submitted', ctx)
            apply_stage(case_id, 'submitted')
            responses.append(record_message(case_id, 'assistant',
                "This case has been submitted. Let me know if you need any additional summaries or follow-up steps."))
        else:
            responses.append(record_message(case_id, 'assistant',
                "This case is ready to submit. Say 'submit' when you're ready, or let me know if you need any additional summaries."))

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
