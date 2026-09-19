import argparse
import csv
import os
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path

from app import create_app, db
from app.models import Appointment, Doctor, Invoice, InvoiceItem, MedicalRecord, Patient, Treatment, User


STATUS_MAP = {
    "Scheduled": "scheduled",
    "Completed": "completed",
    "Cancelled": "cancelled",
    "No-show": "no_show",
}
PAYMENT_METHOD_MAP = {
    "Cash": "cash",
    "Credit Card": "card",
    "Card": "card",
    "UPI": "upi",
    "Insurance": "insurance",
}


def parse_date(value):
    """Parse a dataset ISO date."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def read_rows(dataset_dir, filename):
    """Read a UTF-8 CSV file from the dataset directory."""
    with (dataset_dir / filename).open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def build_invoice_status(payment_status, amount):
    """Convert source payment labels into the invoice status contract."""
    return "paid" if payment_status.lower() == "paid" else "unpaid"


def import_dataset(dataset_dir):
    """Drop, recreate, and import the MediCore CSV dataset."""
    patients = read_rows(dataset_dir, "patients.csv")
    doctors = read_rows(dataset_dir, "doctors.csv")
    appointments = read_rows(dataset_dir, "appointments.csv")
    billing = read_rows(dataset_dir, "billing.csv")
    treatments = read_rows(dataset_dir, "treatments.csv")

    db.drop_all()
    db.create_all()

    bootstrap_password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
    if not bootstrap_password:
        raise RuntimeError("Set BOOTSTRAP_ADMIN_PASSWORD before importing a dataset")
    admin = User(
        full_name="MediCore Administrator",
        username="admin",
        email="admin@medicore.local",
        role="admin",
    )
    admin.set_password(bootstrap_password)
    db.session.add(admin)

    patient_map = {}
    for row in patients:
        patient = Patient(
            patient_code=row["patient_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            dob=parse_date(row["date_of_birth"]),
            gender=row["gender"],
            phone=row["contact_number"],
            email=row.get("email") or None,
            address=row.get("address") or None,
            registration_date=parse_date(row["registration_date"]),
            insurance_provider=row.get("insurance_provider") or None,
            insurance_number=row.get("insurance_number") or None,
        )
        db.session.add(patient)
        patient_map[row["patient_id"]] = patient

    doctor_map = {}
    for row in doctors:
        doctor = Doctor(
            full_name=f"Dr. {row['first_name']} {row['last_name']}",
            specialization=row["specialization"],
            phone=row["phone_number"],
            email=row.get("email") or None,
            years_experience=int(row["years_experience"]),
            hospital_branch=row.get("hospital_branch") or None,
            available_days="Mon,Tue,Wed,Thu,Fri",
            available_from=time(9, 0),
            available_to=time(17, 0),
            status="active",
        )
        db.session.add(doctor)
        doctor_map[row["doctor_id"]] = doctor

    db.session.flush()

    appointment_map = {}
    for row in appointments:
        appointment = Appointment(
            patient=patient_map[row["patient_id"]],
            doctor=doctor_map[row["doctor_id"]],
            appointment_date=parse_date(row["appointment_date"]),
            appointment_time=datetime.strptime(row["appointment_time"], "%H:%M:%S").time(),
            reason=row.get("reason_for_visit") or None,
            status=STATUS_MAP.get(row["status"], "scheduled"),
            created_by=admin.id,
        )
        db.session.add(appointment)
        appointment_map[row["appointment_id"]] = appointment

    db.session.flush()
    treatment_map = {}
    for row in treatments:
        treatment = Treatment(
            treatment_code=row["treatment_id"],
            appointment=appointment_map[row["appointment_id"]],
            treatment_type=row["treatment_type"],
            description=row.get("description") or None,
            cost=Decimal(row["cost"]),
            treatment_date=parse_date(row["treatment_date"]),
        )
        db.session.add(treatment)
        treatment_map[row["treatment_id"]] = treatment
        appointment = appointment_map[row["appointment_id"]]
        db.session.add(MedicalRecord(
            patient=appointment.patient,
            doctor=appointment.doctor,
            appointment=appointment,
            visit_date=treatment.treatment_date,
            complaint=appointment.reason,
            diagnosis=treatment.treatment_type,
            treatment=treatment.description,
        ))

    db.session.flush()
    for row in billing:
        amount = Decimal(row["amount"])
        treatment = treatment_map[row["treatment_id"]]
        appointment = treatment.appointment
        invoice = Invoice(
            invoice_no=row["bill_id"],
            patient=appointment.patient,
            appointment=appointment,
            issue_date=parse_date(row["bill_date"]),
            due_date=parse_date(row["bill_date"]),
            subtotal=amount,
            total=amount,
            amount_paid=amount if row["payment_status"].lower() == "paid" else Decimal("0"),
            status=build_invoice_status(row["payment_status"], amount),
            payment_method=PAYMENT_METHOD_MAP.get(row["payment_method"], "cash"),
        )
        invoice.invoice_items.append(InvoiceItem(
            description=f"{treatment.treatment_type} — {treatment.description or 'Treatment'}",
            quantity=1,
            unit_price=amount,
            amount=amount,
        ))
        db.session.add(invoice)

    db.session.commit()
    return {
        "patients": len(patients),
        "doctors": len(doctors),
        "appointments": len(appointments),
        "treatments": len(treatments),
        "invoices": len(billing),
    }


def main():
    """Import the configured MediCore dataset."""
    parser = argparse.ArgumentParser(description="Import MediCore CSV data")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(os.environ.get("MEDICORE_DATASET_DIR", r"E:\MediCore dataset")),
        help="Directory containing patients.csv, doctors.csv, appointments.csv, billing.csv, and treatments.csv",
    )
    args = parser.parse_args()
    if not args.dataset.is_dir():
        raise SystemExit(f"Dataset directory does not exist: {args.dataset}")

    app = create_app()
    with app.app_context():
        counts = import_dataset(args.dataset)
    print("MediCore dataset imported successfully")
    for name, count in counts.items():
        print(f"{name}: {count}")
    print("Bootstrap admin created from BOOTSTRAP_ADMIN_PASSWORD")


if __name__ == "__main__":
    main()