from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "supersecreto"  # ⚠️ cámbialo en producción
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///recolectores.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Orden fijo para mostrar los días en los registros
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


# -------------------------
# MODELOS
# -------------------------
class Recolector(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    dia = db.Column(db.String(15), nullable=False)  # día de la semana
    cantidad_recolectada = db.Column(db.Float, default=0.0)
    total_alimentacion = db.Column(db.Float, default=0.0)
    total_no_alimentacion = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<Recolector {self.nombre} {self.apellido} - {self.dia}>"


# -------------------------
# RUTAS PRINCIPALES
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/calcular", methods=["POST"])
def calcular():
    try:
        valor = float(request.form["valor_carga_cafe"])
        precio_kilo_alimentacion = float(request.form["precio_kilo_alimentacion"])
        precio_kilo_no_alimentacion = float(request.form["precio_kilo_no_alimentacion"])

        cafe_seco = float(request.form["cafe_seco"])
        cafe_verde = float(request.form["cafe_verde"])
        cafe_colorado = float(request.form["cafe_colorado"])
    except (KeyError, ValueError):
        flash("Error en los datos ingresados. Verifica los valores numéricos.", "error")
        return redirect(url_for("index"))

    # Cálculos
    porcentaje_seco = cafe_seco
    porcentaje_verde = cafe_verde * 0.92
    porcentaje_colorado = cafe_colorado * 0.35
    porcentaje_colorado_seco = porcentaje_colorado * 0.60

    valor_seco = valor / 125
    valor_verde = valor / 250
    valor_colorado = valor / 250

    Precio_seco = valor_seco * porcentaje_seco
    Precio_verde = valor_verde * porcentaje_verde
    Precio_colorado = valor_colorado * porcentaje_colorado
    Precio_total = Precio_seco + Precio_verde + Precio_colorado

    return render_template(
        "resultado.html",
        Precio_seco=Precio_seco,
        Precio_verde=Precio_verde,
        Precio_colorado=Precio_colorado,
        porcentaje_seco=porcentaje_seco,
        porcentaje_verde=porcentaje_verde,
        porcentaje_colorado=porcentaje_colorado,
        porcentaje_colorado_seco=porcentaje_colorado_seco,
        valor_seco=valor_seco,
        valor_verde=valor_verde,
        valor_colorado=valor_colorado,
        Precio_total=Precio_total,
    )


# -------------------------
# RECOLECTORES
# -------------------------
@app.route("/tabla_recolectores")
def tabla_recolectores():
    recolectores = Recolector.query.all()
    return render_template("tabla_recolectores.html", recolectores=recolectores)


@app.route("/guardar_recolectores", methods=["POST"])
def guardar_recolectores():
    try:
        nombres = request.form.getlist("nombre[]")
        apellidos = request.form.getlist("apellido[]")
        dias = request.form.getlist("dia[]")
        cantidades = request.form.getlist("cantidad_recolectada[]")
        precio_alimentacion = float(request.form["precio_alimentacion"])
        precio_no_alimentacion = float(request.form["precio_no_alimentacion"])
    except (KeyError, ValueError):
        flash("Error en los datos ingresados. Verifica los valores numéricos.", "error")
        return redirect(url_for("tabla_recolectores"))

    # Eliminar registros anteriores
    Recolector.query.delete()

    for i in range(len(nombres)):
        nombre = (nombres[i] or "").strip()
        apellido = (apellidos[i] or "").strip()
        dia = (dias[i] or "").strip() or "Lunes"
        try:
            cantidad = float(cantidades[i]) if cantidades[i] else 0.0
        except ValueError:
            cantidad = 0.0

        total_alim = cantidad * precio_alimentacion
        total_no_alim = cantidad * precio_no_alimentacion

        recolector = Recolector(
            nombre=nombre,
            apellido=apellido,
            dia=dia,
            cantidad_recolectada=cantidad,
            total_alimentacion=total_alim,
            total_no_alimentacion=total_no_alim,
        )
        db.session.add(recolector)

    try:
        db.session.commit()
        flash("Registros guardados correctamente.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Error al guardar en la base de datos.", "error")

    return redirect(url_for("tabla_recolectores"))


@app.route("/borrar_registros", methods=["POST"])
def borrar_registros():
    Recolector.query.delete()
    db.session.commit()
    flash("Todos los registros han sido borrados.", "info")
    return redirect(url_for("ver_registros"))


@app.route("/ver_registros")
def ver_registros():
    recolectores = Recolector.query.all()

    # Agrupar por recolector y día, acumulando cantidades e importes
    agrupados = defaultdict(lambda: {
        "dias": defaultdict(lambda: {"cantidad": 0.0, "alim": 0.0, "no_alim": 0.0}),
        "total_semanal": 0.0,
        "alim_semanal": 0.0,
        "no_alim_semanal": 0.0
    })

    for r in recolectores:
        key = f"{(r.nombre or '').strip()} {(r.apellido or '').strip()}".strip()
        d = r.dia or "Lunes"
        bucket = agrupados[key]["dias"][d]
        bucket["cantidad"] += float(r.cantidad_recolectada or 0.0)
        bucket["alim"] += float(r.total_alimentacion or 0.0)
        bucket["no_alim"] += float(r.total_no_alimentacion or 0.0)

        agrupados[key]["total_semanal"] += float(r.cantidad_recolectada or 0.0)
        agrupados[key]["alim_semanal"] += float(r.total_alimentacion or 0.0)
        agrupados[key]["no_alim_semanal"] += float(r.total_no_alimentacion or 0.0)

    total_alimentacion = sum(float(r.total_alimentacion or 0.0) for r in recolectores)
    total_no_alimentacion = sum(float(r.total_no_alimentacion or 0.0) for r in recolectores)

    # Convertir defaultdicts a dict para Jinja
    agrupados = {k: {
        "dias": dict(v["dias"]),
        "total_semanal": v["total_semanal"],
        "alim_semanal": v["alim_semanal"],
        "no_alim_semanal": v["no_alim_semanal"],
    } for k, v in agrupados.items()}

    return render_template(
        "registros_guardados.html",
        recolectores_agrupados=agrupados,
        dias_semana=DIAS_SEMANA,
        total_alimentacion=total_alimentacion,
        total_no_alimentacion=total_no_alimentacion,
    )


# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
