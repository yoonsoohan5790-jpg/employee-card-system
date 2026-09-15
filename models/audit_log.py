from datetime import datetime

from extensions import db

ACTOR_SYSTEM = "SYSTEM"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    card_id = db.Column(db.String(30), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    before_value = db.Column(db.Text)
    after_value = db.Column(db.Text)
    actor = db.Column(db.String(50), nullable=False, default=ACTOR_SYSTEM)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "card_id": self.card_id,
            "action": self.action,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "actor": self.actor,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
