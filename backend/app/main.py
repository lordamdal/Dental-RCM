from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import logging
import os, shutil

from .settings import settings
from .utils import ensure_dir, uid, read_csv, append_csv, now_iso
from .models import CaseCreate, Case, MessageCreate, Message, Document
from . import workflow

from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

app = FastAPI(title="Amdal Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CASES_CSV = os.path.join(settings.DATA_DIR, 'cases.csv')
DOCS_CSV  = os.path.join(settings.DATA_DIR, 'documents.csv')
MSGS_CSV  = os.path.join(settings.DATA_DIR, 'messages.csv')
UPLOADS   = os.path.join(settings.DATA_DIR, 'uploads')

ensure_dir(UPLOADS)


def build_public_url(case_id: str, filename: str) -> str:
    safe_name = os.path.basename(filename)
    relative = f"/uploads/{case_id}/{safe_name}"
    base = settings.PUBLIC_BASE_URL.rstrip('/') if settings.PUBLIC_BASE_URL else None
    return f"{base}{relative}" if base else relative


def document_row_to_response(row: dict) -> dict:
    name = row.get('name') or os.path.basename(row.get('path', '')) or row.get('doc_id', 'document')
    name = os.path.basename(name)
    public_url = row.get('public_url') or build_public_url(row['case_id'], name)
    path_value = row.get('path') or os.path.join(UPLOADS, row['case_id'], name)
    return {**row, 'name': name, 'path': path_value, 'public_url': public_url}


def to_float(value):
    if value in (None, '', 'None'):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def case_row_to_response(row: dict) -> dict:
    data = dict(row)
    data['reimbursement_amount'] = to_float(data.get('reimbursement_amount'))
    if not data.get('workflow_stage'):
        state = workflow.get_state(data['case_id'])
        data['workflow_stage'] = state.get('stage', 'awaiting_case_start')
    defaults = workflow.STAGE_DEFAULTS.get(data['workflow_stage'], {})
    if not data.get('workflow_status'):
        data['workflow_status'] = defaults.get('workflow_status')
    if not data.get('next_action'):
        data['next_action'] = defaults.get('next_action')
    if not data.get('status'):
        data['status'] = defaults.get('status')
    for field in ['workflow_stage', 'workflow_status', 'next_action', 'risk_level']:
        if data.get(field) == '':
            data[field] = None
    return data


# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")

@app.get('/health')
def health():
    return {"status": "ok"}

@app.get('/cases', response_model=List[Case])
def list_cases():
    workflow.normalize_case_file()
    rows = workflow.load_cases()
    return [case_row_to_response(r) for r in rows[::-1]]  # newest first

@app.post('/cases', response_model=Case)
def create_case(payload: CaseCreate):
    case_id = uid('case')
    now = now_iso()
    record = workflow.create_case_record(case_id, payload.title, payload.patient_name, payload.payer, now)
    workflow.add_case(record)
    workflow.initialize_case(case_id, payload.title)
    return get_case(case_id)

@app.get('/cases/{case_id}', response_model=Case)
def get_case(case_id: str):
    rows = workflow.load_cases()
    for r in rows:
        if r['case_id'] == case_id:
            return case_row_to_response(r)
    raise HTTPException(status_code=404, detail="Case not found")

@app.delete('/cases/{case_id}', status_code=204)
def delete_case(case_id: str):
    rows = workflow.load_cases()
    if not any(r['case_id'] == case_id for r in rows):
        raise HTTPException(status_code=404, detail="Case not found")
    workflow.delete_case_data(case_id)
    return

@app.get('/cases/{case_id}/documents', response_model=List[Document])
def list_documents(case_id: str):
    rows = read_csv(DOCS_CSV)
    return [document_row_to_response(r) for r in rows if r['case_id'] == case_id]

@app.post('/cases/{case_id}/documents', response_model=Document)
async def upload_document(case_id: str, file: UploadFile = File(...)):
    # save file
    case_dir = os.path.join(UPLOADS, case_id)
    ensure_dir(case_dir)
    filename = os.path.basename(file.filename or '')
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid file name")
    dst_path = os.path.join(case_dir, filename)
    with open(dst_path, 'wb') as out:
        shutil.copyfileobj(file.file, out)
    public_url = build_public_url(case_id, filename)
    rec = {
        'doc_id': uid('doc'),
        'case_id': case_id,
        'name': filename,
        'type': file.content_type or '',
        'path': dst_path,
        'uploaded_at': now_iso(),
        'public_url': public_url,
    }
    append_csv(DOCS_CSV, rec, rec.keys())
    workflow.handle_document_upload(case_id, rec)
    return document_row_to_response(rec)

@app.get('/cases/{case_id}/messages', response_model=List[Message])
def list_messages(case_id: str):
    rows = read_csv(MSGS_CSV)
    # sort ascending by created_at
    filtered = [r for r in rows if r['case_id'] == case_id]
    filtered.sort(key=lambda r: r['created_at'])
    return filtered

@app.post('/cases/{case_id}/chat', response_model=Message)
def chat(case_id: str, payload: MessageCreate):
    # append user message
    user_row = {
        'msg_id': uid('msg'),
        'case_id': case_id,
        'role': 'user',
        'content': payload.content,
        'created_at': now_iso(),
    }
    append_csv(MSGS_CSV, user_row, user_row.keys())
    responses = workflow.handle_user_message(case_id, payload.content)
    if not responses:
        responses = [workflow.record_message(case_id, 'assistant', "I'm here if you need anything else for this case.")]
    return responses[-1]
