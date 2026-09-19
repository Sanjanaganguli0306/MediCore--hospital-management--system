from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, DateField, DecimalField, HiddenField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError


class EmptyForm(FlaskForm):
    """Base CSRF-protected form for actions without fields."""

    pass


class LoginForm(FlaskForm):
    """Validate staff sign-in credentials."""

    username = StringField("Username", validators=[DataRequired(), Length(max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class StrongPassword:
    """Require a password with mixed character classes and minimum length."""

    def __call__(self, form, field):
        password = field.data or ""
        requirements = [
            (len(password) >= 12, "Password must be at least 12 characters."),
            (any(char.isupper() for char in password), "Password must include an uppercase letter."),
            (any(char.islower() for char in password), "Password must include a lowercase letter."),
            (any(char.isdigit() for char in password), "Password must include a number."),
            (any(not char.isalnum() for char in password), "Password must include a symbol."),
        ]
        for valid, message in requirements:
            if not valid:
                raise ValidationError(message)


class RegisterForm(FlaskForm):
    """Validate a new staff account."""

    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField(
        "Workspace role",
        choices=[
            ("receptionist", "Receptionist"),
            ("doctor", "Doctor"),
            ("admin", "Admin"),
        ],
        validators=[DataRequired()],
    )
    password = PasswordField("Password", validators=[DataRequired(), StrongPassword()])
    confirm_password = PasswordField(
        "Confirm password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Create account")

class PastDate:
    """Require a date field to be strictly before today."""

    def __call__(self, form, field):
        if field.data and field.data >= date.today():
            raise ValidationError("Date of birth must be in the past.")


class PatientForm(FlaskForm):
    """Validate patient demographic and contact details."""

    first_name = StringField("First name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=80)])
    dob = DateField("Date of birth", format="%Y-%m-%d", validators=[DataRequired(), PastDate()])
    gender = SelectField(
        "Gender",
        choices=[("", "Select gender"), ("F", "Female"), ("M", "Male"), ("Other", "Other")],
        validators=[DataRequired()],
    )
    blood_group = SelectField(
        "Blood group",
        choices=[("", "Select blood group"), ("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"), ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-")],
    )
    phone = StringField("Phone", validators=[DataRequired(), Regexp(r"^\d{10}$", message="Phone must contain exactly 10 digits.")])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    address = TextAreaField("Address", validators=[Length(max=500)])
    emergency_contact_name = StringField("Emergency contact name", validators=[Length(max=120)])
    emergency_contact_phone = StringField("Emergency contact phone", validators=[Regexp(r"^\d{10}$", message="Phone must contain exactly 10 digits.")])
    allergies = TextAreaField("Allergies", validators=[Length(max=500)])
    submit = SubmitField("Save patient")


class DoctorForm(FlaskForm):
    """Validate doctor profile and availability details."""

    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    specialization = StringField("Specialization", validators=[DataRequired(), Length(max=100)])
    qualification = StringField("Qualification", validators=[Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Regexp(r"^\d{10}$", message="Phone must contain exactly 10 digits.")])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    years_experience = IntegerField("Years of experience", validators=[Optional()])
    hospital_branch = StringField("Hospital branch", validators=[Length(max=120)])
    consultation_fee = DecimalField("Consultation fee", places=2, validators=[DataRequired()])
    day_mon = BooleanField("Monday")
    day_tue = BooleanField("Tuesday")
    day_wed = BooleanField("Wednesday")
    day_thu = BooleanField("Thursday")
    day_fri = BooleanField("Friday")
    day_sat = BooleanField("Saturday")
    day_sun = BooleanField("Sunday")
    available_from = TimeField("Available from", format="%H:%M", validators=[DataRequired()])
    available_to = TimeField("Available to", format="%H:%M", validators=[DataRequired()])
    status = SelectField(
        "Status",
        choices=[("active", "Active"), ("on_leave", "On leave"), ("inactive", "Inactive")],
        validators=[DataRequired()],
    )
    profile_photo = FileField(
        "Profile photo",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Upload a JPEG, PNG, or WebP image.")],
    )
    bio = TextAreaField("Bio", validators=[Length(max=1000)])
    submit = SubmitField("Save doctor")


class AppointmentForm(FlaskForm):
    """Validate the patient, doctor, date, and requested appointment slot."""

    patient_id = HiddenField(validators=[DataRequired()])
    patient_search = StringField("Patient", validators=[DataRequired()])
    doctor_id = SelectField("Doctor", coerce=int, validators=[DataRequired()])
    appointment_date = DateField("Appointment date", format="%Y-%m-%d", validators=[DataRequired()])
    appointment_time = HiddenField(validators=[DataRequired()])
    reason = TextAreaField("Reason for visit", validators=[Length(max=1000)])
    notes = TextAreaField("Notes", validators=[Length(max=2000)])
    submit = SubmitField("Book appointment")

    def validate_consultation_fee(self, field):
        """Require a non-negative consultation fee."""
        if field.data is not None and field.data < 0:
            raise ValidationError("Consultation fee cannot be negative.")

    def validate_available_to(self, field):
        """Require the availability end time after the start time."""
        if self.available_from.data and field.data and field.data <= self.available_from.data:
            raise ValidationError("Available to must be after available from.")
