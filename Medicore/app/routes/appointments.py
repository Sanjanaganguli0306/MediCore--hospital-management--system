from datetime import date, datetime, time, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app import db
from app.forms import AppointmentForm
from app.models import Appointment, Doctor, Invoice, Patient
from app.utils import role_required


appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")
appointment_api_bp = Blueprint("appointment_api", __name__)


def active_doctors():
    """Return doctors eligible for new appointment bookings."""
    return Doctor.query.filter_by(status="active").order_by(Doctor.full_name).all()


def parse_slot(value):
    """Parse a posted HH:MM slot into a time value."""
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        return None


def slot_conflict(doctor_id, appointment_date, appointment_time, exclude_id=None):
    """Return a non-cancelled appointment occupying a slot."""
    query = Appointment.query.filter_by(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
    ).filter(Appointment.status != "cancelled")
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    return query.first()


def slots_for(doctor, selected_date):
    """Generate available 30-minute slots for a doctor and date."""
    if not doctor:
        return [], "Select an active doctor."
    if doctor.status != "active":
        return [], "This doctor is not available for booking."
    if not doctor.works_on(selected_date.strftime("%A")):
        return [], f"{doctor.full_name} does not work on {selected_date.strftime('%A')}."
    if not doctor.available_from or not doctor.available_to:
        return [], "This doctor has no availability window configured."

    now = datetime.now()
    current = datetime.combine(selected_date, doctor.available_from)
    end = datetime.combine(selected_date, doctor.available_to)
    slots = []
    while current < end:
        slot_time = current.time()
        available = selected_date > date.today() or current > now
        if slot_conflict(doctor.id, selected_date, slot_time):
            available = False
        slots.append({"time": slot_time.strftime("%H:%M"), "available": available})
        current += timedelta(minutes=30)
    return slots, None


def appointment_query():
    """Build the filtered appointment list query."""
    query = Appointment.query
    selected_date = request.args.get("date")
    doctor_id = request.args.get("doctor_id", type=int)
    status = request.args.get("status")
    if selected_date:
        try:
            query = query.filter(Appointment.appointment_date == datetime.strptime(selected_date, "%Y-%m-%d").date())
        except ValueError:
            pass
    else:
        query = query.filter(Appointment.appointment_date == date.today())
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if status:
        query = query.filter(Appointment.status == status)
    if current_user.role == "doctor":
        doctor = Doctor.query.filter_by(user_id=current_user.id).first()
        query = query.filter(Appointment.doctor_id == doctor.id if doctor else False)
    return query.order_by(Appointment.appointment_date, Appointment.appointment_time)


def can_manage_appointment(appointment):
    """Return whether the signed-in staff member may update this appointment."""
    if current_user.role in {"admin", "receptionist"}:
        return True
    if current_user.role != "doctor":
        return False
    doctor = Doctor.query.filter_by(user_id=current_user.id).first()
    return doctor is not None and appointment.doctor_id == doctor.id


def prepare_form(form):
    """Populate the appointment doctor choices from active doctors."""
    doctors = active_doctors()
    form.doctor_id.choices = [(doctor.id, doctor.full_name) for doctor in doctors]
    return doctors


def next_available_date(doctor):
    """Return the next date with future booking slots for a doctor."""
    candidate = date.today()
    for _ in range(8):
        slots, _ = slots_for(doctor, candidate)
        if any(slot["available"] for slot in slots):
            return candidate
        candidate += timedelta(days=1)
    return date.today()


@appointments_bp.route("")
@login_required
def list_appointments():
    """Render today's appointments with scheduling filters."""
    page = request.args.get("page", 1, type=int)
    pagination = appointment_query().paginate(page=page, per_page=10, error_out=False)
    return render_template(
        "appointments/list.html",
        pagination=pagination,
        doctors=active_doctors(),
        statuses=["scheduled", "completed", "cancelled", "no_show"],
        selected_date=request.args.get("date", date.today().isoformat()),
        selected_doctor=request.args.get("doctor_id", ""),
        selected_status=request.args.get("status", ""),
    )


@appointments_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("admin", "receptionist", "doctor")
def new_appointment():
    """Book an appointment after repeating all slot checks server-side."""
    form = AppointmentForm()
    doctors = prepare_form(form)
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    if request.method == "GET":
        form.appointment_date.data = next_available_date(doctors[0]) if doctors else date.today()
    if form.validate_on_submit():
        patient = db.session.get(Patient, form.patient_id.data)
        doctor = db.session.get(Doctor, form.doctor_id.data)
        selected_time = parse_slot(form.appointment_time.data)
        if not patient or not doctor or doctor.status != "active":
            form.patient_id.errors.append("Select a valid patient and active doctor.")
        elif not selected_time:
            form.appointment_time.errors.append("Select a valid appointment slot.")
        elif form.appointment_date.data < date.today():
            form.appointment_date.errors.append("Appointment date cannot be in the past.")
        elif not doctor.is_available_at(form.appointment_date.data, selected_time):
            form.appointment_time.errors.append("That time is outside the doctor's availability.")
        elif slot_conflict(doctor.id, form.appointment_date.data, selected_time):
            form.appointment_time.errors.append("That doctor is already booked for this slot.")
        else:
            appointment = Appointment(
                patient=patient,
                doctor=doctor,
                appointment_date=form.appointment_date.data,
                appointment_time=selected_time,
                reason=form.reason.data,
                notes=form.notes.data,
                created_by=current_user.id,
            )
            db.session.add(appointment)
            db.session.commit()
            flash("Appointment booked successfully.", "success")
            return redirect(url_for("appointments.detail", appointment_id=appointment.id))
    return render_template("appointments/form.html", form=form, patients=patients, doctors=doctors, appointment=None, today=date.today)

