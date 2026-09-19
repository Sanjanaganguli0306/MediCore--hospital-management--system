from datetime import date, datetime
from decimal import Decimal

from flask_login import UserMixin
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


password_hasher = PasswordHasher()


class User(UserMixin, db.Model):
    """A staff account with a role-based access level."""

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="receptionist")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and store a password."""
        self.password_hash = password_hasher.hash(password)

    def check_password(self, password):
        """Verify Argon2 passwords and transparently migrate legacy hashes."""
        if self.password_hash.startswith("$argon2"):
            try:
                valid = password_hasher.verify(self.password_hash, password)
            except (VerifyMismatchError, VerificationError):
                return False
            if valid and password_hasher.check_needs_rehash(self.password_hash):
                self.set_password(password)
            return valid
        if check_password_hash(self.password_hash, password):
            self.set_password(password)
            return True
        return False


class AuditEvent(db.Model):
    """Append-oriented record of security and administrative activity."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    user_role = db.Column(db.String(30))
    action = db.Column(db.String(80), nullable=False, index=True)
    resource_type = db.Column(db.String(80))
    resource_id = db.Column(db.String(80))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(512))
    success = db.Column(db.Boolean, nullable=False, default=True)
    context = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    user = db.relationship("User", backref="audit_events")


class Patient(db.Model):
    """A patient demographic and medical-contact record."""

    id = db.Column(db.Integer, primary_key=True)
    patient_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    blood_group = db.Column(db.String(10))
    phone = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    registration_date = db.Column(db.Date)
    insurance_provider = db.Column(db.String(120))
    insurance_number = db.Column(db.String(80))
    emergency_contact_name = db.Column(db.String(120))
    emergency_contact_phone = db.Column(db.String(10))
    allergies = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def age(self):
        """Return the patient's age in completed years."""
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))

    @property
    def full_name(self):
        """Return the patient's display name."""
        return f"{self.first_name} {self.last_name}"


class Doctor(db.Model):
    """A clinician and their appointment availability."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    full_name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(120))
    phone = db.Column(db.String(10))
    email = db.Column(db.String(120))
    years_experience = db.Column(db.Integer)
    hospital_branch = db.Column(db.String(120))
    consultation_fee = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    available_days = db.Column(db.String(40), default="Mon,Tue,Wed,Thu,Fri")
    available_from = db.Column(db.Time)
    available_to = db.Column(db.Time)
    status = db.Column(db.String(20), nullable=False, default="active")
    photo_url = db.Column(db.String(500))
    bio = db.Column(db.Text)
    user = db.relationship("User", backref="doctor_profile")

    def works_on(self, weekday_name):
        """Return whether the doctor works on a weekday name."""
        days = {day.strip().title()[:3] for day in (self.available_days or "").split(",") if day.strip()}
        return weekday_name[:3].title() in days

    def is_available_at(self, appointment_date, appointment_time):
        """Return whether the doctor accepts a time on a working day."""
        return (
            self.status == "active"
            and self.works_on(appointment_date.strftime("%A"))
            and self.available_from is not None
            and self.available_to is not None
            and self.available_from <= appointment_time < self.available_to
        )


class Appointment(db.Model):
    """A scheduled or completed patient visit."""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    patient = db.relationship("Patient", backref="appointments")
    doctor = db.relationship("Doctor", backref="appointments")
    creator = db.relationship("User", backref="created_appointments")


class MedicalRecord(db.Model):
    """A clinical record created from a patient visit."""

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=True)
    visit_date = db.Column(db.Date, nullable=False)
    complaint = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    notes = db.Column(db.Text)
    patient = db.relationship("Patient", backref="medical_records")
    doctor = db.relationship("Doctor", backref="medical_records")
    appointment = db.relationship("Appointment", backref="medical_records")


class Treatment(db.Model):
    """A source treatment and cost associated with an appointment."""

    id = db.Column(db.Integer, primary_key=True)
    treatment_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=False)
    treatment_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    treatment_date = db.Column(db.Date, nullable=False)
    appointment = db.relationship("Appointment", backref="treatments")


class Prescription(db.Model):
    """A prescription associated with a patient appointment."""

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    diagnosis = db.Column(db.Text)
    advice = db.Column(db.Text)
    follow_up_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    appointment = db.relationship("Appointment", backref=db.backref("prescription", uselist=False))
    patient = db.relationship("Patient", backref="prescriptions")
    doctor = db.relationship("Doctor", backref="prescriptions")
    prescription_items = db.relationship("PrescriptionItem", backref="prescription", cascade="all, delete-orphan")


class PrescriptionItem(db.Model):
    """One medicine line within a prescription."""

    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey("prescription.id"), nullable=False)
    medicine = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(80))
    frequency = db.Column(db.String(80))
    duration = db.Column(db.String(80))
    instructions = db.Column(db.Text)


class Invoice(db.Model):
    """A patient invoice with calculated payment state."""

    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.id"), nullable=True)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax_percent = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="unpaid")
    payment_method = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    patient = db.relationship("Patient", backref="invoices")
    appointment = db.relationship("Appointment", backref="invoice")
    invoice_items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan")

    @property
    def balance(self):
        """Return the unpaid invoice balance."""
        return self.total - self.amount_paid


class InvoiceItem(db.Model):
    """One charge line within an invoice."""

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoice.id"), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
