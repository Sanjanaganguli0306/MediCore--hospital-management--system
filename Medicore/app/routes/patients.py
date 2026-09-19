from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_

from app import db
from app.forms import PatientForm
from app.models import Invoice, Patient
from app.security.audit import record_event
from app.security.permissions import can_access_patient, permission_required
from app.utils import next_code, role_required


patients_bp = Blueprint("patients", __name__, url_prefix="/patients")


def patient_query():
    """Build the filtered patient query for the list view."""
    query = Patient.query
    search = request.args.get("q", "").strip()
    gender = request.args.get("gender", "").strip()
    blood_group = request.args.get("blood_group", "").strip()
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
                Patient.patient_code.ilike(term),
                Patient.phone.ilike(term),
            )
        )
    if gender:
        query = query.filter(Patient.gender == gender)
    if blood_group:
        query = query.filter(Patient.blood_group == blood_group)
    return query.order_by(Patient.created_at.desc())


@patients_bp.route("")
@permission_required("patients.read")
def list_patients():
    """Render a searchable, paginated patient list."""
    page = request.args.get("page", 1, type=int)
    pagination = patient_query().paginate(page=page, per_page=10, error_out=False)
    genders = [value for value, in db.session.query(Patient.gender).distinct().order_by(Patient.gender)]
    blood_groups = [value for value, in db.session.query(Patient.blood_group).filter(Patient.blood_group.isnot(None)).distinct().order_by(Patient.blood_group)]
    return render_template(
        "patients/list.html",
        pagination=pagination,
        genders=genders,
        blood_groups=blood_groups,
        query=request.args.get("q", ""),
        selected_gender=request.args.get("gender", ""),
        selected_blood_group=request.args.get("blood_group", ""),
    )


@patients_bp.route("/new", methods=["GET", "POST"])
@permission_required("patients.write")
def new_patient():
    """Register a new patient."""
    form = PatientForm()
    if form.validate_on_submit():
        patient = Patient(patient_code=next_code("PAT", Patient, "patient_code"))
        form.populate_obj(patient)
        db.session.add(patient)
        db.session.commit()
        record_event("patient_created", resource_type="patient", resource_id=patient.id)
        flash(f"Patient {patient.patient_code} registered successfully.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))
    return render_template("patients/form.html", form=form, patient=None)


@patients_bp.route("/<int:patient_id>")
@permission_required("patients.read")
def detail(patient_id):
    """Render a patient's overview and related clinical tabs."""
    patient = db.get_or_404(Patient, patient_id)
    if not can_access_patient(patient):
        return "Forbidden", 403
    record_event("patient_viewed", resource_type="patient", resource_id=patient.id)
    upcoming = sorted(
        [appointment for appointment in patient.appointments if appointment.status == "scheduled"],
        key=lambda appointment: (appointment.appointment_date, appointment.appointment_time),
    )
    records = sorted(patient.medical_records, key=lambda record: record.visit_date, reverse=True)
    return render_template("patients/detail.html", patient=patient, upcoming=upcoming, records=records)


@patients_bp.route("/<int:patient_id>/edit", methods=["GET", "POST"])
@permission_required("patients.write")
def edit(patient_id):
    """Edit an existing patient record."""
    patient = db.get_or_404(Patient, patient_id)
    if not can_access_patient(patient):
        return "Forbidden", 403
    form = PatientForm(obj=patient)
    if form.validate_on_submit():
        form.populate_obj(patient)
        db.session.commit()
        record_event("patient_updated", resource_type="patient", resource_id=patient.id)
        flash(f"{patient.full_name}'s record was updated.", "success")
        return redirect(url_for("patients.detail", patient_id=patient.id))
    return render_template("patients/form.html", form=form, patient=patient)


@patients_bp.route("/<int:patient_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete(patient_id):
    """Delete a patient only when no invoices are attached."""
    patient = db.get_or_404(Patient, patient_id)
    if Invoice.query.filter_by(patient_id=patient.id).first():
        flash("This patient cannot be deleted because invoices are attached.", "error")
        return redirect(url_for("patients.detail", patient_id=patient.id))
    db.session.delete(patient)
    db.session.commit()
    record_event("patient_deleted", resource_type="patient", resource_id=patient_id)
    flash("Patient record deleted.", "success")
    return redirect(url_for("patients.list_patients"))