@appointments_bp.route("/<int:appointment_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin", "receptionist", "doctor")
def edit(appointment_id):
    """Reschedule a scheduled appointment with fresh conflict checks."""
    appointment = db.get_or_404(Appointment, appointment_id)
    if not can_manage_appointment(appointment):
        flash("You can only reschedule your own appointments.", "error")
        return redirect(url_for("appointments.detail", appointment_id=appointment.id))
    if appointment.status != "scheduled":
        flash("Only scheduled appointments can be rescheduled.", "error")
        return redirect(url_for("appointments.detail", appointment_id=appointment.id))
    form = AppointmentForm(obj=appointment)
    doctors = prepare_form(form)
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    if request.method == "GET":
        form.patient_id.data = str(appointment.patient_id)
        form.patient_search.data = f"{appointment.patient.patient_code} — {appointment.patient.full_name} ({appointment.patient.phone})"
        form.appointment_time.data = appointment.appointment_time.strftime("%H:%M")
    if form.validate_on_submit():
        patient = db.session.get(Patient, form.patient_id.data)
        doctor = db.session.get(Doctor, form.doctor_id.data)
        selected_time = parse_slot(form.appointment_time.data)
        if not patient or not doctor or doctor.status != "active":
            form.patient_id.errors.append("Select a valid patient and active doctor.")
        elif not selected_time:
            form.appointment_time.errors.append("Select a valid appointment slot.")
        elif form.appointment_date.data < date.today():
            form.appointment_date.errors.append("Appointment date cannot be in the past.")
        elif not doctor.is_available_at(form.appointment_date.data, selected_time):
            form.appointment_time.errors.append("That time is outside the doctor's availability.")
        elif slot_conflict(doctor.id, form.appointment_date.data, selected_time, appointment.id):
            form.appointment_time.errors.append("That doctor is already booked for this slot.")
        else:
            appointment.patient = patient
            appointment.doctor = doctor
            appointment.appointment_date = form.appointment_date.data
            appointment.appointment_time = selected_time
            appointment.reason = form.reason.data
            appointment.notes = form.notes.data
            db.session.commit()
            flash("Appointment rescheduled successfully.", "success")
            return redirect(url_for("appointments.detail", appointment_id=appointment.id))
    return render_template("appointments/form.html", form=form, patients=patients, doctors=doctors, appointment=appointment, today=date.today)


@appointments_bp.route("/<int:appointment_id>")
@login_required
def detail(appointment_id):
    """Render an appointment summary and lifecycle actions."""
    appointment = db.get_or_404(Appointment, appointment_id)
    invoices = Invoice.query.filter_by(appointment_id=appointment.id).order_by(Invoice.created_at.desc()).all()
    return render_template(
        "appointments/detail.html",
        appointment=appointment,
        can_manage_actions=can_manage_appointment(appointment),
        invoices=invoices,
    )


@appointments_bp.route("/<int:appointment_id>/status", methods=["POST"])
@login_required
@role_required("admin", "receptionist", "doctor")
def update_status(appointment_id):
    """Move a scheduled appointment to one terminal status."""
    appointment = db.get_or_404(Appointment, appointment_id)
    requested = request.form.get("status")
    allowed = {"completed", "cancelled", "no_show"}
    if not can_manage_appointment(appointment):
        flash("You can only update your own appointments.", "error")
        return redirect(url_for("appointments.detail", appointment_id=appointment.id))
    if appointment.status != "scheduled" or requested not in allowed:
        flash("Only scheduled appointments can change to completed, cancelled, or no-show.", "error")
    else:
        appointment.status = requested
        db.session.commit()
        flash("Appointment status updated.", "success")
        if requested == "completed" and request.form.get("continue_to") == "prescription" and current_user.role in {"admin", "doctor"}:
            return redirect(url_for("prescriptions.new_prescription", appointment_id=appointment.id))
    return redirect(request.referrer or url_for("appointments.detail", appointment_id=appointment.id))


@appointment_api_bp.route("/api/slots")
@login_required
def api_slots():
    """Return JSON appointment slots for an active doctor and date."""
    doctor = db.session.get(Doctor, request.args.get("doctor_id", type=int))
    try:
        selected_date = datetime.strptime(request.args.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"slots": [], "reason": "Choose a valid date."})
    slots, reason = slots_for(doctor, selected_date)
    return jsonify({"slots": slots, "reason": reason})
