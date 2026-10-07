import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configuración Inteligente y Segura de Base de Datos
if os.environ.get('RENDER'):
    # En internet leerá la URL directamente desde el panel seguro de Render
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
else:
    # Tu configuración local de PC que te corre excelente
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medidores.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo SQL
class RegistroMedidor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=datetime.utcnow)
    lectura_p1 = db.Column(db.Float, nullable=False)
    lectura_p2 = db.Column(db.Float, nullable=False)
    monto_boleta = db.Column(db.Float, nullable=True)
    consumo_p1 = db.Column(db.Float, default=0.0)
    consumo_p2 = db.Column(db.Float, default=0.0)
    porcentaje_p1 = db.Column(db.Float, default=0.0)
    porcentaje_p2 = db.Column(db.Float, default=0.0)
    pago_p1 = db.Column(db.Float, default=0.0)
    pago_p2 = db.Column(db.Float, default=0.0)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        lectura_actual_p1 = float(request.form.get('valor_p1'))
        lectura_actual_p2 = float(request.form.get('valor_p2'))
        monto = request.form.get('monto_boleta')
        monto_total = float(monto) if monto else 0.0
        
        fecha_str = request.form.get('fecha_lectura')
        fecha_objeto = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else datetime.utcnow().date()

        cons_p1, cons_p2 = 0.0, 0.0
        pct_p1, pct_p2 = 0.0, 0.0
        pago_p1, pago_p2 = 0.0, 0.0

        # BUSCAR LA LECTURA INMEDIATAMENTE ANTERIOR EN LA HISTORIA
        ultima_lectura = RegistroMedidor.query.filter(RegistroMedidor.fecha < fecha_objeto)\
                                              .order_by(RegistroMedidor.fecha.desc())\
                                              .first()
        
        if ultima_lectura:
            cons_p1 = max(0.0, lectura_actual_p1 - ultima_lectura.lectura_p1)
            cons_p2 = max(0.0, lectura_actual_p2 - ultima_lectura.lectura_p2)
            consumo_total = cons_p1 + cons_p2
            
            if consumo_total > 0:
                pct_p1 = (cons_p1 / consumo_total) * 100
                pct_p2 = (cons_p2 / consumo_total) * 100
                pago_p1 = (pct_p1 / 100) * monto_total
                pago_p2 = (pct_p2 / 100) * monto_total

        nuevo_registro = RegistroMedidor(
            fecha=fecha_objeto, lectura_p1=lectura_actual_p1, lectura_p2=lectura_actual_p2,
            monto_boleta=monto_total, consumo_p1=round(cons_p1, 2), consumo_p2=round(cons_p2, 2),
            porcentaje_p1=round(pct_p1, 1), porcentaje_p2=round(pct_p2, 1),
            pago_p1=round(pago_p1, 0), pago_p2=round(pago_p2, 0)
        )
        db.session.add(nuevo_registro)
        db.session.commit()
        return redirect(url_for('index'))
    
    # Se obtienen los datos de forma correcta
    historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).all()
    ultimo_registro = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).first()
    
    return render_template('index.html', historial=historial, ultimo=ultimo_registro)

# RUTA PARA ELIMINAR REGISTROS
@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    registro = RegistroMedidor.query.get_or_404(id)
    db.session.delete(registro)
    db.session.commit()
    return redirect(url_for('index'))

# CORRECCIÓN EN EL ARRANQUE SEGURO CON CONTEXTO ACTIVO
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8080)
else:
    # Bloque exclusivo para que Render cree la base de datos al desplegar en internet
    with app.app_context():
        db.create_all()
