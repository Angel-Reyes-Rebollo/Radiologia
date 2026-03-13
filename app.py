# ============================================================
# app.py — Fase 3: Seguridad completa
# ============================================================
# Cambios respecto a Fase 2:
#
# ✅ Login usa bcrypt.checkpw() en lugar de == directo
# ✅ Login guarda la sesión en Flask (session[])
# ✅ Ruta /logout para cerrar sesión
# ✅ Todos los endpoints de API están protegidos
# ✅ Endpoints de admin solo accesibles por admin
# ============================================================

import os
import bcrypt
from flask import Flask, request, jsonify, render_template, session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "clave-por-defecto-no-usar-en-produccion")

# ── Registrar Blueprints ─────────────────────────────────────
from routes.citas    import citas_bp
from routes.doctores import doctores_bp
from routes.admin    import admin_bp

app.register_blueprint(citas_bp)
app.register_blueprint(doctores_bp)
app.register_blueprint(admin_bp)


# ============================================================
# RUTAS DE PÁGINAS HTML
# ============================================================

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    return render_template("index.html")

@app.route("/registro")
def registro_page():
    return render_template("registro.html")

@app.route("/admin")
def admin_page():
    return render_template("admin.html")

@app.route("/informes")
def informes_page():
    return render_template("informes.html")


# ============================================================
# LOGIN — Ahora con bcrypt y sesión
# ============================================================

@app.route("/login", methods=["POST"])
def handle_login():
    try:
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        print(f"[LOGIN] Intento: usuario={username}")

        from database import get_db
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # ── Verificar administrador ──────────────────────────
        cursor.execute(
            "SELECT * FROM administradores WHERE usuario = %s", (username,)
        )
        admin = cursor.fetchone()

        if admin:
            contrasena_bd = admin["contrasena"]

            # bcrypt.checkpw() compara la contraseña ingresada
            # contra el hash guardado en la BD.
            # Nunca "desencripta" — solo verifica.
            if bcrypt.checkpw(password.encode('utf-8'), contrasena_bd.encode('utf-8')):
                cursor.close()
                db.close()

                # Guardar sesión — Flask la almacena en una
                # cookie firmada con SECRET_KEY en el navegador
                session['user_id'] = admin["Aidadmin"]
                session['tipo']    = 'admin'
                session['nombre']  = admin["nombre"]

                print(f"[LOGIN] ✅ Admin autenticado: {username}")
                return jsonify({
                    "success": True,
                    "tipo": "admin",
                    "user_id": admin["Aidadmin"],
                    "user_name": admin["nombre"],
                    "redirect": "/admin"
                })

        # ── Verificar doctor ─────────────────────────────────
        cursor.execute(
            "SELECT * FROM doctores WHERE usuario = %s", (username,)
        )
        doctor = cursor.fetchone()
        cursor.close()
        db.close()

        if doctor:
            if doctor["activo"] == 0:
                return jsonify({
                    "success": False,
                    "message": "Su cuenta está desactivada. Contacte al administrador."
                }), 401

            contrasena_bd = doctor["contrasena"]

            if bcrypt.checkpw(password.encode('utf-8'), contrasena_bd.encode('utf-8')):
                # Guardar sesión del doctor
                session['user_id'] = doctor["Diddoctor"]
                session['tipo']    = 'doctor'
                session['nombre']  = doctor["usuario"]

                print(f"[LOGIN] ✅ Doctor autenticado: {username}")
                return jsonify({
                    "success": True,
                    "tipo": "doctor",
                    "user_id": doctor["Diddoctor"],
                    "user_name": doctor["usuario"],
                    "redirect": f"/dashboard?doctor_id={doctor['Diddoctor']}"
                })

        # Credenciales incorrectas
        print(f"[LOGIN] ❌ Credenciales incorrectas: {username}")
        return jsonify({
            "success": False,
            "message": "Credenciales incorrectas"
        }), 401

    except Exception as e:
        print(f"[ERROR] Login: {e}")
        return jsonify({"success": False, "message": "Error del servidor"}), 500


