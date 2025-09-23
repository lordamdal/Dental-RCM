from pydantic import BaseModel, Field
from typing import Optional, Literal

class CaseCreate(BaseModel):
    title: str
    patient_name: Optional[str] = None
    payer: Optional[str] = None

class Case(BaseModel):
    case_id: str
    title: str
    patient_name: Optional[str] = None
    payer: Optional[str] = None
    status: Optional[str] = None
    reimbursement_amount: Optional[float] = None
    reimbursement_date: Optional[str] = None
    workflow_stage: Optional[str] = None
    workflow_status: Optional[str] = None
    next_action: Optional[str] = None
    risk_level: Optional[str] = None
    created_at: str
    updated_at: str

class MessageCreate(BaseModel):
    content: str

class Message(BaseModel):
    msg_id: str
    case_id: str
    role: Literal['user','assistant','system']
    content: str
    created_at: str

class Document(BaseModel):
    doc_id: str
    case_id: str
    name: str
    type: Optional[str] = None
    path: str
    uploaded_at: str
    public_url: Optional[str] = None
