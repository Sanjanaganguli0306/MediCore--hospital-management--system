from datetime import datetime, time, timedelta
from urllib.parse import urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.forms import LoginForm, RegisterForm
from app.models import Doctor, User
from app.security.audit import record_event


auth_bp = Blueprint("auth", __name__)
MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate a staff user and honor a safe next destination."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.username == form.username.data.strip()))
        now = datetime.utcnow()
        if user and user.locked_until and user.locked_until <= now:
            user.failed_login_count = 0
            user.locked_until = None
        if user and user.locked_until and user.locked_until > now:
            record_event("login_failed", success=False, context="account_locked")
            flash("Invalid username or password.", "error")
        elif user and user.is_active and user.check_password(form.password.data):
            user.failed_login_count = 0
            user.locked_until = None
            user.last_login_at = now
            db.session.commit()
            login_user(user, remember=form.remember_me.data, fresh=True)
            record_event("login", success=True, commit=True)
            next_url = request.args.get("next")
            if next_url and urlparse(urljoin(request.host_url, next_url)).netloc == request.host:
                return redirect(next_url)
            return redirect(url_for("main.dashboard"))
        else:
            if user:
                user.failed_login_count += 1
                if user.failed_login_count >= MAX_FAILED_LOGINS:
                    user.locked_until = now + LOCKOUT_DURATION
                db.session.commit()
            record_event("login_failed", success=False, context="invalid_credentials")
            flash("Invalid username or password.", "error")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a staff account after validating unique identity fields."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        if db.session.scalar(db.select(User).where(User.username == username)):
            form.username.errors.append("That username is already in use.")
        elif db.session.scalar(db.select(User).where(User.email == email)):
            form.email.errors.append("That email is already in use.")
        else:
            user = User(
                full_name=form.full_name.data.strip(),
                username=username,
                email=email,
                role=form.role.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            if user.role == "doctor":
                display_name = user.full_name if user.full_name.lower().startswith("dr.") else f"Dr. {user.full_name}"
                db.session.add(Doctor(
                    user_id=user.id,
                    full_name=display_name,
                    specialization="Clinical specialist",
                    email=user.email,
                    available_days="Mon,Tue,Wed,Thu,Fri",
                    available_from=time(9, 0),
                    available_to=time(17, 0),
                    status="active",
                ))
            db.session.commit()
            login_user(user, fresh=True)
            record_event("registration", success=True, commit=True)
            flash("Account created. Welcome to your MediCore workspace.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """End the current staff session."""
    record_event("logout", success=True)
    logout_user()
    flash("You have been signed out.", "success")
    return redirect(url_for("main.landing"))
