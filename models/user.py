from datetime import datetime, date

from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

# 재직 상태
EMPLOYMENT_STATUS_ACTIVE = "재직"
EMPLOYMENT_STATUS_LEAVE = "휴직"
EMPLOYMENT_STATUS_RESIGNED = "퇴사"

EMPLOYMENT_STATUSES = [
    EMPLOYMENT_STATUS_ACTIVE,
    EMPLOYMENT_STATUS_LEAVE,
    EMPLOYMENT_STATUS_RESIGNED,
]

ROLE_ADMIN = "admin"
ROLE_EMPLOYEE = "employee"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50), nullable=False, default="")
    position = db.Column(db.String(50), nullable=False, default="")
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))

    hire_date = db.Column(db.Date)
    resign_date = db.Column(db.Date)
    leave_start_date = db.Column(db.Date)
    leave_end_date = db.Column(db.Date)

    employment_status = db.Column(db.String(20), nullable=False, default=EMPLOYMENT_STATUS_ACTIVE)
    role = db.Column(db.String(20), nullable=False, default=ROLE_EMPLOYEE)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    card = db.relationship("Card", backref="user", uselist=False, cascade="all, delete-orphan")
    access_grants = db.relationship("UserAccess", backref="user", cascade="all, delete-orphan")

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    def to_dict(self, include_sensitive=False):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "department": self.department,
            "position": self.position,
            "email": self.email,
            "phone": self.phone,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "resign_date": self.resign_date.isoformat() if self.resign_date else None,
            "leave_start_date": self.leave_start_date.isoformat() if self.leave_start_date else None,
            "leave_end_date": self.leave_end_date.isoformat() if self.leave_end_date else None,
            "employment_status": self.employment_status,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
