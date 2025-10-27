from flask import Flask, render_template, request, redirect, url_for
import json
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)

DATA_FILE = "data.json"

# Inicializar archivo de datos si no existe
try:
    with open(DATA_FILE, "r") as f:
        pass
except FileNotFoundError:
    with open(DATA_FILE, "w") as f:
        json.dump({
            "weight": 110.5,
            "level": 1,
            "xp": 0,
            "daily_quests": {"cardio": False, "strength": False, "stretching": False, "water": False},
            "history": []
        }, f, indent=4)

# Funciones de agrupamiento
def group_by_week(records):
    weekly = defaultdict(list)
    for r in records:
        dt = datetime.strptime(r["date"], "%Y-%m-%d")
        year, week, _ = dt.isocalendar()
        key = f"{year}-W{week}"
        weekly[key].append(r)
    result = []
    for week, items in sorted(weekly.items()):
        avg_weight = sum(i["weight"] for i in items) / len(items)
        avg_level = sum(i["level"] for i in items) / len(items)
        avg_xp = sum(i["xp"] % 1000 for i in items) / len(items)
        result.append({"label": week, "weight": avg_weight, "level": avg_level, "xp": avg_xp})
    return result

def group_by_month(records):
    monthly = defaultdict(list)
    for r in records:
        dt = datetime.strptime(r["date"], "%Y-%m-%d")
        key = dt.strftime("%Y-%m")
        monthly[key].append(r)
    result = []
    for month, items in sorted(monthly.items()):
        avg_weight = sum(i["weight"] for i in items) / len(items)
        avg_level = sum(i["level"] for i in items) / len(items)
        avg_xp = sum(i["xp"] % 1000 for i in items) / len(items)
        result.append({"label": month, "weight": avg_weight, "level": avg_level, "xp": avg_xp})
    return result

# Función para guardar datos
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Ruta Dashboard
@app.route("/")
def dashboard():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return render_template("dashboard.html", data=data)

#Ruta Daily
@app.route("/daily", methods=["GET", "POST"])
def daily():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    # Fecha seleccionada por defecto = hoy
    selected_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    # Buscar el registro de la fecha seleccionada
    history = data.setdefault("history", [])
    record = next((r for r in history if r["date"] == selected_date), None)

    if not record:
        # Si no existe, crear uno temporal con misiones desmarcadas
        record = {
            "date": selected_date,
            "daily_quests": {q: False for q in data["daily_quests"]},
            "weight": data["weight"],
            "level": data["level"],
            "xp": 0
        }

    if request.method == "POST":
        # Actualizar misiones para la fecha seleccionada
        checked = request.form.getlist("daily_quests")
        for quest in record["daily_quests"]:
            record["daily_quests"][quest] = quest in checked

        # Calcular XP de ese día
        record["xp"] = sum(100 for q in record["daily_quests"].values() if q)
        record["weight"] = float(request.form.get("weight", record["weight"]))
        record["level"] = data["level"]  # Nivel actual

        # Guardar o actualizar en el histórico
        for idx, r in enumerate(history):
            if r["date"] == selected_date:
                history[idx] = record
                break
        else:
            history.append(record)

        # Recalcular nivel y XP totales
        total_xp = sum(r["xp"] for r in history)
        data["level"] = 1 + total_xp // 1000
        data["xp"] = total_xp % 1000

        save_data(data)
        return redirect(url_for("daily", date=selected_date))

    return render_template("daily.html", data=data, record=record, selected_date=selected_date)



# Actualizar peso
@app.route("/update_weight", methods=["POST"])
def update_weight():
    new_weight = float(request.form["weight"])
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    data["weight"] = new_weight
    save_data(data)
    return redirect(url_for("daily"))

# Histórico
@app.route("/history")
def history():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    history = data.get("history", [])
    return render_template("history.html", history=history)

# Gráficas
@app.route("/charts", methods=["GET", "POST"])
def charts():
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    history = data.get("history", [])

    # Filtrado por rango de fechas si se envía POST
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    filtered_history = []
    if start_date and end_date:
        for record in history:
            if start_date <= record["date"] <= end_date:
                filtered_history.append(record)
    else:
        filtered_history = history

    daily_dates = [r["date"] for r in filtered_history]
    daily_weights = [r["weight"] for r in filtered_history]
    daily_levels = [r["level"] for r in filtered_history]
    daily_xps = [r["xp"] % 1000 for r in filtered_history]

    weekly = group_by_week(filtered_history)
    monthly = group_by_month(filtered_history)

    return render_template(
        "charts.html",
        daily_dates=daily_dates,
        daily_weights=daily_weights,
        daily_levels=daily_levels,
        daily_xps=daily_xps,
        weekly=weekly,
        monthly=monthly,
        start_date=start_date,
        end_date=end_date
    )

@app.route("/info")
def info():
    # Datos de explicación de las misiones
    missions_info = {
        "cardio": "Hacer 30 minutos de cardio. Ejemplo: correr, bici, saltar cuerda.",
        "strength": "Ejercicios de fuerza. Ejemplo: flexiones, sentadillas, pesas.",
        "stretching": "Rutina de estiramientos. Ejemplo: yoga, movilidad articular.",
        "water": "Beber 2 litros de agua."
    }
    return render_template("info.html", missions_info=missions_info)

if __name__ == "__main__":
    app.run(debug=True)
