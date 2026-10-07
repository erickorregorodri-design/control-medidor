import os
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime

app = Flask(__name__)

# LLAVE SECRETA: Clave para encriptar las sesiones de usuario de forma segura
app.secret_key = 'mi_llave_secreta_super_segura_medidores_2026'

# Credenciales fijas de acceso (Usuario y contraseña para tu celular)
USUARIO_CORRECTO = "admin"
CLAVE_CORRECTA = "medidor2026"

# CONEXIÓN DIRECTA NATIVA A SUPABASE (Evita por completo las validaciones ocultas de Railway)
DATABASE_URL = 'postgresql://postgres.eczhbmjltaropyzagdww:kx?EQ-65D+vcqYV@://supabase.com'

def get_db_connection():
    # Conexión pura que no valida variables de entorno ocultas
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
    return conn

# CREACIÓN AUTOMÁTICA DE LA TABLA SI NO EXISTE
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS registro_medidor (
            id SERIAL PRIMARY KEY,
            fecha DATE NOT NULL,
            lectura_p1 REAL NOT NULL,
            lectura_p2 REAL NOT NULL,
            monto_boleta REAL,
            consumo_p1 REAL DEFAULT 0.0,
            consumo_p2 REAL DEFAULT 0.0,
            porcentaje_p1 REAL DEFAULT 0.0,
            porcentaje_p2 REAL DEFAULT 0.0,
            pago_p1 REAL DEFAULT 0.0,
            pago_p2 REAL DEFAULT 0.0
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

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
        
    conn = get_db_connection()
    cur = conn.cursor()

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

        # BUSCAR EL REGISTRO ANTERIOR REAL
        cur.execute('SELECT lectura_p1, lectura_p2 FROM registro_medidor WHERE fecha < %s ORDER BY fecha DESC LIMIT 1', (fecha_objeto,))
        ultima_lectura = cur.fetchone()
        
        if ultima_lectura:
            cons_p1 = max(0.0, lectura_actual_p1 - ultima_lectura['lectura_p1'])
            cons_p2 = max(0.0, lectura_actual_p2 - ultima_lectura['lectura_p2'])
            consumo_total = cons_p1 + cons_p2
            
            if consumo_total > 0:
                pct_p1 = (cons_p1 / consumo_total) * 100
                pct_p2 = (cons_p2 / consumo_total) * 100
                pago_p1 = (pct_p1 / 100) * monto_total
                pago_p2 = (pct_p2 / 100) * monto_total

        # GUARDAR EN LA BASE DE DATOS SQL
        cur.execute('''
            INSERT INTO registro_medidor (fecha, lectura_p1, lectura_p2, monto_boleta, consumo_p1, consumo_p2, porcentaje_p1, porcentaje_p2, pago_p1, pago_p2)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (fecha_objeto, lectura_actual_p1, lectura_actual_p2, monto_total, round(cons_p1, 2), round(cons_p2, 2), round(pct_p1, 1), round(pct_p2, 1), round(pago_p1, 0), round(pago_p2, 0)))
        
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    
    # OBTENER HISTORIAL Y ÚLTIMO REGISTRO
    cur.execute('SELECT * FROM registro_medidor ORDER BY fecha DESC')
    historial = cur.fetchall()
    
    cur.execute('SELECT lectura_p1, lectura_p2 FROM registro_medidor ORDER BY fecha DESC LIMIT 1')
    ultimo_registro = cur.fetchone()
    
    cur.close()
    conn.close()
    return render_template('index.html', historial=historial, ultimo=ultimo_registro)

# RUTA: ELIMINAR REGISTROS PROTEGIDA
@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if not session.get('logeado'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM registro_medidor WHERE id = %s', (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('index'))

# Inicializar la tabla antes de arrancar
init_db()

if __name__ == '__main__':
    app.run(debug=True, port=8080)
