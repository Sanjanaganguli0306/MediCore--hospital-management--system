from datetime import date, datetime
from itertools import zip_longest

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app import db
from app.models import Appointment, Doctor, Prescription, PrescriptionItem, Patient
from app.security.audit import record_event
from app.security.permissions import permission_required
from app.utils import role_required


prescriptions_bp = Blueprint("prescriptions", __name__, url_prefix="/prescriptions")


def doctor_for_user():
    """Return the signed-in user's doctor profile, if one exists."""
    return Doctor.query.filter_by(user_id=current_user.id).first()


def permitted_appointments():
    """Return completed appointments available for a new prescription."""
    query = Appointment.query.filter_by(status="completed").outerjoin(Prescription).filter(Prescription.id.is_(None))
    doctor = doctor_for_user() if current_user.role == "doctor" else None
    if current_user.role == "doctor":
        query = query.filter(Appointment.doctor_id == doctor.id if doctor else False)
    return query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()


def medicine_rows_from_request(form_data):
    """Normalize dynamically added medicine fields into stable form rows."""
    field_names = ("medicine", "dosage", "frequency", "duration", "instructions")
    values = [form_data.getlist(field_name) for field_name in field_names]
    rows = [
        dict(zip(field_names, row_values))
        for row_values in zip_longest(*values, fillvalue="")
    ]
    return rows or [dict.fromkeys(field_names, "")]


@prescriptions_bp.route("")
@permission_required("prescriptions.read")
def list_prescriptions():
    """Render searchable prescriptions for staff."""
    query = Prescription.query.join(Patient).join(Doctor)
    search = request.args.get("q", "").strip()
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(Patient.first_name.ilike(term), Patient.last_name.ilike(term), Patient.patient_code.ilike(term), Doctor.full_name.ilike(term))
        )
    if current_user.role == "doctor":
        doctor = doctor_for_user()
        query = query.filter(Prescription.doctor_id == doctor.id if doctor else False)
    prescriptions = query.order_by(Prescription.created_at.desc()).all()
    return render_template("prescriptions/list.html", prescriptions=prescriptions, query=search)


@prescriptions_bp.route("/new", methods=["GET", "POST"])
@permission_required("prescriptions.write")
def new_prescription():
    """Create a prescription from a completed appointment."""
    appointments = permitted_appointments()
    selected_id = request.args.get("appointment_id", type=int)
    form_data = request.form
    medicine_rows = medicine_rows_from_request(form_data)
    if request.method == "POST":
        selected_id = request.form.get("appointment_id", type=int)
        selected_patient_id = request.form.get("patient_id", type=int)
        appointment = db.session.get(Appointment, selected_id)
        eligible_appointment_ids = {eligible_appointment.id for eligible_appointment in appointments}
        doctor = doctor_for_user() if current_user.role == "doctor" else None
        if (
            not selected_patient_id
            or not appointment
            or appointment.id not in eligible_appointment_ids
            or appointment.status != "completed"
            or appointment.prescription
            or appointment.patient_id != selected_patient_id
            or (current_user.role == "doctor" and (not doctor or appointment.doctor_id != doctor.id))
        ):
            flash("Choose an eligible completed appointment.", "error")
        else:
            follow_up_date = None
            follow_up_error = False
            follow_up_value = request.form.get("follow_up_date", "").strip()
            if follow_up_value:
                try:
                    follow_up_date = datetime.strptime(follow_up_value, "%Y-%m-%d").date()
                except ValueError:
                    follow_up_error = True
                    flash("Enter a valid follow-up date.", "error")
                else:
                    if follow_up_date < date.today():
                        follow_up_error = True
                        flash("Follow-up date cannot be in the past.", "error")
            item_values = [
                PrescriptionItem(
                    medicine=row["medicine"].strip(),
                    dosage=row["dosage"].strip(),
                    frequency=row["frequency"].strip(),
                    duration=row["duration"].strip(),
                    instructions=row["instructions"].strip(),
                )
                for row in medicine_rows
                if row["medicine"].strip()
            ]
            if follow_up_error:
                pass
            elif not item_values:
                flash("Add at least one medicine.", "error")
            else:
                prescription = Prescription(
                    appointment=appointment,
                    patient=appointment.patient,
                    doctor=appointment.doctor,
                    diagnosis=request.form.get("diagnosis", "").strip() or None,
                    advice=request.form.get("advice", "").strip() or None,
                    follow_up_date=follow_up_date,
                    prescription_items=item_values,
                )
                db.session.add(prescription)
                db.session.commit()
                record_event("prescription_created", resource_type="prescription", resource_id=prescription.id)
                flash("Prescription created successfully.", "success")
                return redirect(url_for("prescriptions.detail", prescription_id=prescription.id))
    patients = sorted(
        {appointment.patient.id: appointment.patient for appointment in appointments}.values(),
        key=lambda patient: (patient.last_name.lower(), patient.first_name.lower()),
    )
    selected_appointment = next((appointment for appointment in appointments if appointment.id == selected_id), None)
    return render_template(
        "prescriptions/form.html",
        appointments=appointments,
        patients=patients,
        selected_id=selected_id,
        selected_patient_id=selected_appointment.patient_id if selected_appointment else form_data.get("patient_id", type=int),
        form_data=form_data,
        medicine_rows=medicine_rows,
        today=date.today().isoformat(),
    )


@prescriptions_bp.route("/<int:prescription_id>")
@permission_required("prescriptions.read")
def detail(prescription_id):
    """Render one prescription and its medicine instructions."""
    prescription = db.get_or_404(Prescription, prescription_id)
    if current_user.role == "doctor":
        doctor = doctor_for_user()
        if not doctor or prescription.doctor_id != doctor.id:
            return "Forbidden", 403
    record_event("prescription_viewed", resource_type="prescription", resource_id=prescription.id)
    return render_template("prescriptions/detail.html", prescription=prescription)


@prescriptions_bp.route("/<int:prescription_id>/print")
@permission_required("prescriptions.read")
def print_prescription(prescription_id):
    """Render a print-friendly prescription sheet."""
    prescription = db.get_or_404(Prescription, prescription_id)
    if current_user.role == "doctor":
        doctor = doctor_for_user()
        if not doctor or prescription.doctor_id != doctor.id:
            return "Forbidden", 403
    return render_template("prescriptions/print.html", prescription=prescription)
