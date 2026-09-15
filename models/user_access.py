from datetime import datetime

from extensions import db

SOURCE_POLICY = "policy"
SOURCE_MANUAL = "manual"


class UserAccess(db.Model):
    __tablename__ = "user_access"
    __table_args__ = (
        db.UniqueConstraint("user_id", "area_id", name="uq_user_access_user_area"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey("access_areas.id"), nullable=False)
    allowed = db.Column(db.Boolean, default=False, nullable=False)
    source = db.Column(db.String(20), default=SOURCE_POLICY, nullable=False)
    # source가 manual(예외처리)일 때 그 사유/적용 기간. 정책 적용(policy)으로 재계산되면 함께 초기화된다.
    reason = db.Column(db.String(200))
    # 이 날짜까지만 예외가 유효하다. None이면 무기한. 지나면 자동으로 정책 값으로 복귀한다.
    expires_at = db.Column(db.Date)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    area = db.relationship("AccessArea")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "area_id": self.area_id,
            "area_code": self.area.area_code if self.area else None,
            "area_name": self.area.area_name if self.area else None,
            "allowed": self.allowed,
            "source": self.source,
            "reason": self.reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
