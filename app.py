import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# CONFIGURACIÓN DE CARPETA SEGURA PARA EL DISCO DURO (VOLUMEN)
DATABASE_DIR = '/app/data'
if os.environ.get('PORT') or os.environ.get('DATABASE_URL'):  # Si está en internet (Railway)
    if not os.path.exists(DATABASE_DIR):
        os.makedirs(DATABASE_DIR, exist_ok=True)
    DATABASE_PATH = os.path.join(DATABASE_DIR, 'medidores.db')
else:
    DATABASE_PATH = 'medidores.db'

# Inicializamos Flask
app = Flask(__name__)

# LLAVE SECRETA: Clave para encriptar las sesiones de usuario de forma segura
app.secret_key = 'mi_llave_secreta_super_segura_medidores_2026'

# Credenciales fijas de acceso para tu teléfono celular
USUARIO_CORRECTO = "admin"
CLAVE_CORRECTA = "medidor2026"

# BASE DE DATOS LOCAL PERMANENTE E INFALIBLE BLINDADA
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialización limpia de la base de datos
db = SQLAlchemy()
db.init_app(app)

# Modelo de Tabla SQL
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

# RUTA: PANTALLA DE LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == USUARIO_CORRECTO and request.form['password'] == CLAVE_CORRECTA:
            session['logeado'] = True
            return redirect(url_for('index'))
        else:
            error = 'Usuario o contraseña incorrectos. Inténtalo de nuevo.'
    return render_template('login.html', error=error)

# RUTA: CERRAR SESIÓN
@app.route('/logout')
def logout():
    session.pop('logeado', None)
    return redirect(url_for('login'))

# RUTA: PÁGINA PRINCIPAL PROTEGIDA
@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logeado'):
        return redirect(url_for('login'))
        
    error_validacion = None
    
    # Obtener el último registro base antes de cualquier acción
    ultimo_registro = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).first()
        
    if request.method == 'POST':
        lectura_actual_p1 = float(request.form.get('valor_p1'))
        lectura_actual_p2 = float(request.form.get('valor_p2'))
        monto = request.form.get('monto_boleta')
        monto_total = float(monto) if monto else 0.0
        
        fecha_str = request.form.get('fecha_lectura')
        fecha_objeto = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else datetime.utcnow().date()

        # VALIDACIÓN CRÍTICA EN EL SERVIDOR (Doble escudo de protección)
        if ultimo_registro:
            # 1. Validación de Fecha
            if fecha_objeto <= ultimo_registro.fecha:
                error_validacion = f"⚠️ Error: La fecha seleccionada ({fecha_objeto.strftime('%d/%m/%Y')}) debe ser posterior a la del último registro guardado ({ultimo_registro.fecha.strftime('%d/%m/%Y')})."
                historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).all()
                return render_template('index.html', historial=historial, ultimo=ultimo_registro, error_validacion=error_validacion)
                
            # 2. Validación de Lecturas
            if lectura_actual_p1 < ultimo_registro.lectura_p1 or lectura_actual_p2 < ultimo_registro.lectura_p2:
                error_validacion = f"⚠️ Error: Las lecturas ingresadas no pueden ser menores al último registro guardado (Erick: {ultimo_registro.lectura_p1} kWh / Esteban: {ultimo_registro.lectura_p2} kWh)."
                historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).all()
                return render_template('index.html', historial=historial, ultimo=ultimo_registro, error_validacion=error_validacion)

        cons_p1, cons_p2 = 0.0, 0.0
        pct_p1, pct_p2 = 0.0, 0.0
        pago_p1, pago_p2 = 0.0, 0.0

        # Buscar la lectura inmediatamente anterior para el cálculo real del período
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
    
    historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).all()
    return render_template('index.html', historial=historial, ultimo=ultimo_registro, error_validacion=error_validacion)

# RUTA: ELIMINAR REGISTROS PROTEGIDA
@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if not session.get('logeado'):
        return redirect(url_for('login'))
    registro = RegistroMedidor.query.get_or_404(id)
    db.session.delete(registro)
    db.session.commit()
    return redirect(url_for('index'))

# Asegurar la creación de tablas dentro del contexto seguro
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=8080)
