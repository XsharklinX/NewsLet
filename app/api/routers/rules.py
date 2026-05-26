import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel as _BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.rule import Rule
from app.services.auth import require_auth

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_auth)],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class RuleIn(_BaseModel):
    name: str
    conditions: list[dict]
    actions: list[dict]
    is_active: bool = True
    priority: int = 10


class RuleOut(_BaseModel):
    id: int
    name: str
    conditions: list[dict]
    actions: list[dict]
    is_active: bool
    priority: int
    created_at: datetime
    last_matched_at: datetime | None
    match_count: int

    model_config = {"from_attributes": True}


def _rule_to_out(r: Rule) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "conditions": json.loads(r.conditions or "[]"),
        "actions": json.loads(r.actions or "[]"),
        "is_active": r.is_active,
        "priority": r.priority,
        "created_at": r.created_at.isoformat(),
        "last_matched_at": r.last_matched_at.isoformat() if r.last_matched_at else None,
        "match_count": r.match_count or 0,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/rules")
def list_rules(db: Session = Depends(get_db)):
    rules = db.query(Rule).order_by(Rule.priority, Rule.id).all()
    return {"rules": [_rule_to_out(r) for r in rules]}


@router.post("/rules", status_code=201)
def create_rule(body: RuleIn, db: Session = Depends(get_db)):
    rule = Rule(
        name=body.name,
        conditions=json.dumps(body.conditions),
        actions=json.dumps(body.actions),
        is_active=body.is_active,
        priority=body.priority,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_out(rule)


@router.get("/rules/{rule_id}")
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Regla no encontrada")
    return _rule_to_out(rule)


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, body: RuleIn, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Regla no encontrada")
    rule.name = body.name
    rule.conditions = json.dumps(body.conditions)
    rule.actions = json.dumps(body.actions)
    rule.is_active = body.is_active
    rule.priority = body.priority
    db.commit()
    return _rule_to_out(rule)


@router.patch("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Regla no encontrada")
    rule.is_active = not rule.is_active
    db.commit()
    return {"id": rule_id, "is_active": rule.is_active}


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Regla no encontrada")
    db.delete(rule)
    db.commit()


@router.post("/rules/apply-now")
async def apply_rules_now(db: Session = Depends(get_db)):
    """Apply all active rules to pending articles immediately."""
    from app.services.rule_engine import apply_rules_to_pending
    affected = await apply_rules_to_pending(db)
    return {"affected_articles": affected}
