from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from app import db
from app.models import Appointment, Invoice, InvoiceItem, Patient
from app.security.audit import record_event
from app.security.permissions import permission_required
from app.utils import role_required


billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


def money(value, default=Decimal("0")):
    """Parse a non-negative decimal value from a form field."""
    try:
        parsed = Decimal(value or default)
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def next_invoice_number():
    """Generate a readable invoice number without relying on a database sequence."""
    return f"INV-{Invoice.query.count() + 1:04d}"


def invoice_status(total, paid):
    """Return the payment status for an invoice balance."""
    if paid >= total:
        return "paid"
    if paid > 0:
        return "partial"
    return "unpaid"


def billable_appointments():
    """Return completed visits that have not yet received an invoice."""
    return (
        Appointment.query.filter_by(status="completed")
        .outerjoin(Invoice)
        .filter(Invoice.id.is_(None))
        .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        .all()
    )


@billing_bp.route("")
@permission_required("billing.write")
def list_invoices():
    """Render searchable invoices and their payment state."""
    query = Invoice.query.join(Patient)
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(Invoice.invoice_no.ilike(term), Patient.first_name.ilike(term), Patient.last_name.ilike(term))
        )
    if status:
        query = query.filter(Invoice.status == status)
    invoices = query.order_by(Invoice.issue_date.desc(), Invoice.id.desc()).all()
    return render_template("billing/list.html", invoices=invoices, query=search, selected_status=status)


@billing_bp.route("/new", methods=["GET", "POST"])
@permission_required("billing.write")
def new_invoice():
    """Create an invoice connected to a patient or completed visit."""
    patients = Patient.query.order_by(Patient.last_name, Patient.first_name).all()
    appointments = billable_appointments()
    selected_appointment_id = request.args.get("appointment_id", type=int)
    selected_patient_id = request.args.get("patient_id", type=int)
    form_data = request.form
    if request.method == "POST":
        selected_patient_id = request.form.get("patient_id", type=int)
        selected_appointment_id = request.form.get("appointment_id", type=int)
        patient = db.session.get(Patient, selected_patient_id)
        description = request.form.get("description", "").strip()
        quantity = request.form.get("quantity", "1", type=int)
        unit_price = money(request.form.get("unit_price"))
        tax_percent = money(request.form.get("tax_percent"))
        discount = money(request.form.get("discount"))
        amount_paid = money(request.form.get("amount_paid"))
        appointment = db.session.get(Appointment, selected_appointment_id) if selected_appointment_id else None
        billable_appointment_ids = {billable_appointment.id for billable_appointment in appointments}
        if (
            not patient
            or not description
            or not quantity
            or unit_price is None
            or tax_percent is None
            or discount is None
            or amount_paid is None
            or (appointment and (appointment.id not in billable_appointment_ids or appointment.patient_id != patient.id))
        ):
            flash("Complete the patient, charge, quantity, and valid amount fields.", "error")
        else:
            subtotal = unit_price * quantity
            total = max(Decimal("0"), subtotal + (subtotal * tax_percent / Decimal("100")) - discount)
            amount_paid = min(amount_paid, total)
            invoice = Invoice(
                invoice_no=next_invoice_number(), patient=patient, appointment=appointment,
                issue_date=date.today(), due_date=date.fromisoformat(request.form["due_date"]) if request.form.get("due_date") else date.today(),
                subtotal=subtotal, tax_percent=tax_percent, discount=discount, total=total,
                amount_paid=amount_paid, status=invoice_status(total, amount_paid), payment_method=request.form.get("payment_method") or None,
            )
            invoice.invoice_items.append(InvoiceItem(description=description, quantity=quantity, unit_price=unit_price, amount=unit_price * quantity))
            db.session.add(invoice)
            db.session.commit()
            record_event("invoice_created", resource_type="invoice", resource_id=invoice.id)
            flash(f"{invoice.invoice_no} created successfully.", "success")
            return redirect(url_for("billing.detail", invoice_id=invoice.id))
    selected_appointment = next(
        (appointment for appointment in appointments if appointment.id == selected_appointment_id),
        None,
    )
    if selected_appointment:
        selected_patient_id = selected_appointment.patient_id
    selected_patient = db.session.get(Patient, selected_patient_id) if selected_patient_id else None
    default_description = (
        f"Consultation - {selected_appointment.doctor.full_name}"
        if selected_appointment
        else ""
    )
    default_unit_price = (
        str(selected_appointment.doctor.consultation_fee)
        if selected_appointment
        else ""
    )
    return render_template(
        "billing/form.html",
        patients=patients,
        appointments=appointments,
        selected_appointment_id=selected_appointment_id,
        selected_patient_id=selected_patient_id,
        selected_patient=selected_patient,
        form_data=form_data,
        default_description=default_description,
        default_unit_price=default_unit_price,
        today=date.today().isoformat(),
    )


@billing_bp.route("/<int:invoice_id>")
@permission_required("billing.write")
def detail(invoice_id):
    """Render invoice details and the payment form."""
    return render_template("billing/detail.html", invoice=db.get_or_404(Invoice, invoice_id))


@billing_bp.route("/<int:invoice_id>/payment", methods=["POST"])
@permission_required("billing.write")
def record_payment(invoice_id):
    """Apply a payment and recalculate the invoice state."""
    invoice = db.get_or_404(Invoice, invoice_id)
    payment = money(request.form.get("amount"))
    if payment is None or payment <= 0:
        flash("Enter a payment amount greater than zero.", "error")
    else:
        invoice.amount_paid = min(invoice.total, invoice.amount_paid + payment)
        invoice.payment_method = request.form.get("payment_method") or invoice.payment_method
        invoice.status = invoice_status(invoice.total, invoice.amount_paid)
        db.session.commit()
        record_event("payment_recorded", resource_type="invoice", resource_id=invoice.id)
        flash("Payment recorded successfully.", "success")
    return redirect(url_for("billing.detail", invoice_id=invoice.id))