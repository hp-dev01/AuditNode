from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from hashlogic import gen_token, hashtoken
from models import Greivances, Base, AuditLog
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from states import Status, ALLOWED_TRANSITIONS
import hashlib
from datetime import datetime,timedelta
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import json
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(check_sla_breaches, "interval", seconds=10)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
class transition_request(BaseModel):
    new_status: Status

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*","null"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def read_index():
    return FileResponse("index.html")
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
main_loop: asyncio.AbstractEventLoop | None = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()  # Stores the main FastAPI loop

    scheduler.add_job(check_sla_breaches, "interval", seconds=10)
    scheduler.start()
    yield
    scheduler.shutdown()
subscribers: list[asyncio.Queue] = []

async def broadcast_event(event_data: dict):
    """Pushes a message to every connected SSE client."""
    for queue in subscribers:
        await queue.put(event_data)

def check_sla_breaches():
    print("Checking SLA breaches...")
    try:
        db = sessionmaker(bind=engine)()
        db = SessionLocal()
        try:
            breaches = db.query(Greivances).filter(Greivances.deadline_at <= datetime.utcnow(),Greivances.status != Status.RESOLVED.value,Greivances.status != Status.TIER_3_REVIEW.value).all()
            for breach in breaches:
                Escalation_map = {
                Status.SUBMITTED: Status.TIER_1_REVIEW,
                Status.TIER_1_REVIEW: Status.TIER_2_REVIEW,
                Status.TIER_2_REVIEW: Status.TIER_3_REVIEW
            }
                target_status = Escalation_map.get(breach.status)
                if not target_status:
                    continue

                breach.deadline_at = datetime.utcnow() + timedelta(seconds=60)
                chain_tail = db.query(AuditLog).filter(AuditLog.complaint_id == breach.id).order_by(AuditLog.id.desc()).first()
                if not chain_tail:
                    prev_hash = "0" * 64
                else:
                    prev_hash = chain_tail.curr_hash
                old_status = breach.status
                breach.status = target_status.value
                timestamp = datetime.utcnow()
                curr_hash = hashlib.sha256((prev_hash + str(breach.id) + str(old_status) + str(breach.status) + timestamp.isoformat()).encode("utf-8")).hexdigest()
                newlog = AuditLog(complaint_id=breach.id,
    old_status=str(old_status),
    new_status=str(breach.status),
    timestamp=timestamp,
    prev_hash=prev_hash,
    curr_hash=curr_hash)
                db.add(newlog)
                db.commit()
                event_payload = {
    "grievance_id": breach.id,
    "old_status": old_status,
    "new_status": breach.status,
}
                # Since check_sla_breaches is synchronous, schedule the async broadcast onto the event loop:
                try:
                    if main_loop and main_loop.is_running():
                        asyncio.run_coroutine_threadsafe(broadcast_event(event_payload), main_loop)
                except Exception as e:
                    print(f"Failed to broadcast event: {e}")
        finally:
            db.close()
    except Exception as e:
        print(f"Exception inside check_sla_branches: {e}")


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
    new_complaint.deadline_at = datetime.utcnow() + timedelta(seconds=60)
    db.add(new_complaint)
    db.commit()
    
    db.refresh(new_complaint)
    return {
        "id": new_complaint.id,
        "message": "Complaint submitted successfully",
        "receipt": receipt
    }
@app.get("/complaints")
def get_complaints(db: Session = Depends(get_db)):
    return db.query(Greivances).all()   

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

    old_status = current_status.value
    new_status = target_status.value

    complaint.status = new_status

    entry = db.query(AuditLog).filter(complaint.id == AuditLog.complaint_id).order_by(AuditLog.id.desc()).first()

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
        if log.prev_hash != expected_prev_hash:
           return {"tamper_detected": True, "tampered_at_id": log.id, "reason": "Previous hash link broken"}

        payload = expected_prev_hash + str(log.complaint_id) + str(log.old_status) + str(log.new_status) + log.timestamp.isoformat()
        computed_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if log.curr_hash != computed_hash:
            return {"tamper_detected": True, "tampered_at_id": log.id, "reason": "Hash mismatch detected"}

        expected_prev_hash = log.curr_hash

    return {"tamper_detected": False, "status": "Audit chain intact", "total_records": len(logs),"complaint_id": complaint_id}

@app.get("/events")
async def sse_events():
    async def event_generator():
        queue = asyncio.Queue()
        subscribers.append(queue)
        try:
            while True:
                # Wait for a new event to arrive
                data = await queue.get()
                # SSE requires the 'data: <payload>\n\n' format
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            # Clean up when a client closes the browser tab
            subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
