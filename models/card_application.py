from datetime import datetime

from extensions import db

STATUS_APPROVED = "approved"
STATUS_PENDING = "pending"
STATUS_REJECTED = "rejected"

STATUS_LABELS = {
    STATUS_APPROVED: "승인됨(발급완료)",
    STATUS_PENDING: "검토 대기",
    STATUS_REJECTED: "반려됨",
}


class CardApplication(db.Model):
    """
    일반 사용자가 로그인 없이 제출하는 사원증 신청서.
    기타사항이 없으면 즉시 자동 승인되어 계정/사원증이 만들어지고,
    기타사항이 있으면 관리자 검토를 거쳐야 한다.
    """
    __tablename__ = "card_applications"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    employee_number = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text)

    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    reject_reason = db.Column(db.String(200))

    resulting_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    reviewed_by = db.Column(db.String(50))
    reviewed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "employee_number": self.employee_number,
            "department": self.department,
            "position": self.position,
            "note": self.note,
            "status": self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "reject_reason": self.reject_reason,
            "resulting_user_id": self.resulting_user_id,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
