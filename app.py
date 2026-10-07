import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Instanciamos la aplicación de Flask de forma limpia
app = Flask(__name__)

# LLAVE SECRETA: Necesaria para activar las sesiones seguras en Flask
app.secret_key = 'mi_llave_secreta_super_segura_medidores'

# Credenciales fijas de acceso (Puedes cambiarlas aquí a tu gusto)
USUARIO_CORRECTO = "admin"
CLAVE_CORRECTA = "medidor2026"

# CONFIGURACIÓN INTELIGENTE DEFINITIVA (PC usa SQLite / Internet usa Supabase de forma directa)
if os.environ.get('RENDER') or os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('PORT'):
    # Cadena directa y robusta con el conector estándar de la industria (+psycopg2)
    # Cambiamos el signo más '+' por '%2B' para cumplir las reglas de SQLAlchemy en la nube
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres.eczhbmjltaropyzagdww:kx?EQ-65D%2BvcqYV@://supabase.com'
else:
    # Tu configuración de PC local que te corre excelente
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medidores.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# INICIALIZACIÓN FORZADA CONTROLADA
db = SQLAlchemy()
db.init_app(app)

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

# RUTA DEL LOGIN
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

# RUTA PARA CERRAR SESIÓN
@app.route('/logout')
def logout():
    session.pop('logeado', None)
    return redirect(url_for('login'))

# RUTA PRINCIPAL PROTEGIDA
@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logeado'):
        return redirect(url_for('login'))
        
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
    
    historial = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).all()
    ultimo_registro = RegistroMedidor.query.order_by(RegistroMedidor.fecha.desc()).first()
    return render_template('index.html', historial=historial, ultimo=ultimo_registro)

# RUTA ELIMINAR PROTEGIDA
@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if not session.get('logeado'):
        return redirect(url_for('login'))
    registro = RegistroMedidor.query.get_or_404(id)
    db.session.delete(registro)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8080)
else:
    with app.app_context():
        db.create_all()
