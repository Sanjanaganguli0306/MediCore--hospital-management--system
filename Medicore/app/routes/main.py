from datetime import date

from flask import Blueprint, flash, render_template, request
from flask_login import login_required

from app.models import Invoice, Patient, Doctor, Appointment

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def landing():
    """Render the public MediCore landing page."""
    return render_template("main/landing.html")


@main_bp.route("/services")
def services():
    """Render the public services overview."""
    return render_template("main/services.html")


@main_bp.route("/about")
def about():
    """Render the public MediCore story page."""
    return render_template("main/about.html")


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Render the contact page and acknowledge submitted enquiries."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not email or not message:
            flash("Please complete your name, email, and message.", "error")
        else:
            flash("Thanks for reaching out. Our care team will be in touch soon.", "success")
            return render_template("main/contact.html", submitted=True)
    return render_template("main/contact.html", submitted=False)


@main_bp.route("/terms")
def terms():
    """Render the public terms and privacy overview."""
    return render_template("main/terms.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """Render the focused MediCore workspace dashboard."""
    return render_template(
        "main/dashboard.html",
        patient_count=Patient.query.count(),
        doctor_count=Doctor.query.count(),
        appointment_count=Appointment.query.filter_by(appointment_date=date.today()).count(),
        pending_invoice_count=Invoice.query.filter(Invoice.status != "paid").count(),
    )