# ============================================================
# LOGOUT — Cerrar sesión
# ============================================================

@app.route("/logout", methods=["POST"])
def handle_logout():
    """
    Elimina la sesión del usuario.
    Después de esto, cualquier intento de acceder a un
    endpoint protegido devolverá error 401.
    """
    nombre = session.get('nombre', 'desconocido')
    session.clear()  # borra todos los datos de sesión
    print(f"[LOGOUT] Usuario {nombre} cerró sesión")
    return jsonify({"success": True, "redirect": "/"})


# ============================================================
# REGISTRO — Sin cambios en la lógica, solo agrega bcrypt
# ============================================================

@app.route("/registrar", methods=["POST"])
def handle_registro():
    try:
        nombre_completo = (
            request.form.get("nombre", "") + " " +
            request.form.get("apellidos", "")
        ).strip()
        usuario         = request.form.get("usuario", "")
        contrasena      = request.form.get("contrasena", "")
        especialidad    = request.form.get("especialidad", "")
        email           = request.form.get("correo", "")
        telefono        = request.form.get("telefono", "")
        direccion       = request.form.get("direccion_consultorio", "")
        tel_consultorio = request.form.get("telefono_consultorio", "")

        if not all([nombre_completo, usuario, contrasena, especialidad,
                    email, telefono, direccion, tel_consultorio]):
            return jsonify({"success": False, "message": "Faltan campos obligatorios"}), 400

        from database import get_db
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT usuario COLLATE utf8mb4_unicode_ci FROM doctores WHERE usuario=%s "
            "UNION SELECT usuario COLLATE utf8mb4_unicode_ci FROM administradores WHERE usuario=%s",
            (usuario, usuario)
        )
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({"success": False, "message": "El nombre de usuario ya está en uso"}), 400

        cursor.execute(
            "SELECT email COLLATE utf8mb4_unicode_ci FROM doctores WHERE email=%s "
            "UNION SELECT email COLLATE utf8mb4_unicode_ci FROM administradores WHERE email=%s",
            (email, email)
        )
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({"success": False, "message": "El correo ya está registrado"}), 400

        cursor.execute(
            "SELECT MAX(CAST(SUBSTRING(Diddoctor, 2) AS UNSIGNED)) as max_id FROM doctores"
        )
        result   = cursor.fetchone()
        max_id   = result[0] if result[0] else 0
        nuevo_id = f"D{str(max_id + 1).zfill(3)}"

        # ⬇️ Hashear la contraseña ANTES de guardarla
        contrasena_hash = bcrypt.hashpw(
            contrasena.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        cursor.execute("""
            INSERT INTO doctores (
                Diddoctor, nombre, usuario, contrasena, especialidad,
                email, telefono, direccion_consultorio, telefono_consultorio,
                fecha_registro, activo, puntos
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),1,0)
        """, (nuevo_id, nombre_completo, usuario, contrasena_hash,
               especialidad, email, telefono, direccion, tel_consultorio))

        db.commit()
        cursor.close()
        db.close()

        return jsonify({
            "success": True,
            "message": f"Doctor registrado exitosamente. Su ID es: {nuevo_id}",
            "redirect": "/"
        })

    except Exception as e:
        print(f"[ERROR] Registro: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ============================================================
# ARRANCAR EL SERVIDOR
# ============================================================

if __name__ == "__main__":
    print("=" * 55)
    print("🚀  SISTEMA RADIOLOGÍA — Flask (Fase 3: Seguridad)")
    print("=" * 55)
    print("📊  Accede en:  http://localhost:8000")
    print("🔐  Contraseñas protegidas con bcrypt")
    print("🛡️   Endpoints protegidos con sesiones")
    print("=" * 55)

    app.run(host="0.0.0.0", port=8000, debug=True)
