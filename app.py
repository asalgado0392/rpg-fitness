from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import uuid

# --- CONFIGURACIÓN BASE ---
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:zordon01578426A!@db.yozknwunqvvtzymlrmlb.supabase.co:5432/postgres"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- MODELOS ---
class UserProfile(db.Model):
    __tablename__ = "user_profiles"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String, unique=True)
    weight = db.Column(db.Numeric(5, 2))
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


class DailyQuest(db.Model):
    __tablename__ = "daily_quests"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String)
    date = db.Column(db.Date)
    cardio = db.Column(db.Boolean, default=False)
    strength = db.Column(db.Boolean, default=False)
    stretching = db.Column(db.Boolean, default=False)
    water = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class History(db.Model):
    __tablename__ = "history"
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String)
    date = db.Column(db.Date)
    weight = db.Column(db.Numeric(5, 2))
    level = db.Column(db.Integer)
    xp = db.Column(db.Integer)
    cardio = db.Column(db.Boolean, default=False)
    strength = db.Column(db.Boolean, default=False)
    stretching = db.Column(db.Boolean, default=False)
    water = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- FUNCIONES AUXILIARES ---
def get_or_create_profile(user_id="demo-user"):
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id, weight=0, level=1, xp=0)
        db.session.add(profile)
        db.session.commit()
    return profile


def calculate_xp(cardio, strength, stretching, water):
    xp = 0
    if cardio:
        xp += 10
    if strength:
        xp += 10
    if stretching:
        xp += 10
    if water:
        xp += 10
    return xp


# --- RUTAS PRINCIPALES ---
@app.route("/")
def dashboard():
    user_id = "demo-user"
    profile = get_or_create_profile(user_id)
    progress = min(100, (profile.xp % 100))
    return render_template("dashboard.html", level=profile.level, xp=profile.xp, progress=progress)


@app.route("/daily", methods=["GET", "POST"])
def daily():
    user_id = "demo-user"
    profile = get_or_create_profile(user_id)
    today = date.today()

    selected_date_str = request.args.get("date")
    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
    else:
        selected_date = today

    quest = DailyQuest.query.filter_by(user_id=user_id, date=selected_date).first()

    if request.method == "POST":
        cardio = "cardio" in request.form
        strength = "strength" in request.form
        stretching = "stretching" in request.form
        water = "water" in request.form

        if not quest:
            quest = DailyQuest(
                user_id=user_id,
                date=selected_date,
                cardio=cardio,
                strength=strength,
                stretching=stretching,
                water=water,
            )
            db.session.add(quest)
        else:
            quest.cardio = cardio
            quest.strength = strength
            quest.stretching = stretching
            quest.water = water

        # Calcular XP total
        new_xp = calculate_xp(cardio, strength, stretching, water)
        profile.xp = new_xp
        profile.level = 1 + profile.xp // 100
        profile.updated_at = datetime.utcnow()

        # Guardar histórico
        history = History.query.filter_by(user_id=user_id, date=selected_date).first()
        if not history:
            history = History(
                user_id=user_id,
                date=selected_date,
                weight=profile.weight,
                level=profile.level,
                xp=profile.xp,
                cardio=cardio,
                strength=strength,
                stretching=stretching,
                water=water,
            )
            db.session.add(history)
        else:
            history.level = profile.level
            history.xp = profile.xp
            history.cardio = cardio
            history.strength = strength
            history.stretching = stretching
            history.water = water

        db.session.commit()
        return redirect(url_for("daily", date=selected_date))

    return render_template(
        "daily.html",
        selected_date=selected_date,
        quest=quest,
        level=profile.level,
        xp=profile.xp,
    )


@app.route("/update_weight", methods=["POST"])
def update_weight():
    user_id = "demo-user"
    profile = get_or_create_profile(user_id)
    weight = request.form.get("weight")

    if weight:
        profile.weight = weight
        profile.updated_at = datetime.utcnow()

        # Registrar en histórico
        history = History.query.filter_by(user_id=user_id, date=date.today()).first()
        if not history:
            history = History(
                user_id=user_id,
                date=date.today(),
                weight=weight,
                level=profile.level,
                xp=profile.xp,
            )
            db.session.add(history)
        else:
            history.weight = weight
        db.session.commit()

    return redirect(url_for("daily"))


@app.route("/history")
def history():
    user_id = "demo-user"
    records = History.query.filter_by(user_id=user_id).order_by(History.date.desc()).all()
    return render_template("history.html", records=records)


@app.route("/charts")
def charts():
    user_id = "demo-user"
    records = History.query.filter_by(user_id=user_id).order_by(History.date.asc()).all()
    labels = [r.date.strftime("%d-%m") for r in records]
    weights = [float(r.weight) if r.weight else None for r in records]
    xp_values = [r.xp for r in records]
    return render_template("charts.html", labels=labels, weights=weights, xp_values=xp_values)


@app.route("/info")
def info():
    return render_template("info.html")


# --- EJECUCIÓN LOCAL ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
