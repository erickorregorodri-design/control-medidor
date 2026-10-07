from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

import os

# Si el programa corre en internet (Render), usa Supabase. Si corre en tu PC, usa el archivo local.
if os.environ.get('RENDER'):
    from sqlalchemy.engine import URL
    connection_url = URL.create(
        drivername="postgresql+pg8000",
        username="postgres.eczhbmjltaropyzagdww",
        password="kx?EQ-65D+vcqYV",
        host="aws-0-sa-east-1.pooler.supabase.com",
        port=6543,
        database="postgres"
    )
    app.config['SQLALCHEMY_DATABASE_URI'] = connection_url
else:
    # Para tu PC local, vuelve a usar la base de datos que sí te funcionaba rápido
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medidores.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de la base de datos SQL
class RegistroMedidor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    lectura_p1 = db.Column(db.Float, nullable=False)
    lectura_p2 = db.Column(db.Float, nullable=False)
    monto_boleta = db.Column(db.Float, nullable=True)
    
    # Campos que calcularemos automáticamente
    consumo_p1 = db.Column(db.Float, default=0.0)
    consumo_p2 = db.Column(db.Float, default=0.0)
    porcentaje_p1 = db.Column(db.Float, default=0.0)
    porcentaje_p2 = db.Column(db.Float, default=0.0)
    pago_p1 = db.Column(db.Float, default=0.0)
    pago_p2 = db.Column(db.Float, default=0.0)

@app.route('/', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def index():
    db.create_all()  # <--- AGREGA ESTA LÍNEA AQUÍ MISMO (asegúrate de darle 4 espacios a la derecha)
    if request.method == 'POST':
        # 1. Capturar datos del formulario HTML
        lectura_actual_p1 = float(request.form.get('valor_p1'))
        lectura_actual_p2 = float(request.form.get('valor_p2'))
        monto = request.form.get('monto_boleta')
        monto_total = float(monto) if monto else 0.0
        
        # Capturar la fecha seleccionada por el usuario
        fecha_str = request.form.get('fecha_lectura')
        fecha_objeto = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else datetime.utcnow().date()

        # Valores por defecto para los cálculos
        cons_p1, cons_p2 = 0.0, 0.0
        pct_p1, pct_p2 = 0.0, 0.0
        pago_p1, pago_p2 = 0.0, 0.0

        # 2. Buscar la última lectura registrada que sea anterior o igual a la fecha ingresada
        # Esto asegura cálculos correctos si ingresas datos antiguos de manera desordenada
        ultima_lectura = RegistroMedidor.query.filter(RegistroMedidor.fecha < fecha_objeto)\
                                              .order_by(RegistroMedidor.fecha.desc())\
                                              .first()
        
        if ultima_lectura:
            # Calculamos el consumo restando la lectura actual menos la anterior
            cons_p1 = max(0.0, lectura_actual_p1 - ultima_lectura.lectura_p1)
            cons_p2 = max(0.0, lectura_actual_p2 - ultima_lectura.lectura_p2)
            consumo_total = cons_p1 + cons_p2
            
            if consumo_total > 0:
                # Calcular porcentajes de uso del periodo
                pct_p1 = (cons_p1 / consumo_total) * 100
                pct_p2 = (cons_p2 / consumo_total) * 100
                
                # Calcular montos a pagar basándose en el porcentaje
                pago_p1 = (pct_p1 / 100) * monto_total
                pago_p2 = (pct_p2 / 100) * monto_total

        # 3. Guardar todo en la base de datos SQL con la fecha elegida
        nuevo_registro = RegistroMedidor(
            fecha=fecha_objeto,
            lectura_p1=lectura_actual_p1,
            lectura_p2=lectura_actual_p2,
            monto_boleta=monto_total,
            consumo_p1=cons_p1,
            consumo_p2=cons_p2,
            porcentaje_p1=round(pct_p1, 2),
            porcentaje_p2=round(pct_p2, 2),
            pago_p1=round(pago_p1, 2),
            pago_p2=round(pago_p2, 2)
        )
        db.session.add(nuevo_registro)
        db.session.commit()
        
        return redirect(url_for('index'))
    
    # Obtener el historial completo ordenado por fecha de forma descendente
    historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).all()
    return render_template('index.html', historial=historial)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Cambiamos el puerto al 8080 para evitar bloqueos locales
    app.run(debug=True, port=8080)
