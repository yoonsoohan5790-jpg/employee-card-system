from extensions import db


class AccessArea(db.Model):
    __tablename__ = "access_areas"

    id = db.Column(db.Integer, primary_key=True)
    area_code = db.Column(db.String(20), unique=True, nullable=False)
    area_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "area_code": self.area_code,
            "area_name": self.area_name,
            "description": self.description,
            "active": self.active,
        }
