from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app import db
from app.forms import DoctorForm
from app.models import Appointment, Doctor
from app.utils import role_required


doctors_bp = Blueprint("doctors", __name__, url_prefix="/doctors")
DAYS = [("mon", "Mon", "Monday"), ("tue", "Tue", "Tuesday"), ("wed", "Wed", "Wednesday"), ("thu", "Thu", "Thursday"), ("fri", "Fri", "Friday"), ("sat", "Sat", "Saturday"), ("sun", "Sun", "Sunday")]


def doctor_query():
    """Build the filtered doctor query for the directory."""
    query = Doctor.query
    search = request.args.get("q", "").strip()
    specialization = request.args.get("specialization", "").strip()
    if search:
        term = f"%{search}%"
        query = query.filter(or_(Doctor.full_name.ilike(term), Doctor.specialization.ilike(term)))
    if specialization:
        query = query.filter(Doctor.specialization == specialization)
    return query.order_by(Doctor.full_name.asc())


def set_days(form, doctor):
    """Serialize the seven availability checkboxes to CSV."""
    doctor.available_days = ",".join(short for key, short, label in DAYS if getattr(form, f"day_{key}").data)


def load_days(form, doctor):
    """Populate availability checkboxes from the doctor's CSV days."""
    selected = set((doctor.available_days or "").split(","))
    for key, short, label in DAYS:
        getattr(form, f"day_{key}").data = short in selected


def signed_in_doctor():
    """Return the clinician profile bound to the signed-in doctor account."""
    return Doctor.query.filter_by(user_id=current_user.id).first()


def save_profile_photo(upload, doctor):
    """Store a selected clinician photo and retain its static-relative path."""
    if not upload or not upload.filename:
        return
    extension = Path(secure_filename(upload.filename)).suffix.lower()
    filename = f"doctor-{doctor.id or 'new'}-{uuid4().hex}{extension}"
    upload_directory = Path(current_app.static_folder) / "uploads" / "doctors"
    upload_directory.mkdir(parents=True, exist_ok=True)
    upload.save(upload_directory / filename)
    doctor.photo_url = f"uploads/doctors/{filename}"


@doctors_bp.route("")
@login_required
def list_doctors():
    """Render the searchable doctor directory."""
    page = request.args.get("page", 1, type=int)
    pagination = doctor_query().paginate(page=page, per_page=10, error_out=False)
    specializations = [value for value, in db.session.query(Doctor.specialization).distinct().order_by(Doctor.specialization)]
    return render_template("doctors/list.html", pagination=pagination, specializations=specializations, query=request.args.get("q", ""), selected_specialization=request.args.get("specialization", ""))


@doctors_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("admin")
def new_doctor():
    """Create a doctor profile for administrators."""
    form = DoctorForm()
    if form.validate_on_submit():
        doctor = Doctor()
        form.populate_obj(doctor)
        set_days(form, doctor)
        db.session.add(doctor)
        db.session.flush()
        save_profile_photo(form.profile_photo.data, doctor)
        db.session.commit()
        flash(f"{doctor.full_name} was added to the directory.", "success")
        return redirect(url_for("doctors.detail", doctor_id=doctor.id))
    return render_template("doctors/form.html", form=form, doctor=None, days=DAYS)


@doctors_bp.route("/me")
@login_required
@role_required("doctor")
def personal_profile():
    """Render the authenticated doctor's own profile and practice schedule."""
    doctor = signed_in_doctor()
    if not doctor:
        flash("Your clinician profile is not linked to this account. Contact an administrator.", "error")
        return redirect(url_for("main.dashboard"))
    appointments = sorted(
        doctor.appointments,
        key=lambda appointment: (appointment.appointment_date, appointment.appointment_time),
    )
    upcoming = [appointment for appointment in appointments if appointment.status == "scheduled"][:5]
    return render_template(
        "doctors/personal.html",
        doctor=doctor,
        days=DAYS,
        upcoming=upcoming,
        appointment_count=len(appointments),
        completed_count=sum(appointment.status == "completed" for appointment in appointments),
        patient_count=len({appointment.patient_id for appointment in appointments}),
    )


@doctors_bp.route("/<int:doctor_id>")
@login_required
def detail(doctor_id):
    """Render a doctor profile and upcoming appointments."""
    doctor = db.get_or_404(Doctor, doctor_id)
    appointments = sorted(
        [appointment for appointment in doctor.appointments if appointment.status == "scheduled"],
        key=lambda appointment: (appointment.appointment_date, appointment.appointment_time),
    )
    return render_template("doctors/detail.html", doctor=doctor, appointments=appointments, days=DAYS)


@doctors_bp.route("/<int:doctor_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("admin")
def edit(doctor_id):
    """Edit a doctor profile for administrators."""
    doctor = db.get_or_404(Doctor, doctor_id)
    form = DoctorForm(obj=doctor)
    if request.method == "GET":
        load_days(form, doctor)
    if form.validate_on_submit():
        form.populate_obj(doctor)
        set_days(form, doctor)
        save_profile_photo(form.profile_photo.data, doctor)
        db.session.commit()
        flash(f"{doctor.full_name}'s profile was updated.", "success")
        return redirect(url_for("doctors.detail", doctor_id=doctor.id))
    return render_template("doctors/form.html", form=form, doctor=doctor, days=DAYS)


@doctors_bp.route("/<int:doctor_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete(doctor_id):
    """Delete a doctor only when no appointments are attached."""
    doctor = db.get_or_404(Doctor, doctor_id)
    if Appointment.query.filter_by(doctor_id=doctor.id).first():
        flash("This doctor cannot be deleted because appointments are attached.", "error")
        return redirect(url_for("doctors.detail", doctor_id=doctor.id))
    db.session.delete(doctor)
    db.session.commit()
    flash("Doctor profile deleted.", "success")
    return redirect(url_for("doctors.list_doctors"))