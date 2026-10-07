import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

DATABASE_DIR = '/app/data'
if os.environ.get('PORT') or os.environ.get('DATABASE_URL'):
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR, exist_ok=True)
    DATABASE_PATH = os.path.join(DATABASE_DIR, 'medidores.db')
else:
    DATABASE_PATH = 'medidores.db'

app = Flask(__name__)
app.secret_key = 'mi_llave_secreta_super_segura_medidores_2026'

# DOS ROLES DE USUARIO COMPLETAMENTE INTEGRADOS
USUARIOS = {
    "admin": {"clave": "medidor2026", "rol": "administrador"},
    "lector": {"clave": "ver2026", "rol": "solo_lectura"}
}

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

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

from datetime import timedelta
@app.before_request
def controlar_tiempo_sesion():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=1) # Mantiene tu prueba de 1 minuto activa
    if 'logeado' in session:
        session.modified = True

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        usuario_input = request.form['username']
        clave_input = request.form['password']
        
        if usuario_input in USUARIOS and USUARIOS[usuario_input]['clave'] == clave_input:
            session['logeado'] = True
            session['usuario'] = usuario_input
            session['rol'] = USUARIOS[usuario_input]['rol']
            return redirect(url_for('index'))
        else:
            error = 'Usuario o contraseña incorrectos.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logeado'):
        return redirect(url_for('login'))
        
    error_validacion = None
    ultimo_registro = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).first()
        
    if request.method == 'POST':
        # Bloqueo estricto por si un usuario lector intenta enviar datos a la fuerza
        if session.get('rol') == 'solo_lectura':
            return redirect(url_for('index'))

        lectura_actual_p1 = float(request.form.get('valor_p1'))
        lectura_actual_p2 = float(request.form.get('valor_p2'))
        monto = request.form.get('monto_boleta')
        monto_total = float(monto) if monto else 0.0
        fecha_str = request.form.get('fecha_lectura')
        fecha_objeto = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else datetime.utcnow().date()

        if ultimo_registro:
            if fecha_objeto <= ultimo_registro.fecha:
                error_validacion = f"⚠️ Error: La fecha debe ser posterior al último registro."
                historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.asc()).all()
                return render_template('index.html', historial=historial[::-1], ultimo=ultimo_registro, error_validacion=error_validacion)
                
            if lectura_actual_p1 < ultimo_registro.lectura_p1 or lectura_actual_p2 < ultimo_registro.lectura_p2:
                error_validacion = f"⚠️ Error: Las lecturas no pueden ser menores al último registro."
                historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.asc()).all()
                return render_template('index.html', historial=historial[::-1], ultimo=ultimo_registro, error_validacion=error_validacion)

        cons_p1, cons_p2 = 0.0, 0.0
        pct_p1, pct_p2 = 0.0, 0.0
        pago_p1, pago_p2 = 0.0, 0.0

        ultima_lectura = RegistroMedidor.query.filter(RegistroMedidor.fecha < fecha_objeto).order_by(RegistroMedidor.fecha.desc()).first()
        
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
    
    # Mandamos los registros ordenados cronológicamente (antiguo a nuevo) para graficar bien
    historial_cronologico = RegistroMedidor.query.order_by(RegistroMedidor.fecha.asc()).all()
    # La tabla los muestra del más nuevo al más antiguo
    return render_template('index.html', historial=historial_cronologico[::-1], historial_grafico=historial_cronologico, ultimo=ultimo_registro, error_validacion=error_validacion)

@app.route('/editar/<int:id>', methods=['POST'])
def editar(id):
    if not session.get('logeado') or session.get('rol') == 'solo_lectura':
        return redirect(url_for('index'))
    
    registro = RegistroMedidor.query.get_or_404(id)
    lectura_actual_p1 = float(request.form.get('valor_p1'))
    lectura_actual_p2 = float(request.form.get('valor_p2'))
    monto = request.form.get('monto_boleta')
    monto_total = float(monto) if monto else 0.0
    fecha_str = request.form.get('fecha_lectura')
    fecha_objeto = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else registro.fecha

    ultima_lectura = RegistroMedidor.query.filter(RegistroMedidor.fecha < fecha_objeto, RegistroMedidor.id != id).order_by(RegistroMedidor.fecha.desc()).first()
    
    cons_p1, cons_p2 = 0.0, 0.0
    pct_p1, pct_p2 = 0.0, 0.0
    pago_p1, pago_p2 = 0.0, 0.0

    if ultima_lectura:
        cons_p1 = max(0.0, lectura_actual_p1 - ultima_lectura.lectura_p1)
        cons_p2 = max(0.0, lectura_actual_p2 - ultima_lectura.lectura_p2)
        consumo_total = cons_p1 + cons_p2
        if consumo_total > 0:
            pct_p1 = (cons_p1 / consumo_total) * 100
            pct_p2 = (cons_p2 / consumo_total) * 100
            pago_p1 = (pct_p1 / 100) * monto_total
            pago_p2 = (pct_p2 / 100) * monto_total

    registro.fecha = fecha_objeto
    registro.lectura_p1 = lectura_actual_p1
    registro.lectura_p2 = lectura_actual_p2
    registro.monto_boleta = monto_total
    registro.consumo_p1 = round(cons_p1, 2)
    registro.consumo_p2 = round(cons_p2, 2)
    registro.porcentaje_p1 = round(pct_p1, 1)
    registro.porcentaje_p2 = round(pct_p2, 1)
    registro.pago_p1 = round(pago_p1, 0)
    registro.pago_p2 = round(pago_p2, 0)
    
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if not session.get('logeado') or session.get('rol') == 'solo_lectura':
        return redirect(url_for('index'))
    registro = RegistroMedidor.query.get_or_404(id)
    db.session.delete(registro)
    db.session.commit()
    return redirect(url_for('index'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=8080)
