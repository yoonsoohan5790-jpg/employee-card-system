from datetime import datetime

from extensions import db

CARD_STATUS_ACTIVE = "active"
CARD_STATUS_SUSPENDED = "suspended"
CARD_STATUS_EXPIRED = "expired"
CARD_STATUS_REVOKED = "revoked"

CARD_STATUSES = [
    CARD_STATUS_ACTIVE,
    CARD_STATUS_SUSPENDED,
    CARD_STATUS_EXPIRED,
    CARD_STATUS_REVOKED,
]

CARD_STATUS_LABELS = {
    CARD_STATUS_ACTIVE: "활성",
    CARD_STATUS_SUSPENDED: "중지",
    CARD_STATUS_EXPIRED: "만료",
    CARD_STATUS_REVOKED: "폐기",
}


class Card(db.Model):
    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.String(30), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    issue_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=CARD_STATUS_ACTIVE)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "card_id": self.card_id,
            "user_id": self.user_id,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "status": self.status,
            "status_label": CARD_STATUS_LABELS.get(self.status, self.status),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
