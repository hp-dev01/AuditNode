from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from hashlogic import gen_token, hashtoken
from models import Greivances, Base, AuditLog
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from states import Status, ALLOWED_TRANSITIONS
import hashlib
from datetime import datetime

app = FastAPI()

class transition_request(BaseModel):
    new_status: Status

class Item(BaseModel):
    category: str
    description: str
    visibility: str = "Identified"
engine = create_engine("sqlite:///./grievances.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/complaints")
def create_complaint(data: Item,db: Session = Depends(get_db)):
    receipt = None
    if data.visibility == "Anonymous":
        receipt = gen_token()
        tokenhash = hashtoken(receipt)
        assign_user_id = None
    elif data.visibility == "Identified":
        assign_user_id = 1 # needs review as JWT auth not done yet
        tokenhash = None

    new_complaint = Greivances(description=data.description,visibility=data.visibility,user_id=assign_user_id,token=tokenhash)

    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)
    return {
        "id": new_complaint.id,
        "message": "Complaint submitted successfully",
        "receipt": receipt
    }   

@app.patch("/complaints/{complaint_id}/transition")
def transition_status(
    complaint_id: int,
    payload: transition_request,
    db: Session = Depends(get_db)
):
    complaint = db.query(Greivances).filter(Greivances.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    current_status = Status(complaint.status)
    target_status = payload.new_status

    allowed_states = ALLOWED_TRANSITIONS.get(current_status,[])
    if target_status not in allowed_states:
        raise HTTPException(status_code=400, 
            detail=f"Invalid transition: Cannot move from '{current_status.value}' to '{target_status.value}'")

    complaint.status = target_status.value

    entry = db.query(AuditLog).filter(complaint.id == AuditLog.complaint_id).order_by(AuditLog.id.desc()).first()
    old_status = complaint.status
    new_status = payload.new_status
    timestamp = datetime.utcnow()
    if entry is None:
        prev_hash = "0" * 64
    else:
        prev_hash = entry.curr_hash
    curr_hash = hashlib.sha256((prev_hash+str(complaint.id)+ str(old_status)+ str(new_status)+ timestamp.isoformat()).encode("utf-8")).hexdigest()
    new_log = AuditLog(complaint_id=complaint.id,
    old_status=str(old_status),
    new_status=str(new_status),
    timestamp=timestamp,
    prev_hash=prev_hash,
    curr_hash=curr_hash)
    db.add(new_log)
    db.commit()
    db.refresh(complaint)

    return {
        "id": complaint.id,
        "previous_status": current_status.value,
        "current_status": complaint.status,
        "message": "Status updated successfully"
    }

@app.get("/audit/verify/{complaint_id}")
def verification(complaint_id: int, db: Session =Depends(get_db)):
    logs = db.query(AuditLog).filter(AuditLog.complaint_id == complaint_id).order_by(AuditLog.id.asc()).all()
    if not logs:
        raise HTTPException(status_code = 404, detail="No audit records exist yet")
    expected_prev_hash = "0" * 64
    for log in logs:
        if log.prev_hash == expected_prev_hash:
           return {"tamper_detected": True, "tampered_at_id": log.id, "reason": "Previous hash link broken"}

        payload = expected_prev_hash + str(log.complaint_id) + log.old_status + log.new_status + log.timestamp.isoformat()
        computed_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if log.curr_hash != computed_hash:
            return {"tamper_detected": True, "tampered_at_id": log.id, "reason": "Hash mismatch detected"}

        expected_prev_hash = log.curr_hash

    return {"tamper_detected": False, "status": "Audit chain intact", "total_records": len(logs)}