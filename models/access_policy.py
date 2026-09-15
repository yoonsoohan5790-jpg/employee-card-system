from extensions import db


class AccessPolicy(db.Model):
    __tablename__ = "access_policies"
    __table_args__ = (
        db.UniqueConstraint("department", "position", "area_id", name="uq_policy_dept_position_area"),
    )

    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey("access_areas.id"), nullable=False)
    allowed = db.Column(db.Boolean, default=False, nullable=False)

    area = db.relationship("AccessArea")

    def to_dict(self):
        return {
            "id": self.id,
            "department": self.department,
            "position": self.position,
            "area_id": self.area_id,
            "area_code": self.area.area_code if self.area else None,
            "area_name": self.area.area_name if self.area else None,
            "allowed": self.allowed,
        }
