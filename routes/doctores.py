# ============================================================
# routes/doctores.py — Rutas de doctores (Fase 3: protegidas)
# ============================================================
# Cambio respecto a Fase 2:
#   Rutas de lectura    → @requiere_login (doctor o admin)
#   Rutas de escritura  → @requiere_admin (solo admin)
# ============================================================

from datetime import datetime
from flask import Blueprint, jsonify, request
from database import get_db
from routes.auth import requiere_login, requiere_admin

doctores_bp = Blueprint('doctores', __name__)


@doctores_bp.route('/api/doctores', methods=['GET'])
@requiere_login
def get_doctores():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT d.Diddoctor as id, d.nombre, d.usuario, d.contrasena,
                   d.especialidad, d.email, d.telefono, d.telefono_consultorio,
                   d.direccion_consultorio,
                   DATE_FORMAT(d.fecha_registro, '%Y-%m-%d') as fecha_registro,
                   d.activo, d.puntos,
                   COUNT(c.id_cita) as total_citas,
                   COUNT(DISTINCT c.paciente) as pacientes,
                   SUM(CASE WHEN c.resultado IS NULL THEN 1 ELSE 0 END) as estudios_pendientes
            FROM doctores d
            LEFT JOIN citas c ON c.doctor_id = d.Diddoctor
            GROUP BY d.Diddoctor ORDER BY d.Diddoctor ASC
        """)
        doctores = cursor.fetchall()
        cursor.close()
        db.close()
        for d in doctores:
            d['activo'] = bool(d['activo'])
            d['total_citas'] = int(d['total_citas'] or 0)
            d['pacientes'] = int(d['pacientes'] or 0)
            d['estudios_pendientes'] = int(d['estudios_pendientes'] or 0)
        admin_entry = {
            'id': 'ADMIN', 'nombre': 'Administrador', 'usuario': 'admin',
            'contrasena': '', 'especialidad': 'Administración',
            'email': 'admin@radiologia.com', 'telefono': 'N/A',
            'telefono_consultorio': 'N/A', 'direccion_consultorio': 'N/A',
            'fecha_registro': datetime.now().strftime('%Y-%m-%d'),
            'activo': True, 'puntos': 0, 'total_citas': 0,
            'pacientes': 0, 'estudios_pendientes': 0
        }
        return jsonify([admin_entry] + doctores)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@doctores_bp.route('/api/doctor-by-user/<username>', methods=['GET'])
@requiere_login
def get_doctor_by_user(username):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT Diddoctor as id, nombre, usuario, puntos FROM doctores WHERE usuario=%s AND activo=1",
            (username,)
        )
        doctor = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify(doctor) if doctor else (jsonify({'error': 'Doctor no encontrado'}), 404)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@doctores_bp.route('/api/doctor-info/<doctor_id>', methods=['GET'])
@requiere_login
def get_doctor_info(doctor_id):
    try:
        if doctor_id == 'ADMIN':
            return jsonify({
                'id': 'ADMIN', 'nombre': 'Administrador', 'especialidad': 'Administración',
                'email': 'admin@4digital.com', 'telefono': 'N/A', 'usuario': 'admin',
                'direccion_consultorio': 'N/A', 'telefono_consultorio': 'N/A',
                'fecha_registro': datetime.now().strftime('%Y-%m-%d'), 'activo': True, 'puntos': 0
            })
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT Diddoctor as id, nombre, especialidad, email, telefono, usuario,
                   direccion_consultorio, telefono_consultorio,
                   DATE_FORMAT(fecha_registro, '%Y-%m-%d') as fecha_registro, activo, puntos
            FROM doctores WHERE Diddoctor=%s
        """, (doctor_id,))
        doctor = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify(doctor) if doctor else (jsonify({'error': 'Doctor no encontrado'}), 404)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@doctores_bp.route('/api/doctor/<doctor_id>', methods=['GET'])
@requiere_login
def get_doctor_reporte(doctor_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        if doctor_id == 'ADMIN':
            cursor.execute("""
                SELECT COUNT(*) as total_citas_completadas,
                       COALESCE(SUM(total_estudio),0) as total_facturado
                FROM citas WHERE doctor_id='ADMIN' AND resultado IS NOT NULL
            """)
            stats = cursor.fetchone()
            cursor.close()
            db.close()
            return jsonify({'id': 'ADMIN', 'nombre': 'Administrador', 'puntos': 0,
                            'total_citas_completadas': stats['total_citas_completadas'] if stats else 0,
                            'total_facturado': float(stats['total_facturado']) if stats else 0})
        cursor.execute("""
            SELECT Diddoctor as id, nombre, especialidad, email, telefono, usuario, puntos,
                   DATE_FORMAT(fecha_registro,'%Y-%m-%d') as fecha_registro
            FROM doctores WHERE Diddoctor=%s
        """, (doctor_id,))
        doctor = cursor.fetchone()
        if not doctor:
            cursor.close()
            db.close()
            return jsonify({'error': 'Doctor no encontrado'}), 404
        cursor.execute("""
            SELECT COUNT(*) as total_citas_completadas,
                   COALESCE(SUM(total_estudio),0) as total_facturado
            FROM citas WHERE doctor_id=%s AND resultado IS NOT NULL
        """, (doctor_id,))
        stats = cursor.fetchone()
        cursor.close()
        db.close()
        doctor['total_citas_completadas'] = stats['total_citas_completadas'] if stats else 0
        doctor['total_facturado'] = float(stats['total_facturado']) if stats else 0
        return jsonify(doctor)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@doctores_bp.route('/api/doctor/<doctor_id>/citas-completadas', methods=['GET'])
@requiere_login
def get_citas_completadas_doctor(doctor_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        if doctor_id != 'ADMIN':
            cursor.execute("SELECT Diddoctor FROM doctores WHERE Diddoctor=%s", (doctor_id,))
            if not cursor.fetchone():
                cursor.close()
                db.close()
                return jsonify({'error': 'Doctor no encontrado'}), 404
        cursor.execute("""
            SELECT c.id_cita, c.numero_folio, c.paciente,
                   COALESCE(d.nombre,'Administrador') as doctor_nombre,
                   COALESCE(DATE_FORMAT(c.fecha_cita,'%d/%m/%Y'),'N/A') as fecha_cita,
                   COALESCE(TIME_FORMAT(c.hora_cita,'%H:%i'),'N/A') as hora_cita,
                   CAST(COALESCE(c.total_estudio,0) AS DECIMAL(10,2)) as total_estudio,
                   COALESCE(DATE_FORMAT(c.fecha,'%d/%m/%Y'),'N/A') as fecha_registro,
                   c.documento_nombre,
                   CASE WHEN c.documento_pdf IS NOT NULL THEN 1 ELSE 0 END as tiene_pdf,
                   CASE WHEN c.resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                   c.resultado_nombre,
                   COALESCE(DATE_FORMAT(c.resultado_fecha_carga,'%d/%m/%Y %H:%i'),'N/A') as fecha_carga_resultado
            FROM citas c LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
            WHERE c.doctor_id=%s AND c.resultado IS NOT NULL AND c.fecha_eliminacion IS NULL
            ORDER BY c.fecha_cita DESC
        """, (doctor_id,))
        citas = cursor.fetchall()
        cursor.close()
        db.close()
        for cita in citas:
            cita['total_estudio'] = float(cita['total_estudio'] or 0)
            for k, v in cita.items():
                if v is None:
                    cita[k] = 'N/A'
        return jsonify(citas)
    except Exception as e:
        return jsonify({'error': str(e), 'citas': []}), 500


@doctores_bp.route('/api/resultados/<doctor_id>', methods=['GET'])
@requiere_login
def get_resultados(doctor_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Diddoctor FROM doctores WHERE Diddoctor=%s", (doctor_id,))
        if not cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify([])
        cursor.execute("""
            SELECT id_cita, numero_folio, paciente, resultado_nombre, resultado_tamano,
                   DATE_FORMAT(resultado_fecha_carga,'%d/%m/%Y %H:%i') as fecha_carga,
                   CASE WHEN resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado
            FROM citas WHERE doctor_id=%s AND resultado IS NOT NULL
            ORDER BY resultado_fecha_carga DESC
        """, (doctor_id,))
        resultados = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify(resultados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@doctores_bp.route('/api/usuarios/doctor/<doctor_id>', methods=['GET'])
@requiere_admin
def get_doctor_details(doctor_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT Diddoctor as id, nombre, usuario, contrasena, especialidad,
                   email, telefono, direccion_consultorio, telefono_consultorio,
                   DATE_FORMAT(fecha_registro,'%Y-%m-%d') as fecha_registro, activo, puntos
            FROM doctores WHERE Diddoctor=%s
        """, (doctor_id,))
        doctor = cursor.fetchone()
        if not doctor:
            cursor.close()
            db.close()
            return jsonify({'error': 'Doctor no encontrado'}), 404
        cursor.execute("""
            SELECT COUNT(*) as total_citas, COUNT(DISTINCT paciente) as total_pacientes,
                   SUM(CASE WHEN resultado IS NULL THEN 1 ELSE 0 END) as estudios_pendientes
            FROM citas WHERE doctor_id=%s
        """, (doctor_id,))
        stats = cursor.fetchone()
        cursor.close()
        db.close()
        doctor['activo'] = bool(doctor['activo'])
        doctor['total_citas'] = int(stats['total_citas'] or 0)
        doctor['total_pacientes'] = int(stats['total_pacientes'] or 0)
        doctor['estudios_pendientes'] = int(stats['estudios_pendientes'] or 0)
        return jsonify(doctor)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@doctores_bp.route('/api/create-doctor', methods=['POST'])
@requiere_admin
def create_doctor():
    try:
        import bcrypt
        data     = request.get_json()
        nombre   = data.get('nombre')
        usuario  = data.get('usuario')
        password = data.get('password')
        email    = data.get('email')
        telefono              = data.get('telefono', '')
        telefono_consultorio  = data.get('telefono_consultorio', '')
        direccion_consultorio = data.get('direccion_consultorio', '')
        especialidad          = data.get('especialidad', '')

        if not all([nombre, usuario, password, email]):
            return jsonify({'success': False, 'message': 'Faltan campos obligatorios'}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT usuario FROM doctores WHERE usuario=%s UNION SELECT usuario FROM administradores WHERE usuario=%s",
            (usuario, usuario)
        )
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Usuario ya en uso'}), 400

        cursor.execute(
            "SELECT email FROM doctores WHERE email=%s UNION SELECT email FROM administradores WHERE email=%s",
            (email, email)
        )
        if cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Correo ya registrado'}), 400

        cursor.execute("SELECT MAX(CAST(SUBSTRING(Diddoctor,2) AS UNSIGNED)) as max_id FROM doctores")
        result   = cursor.fetchone()
        nuevo_id = f"D{str((result['max_id'] or 0) + 1).zfill(3)}"

        # Hashear contraseña antes de guardar
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cursor.execute("""
            INSERT INTO doctores (Diddoctor, nombre, usuario, contrasena, especialidad,
                                  email, telefono, direccion_consultorio, telefono_consultorio,
                                  fecha_registro, activo, puntos)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),1,0)
        """, (nuevo_id, nombre, usuario, password_hash, especialidad,
               email, telefono, direccion_consultorio, telefono_consultorio))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': f'Doctor registrado. ID: {nuevo_id}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@doctores_bp.route('/api/update-user', methods=['POST'])
@requiere_admin
def update_user():
    try:
        import bcrypt
        data      = request.get_json()
        user_id   = data.get('userId')
        user_type = data.get('userType')
        if not user_id or user_type != 'doctor':
            return jsonify({'success': False, 'message': 'Datos inválidos'}), 400

        db = get_db()
        cursor = db.cursor()
        fields, valores = [], []

        for campo, key in [
            ('nombre','nombre'), ('email','email'), ('telefono','telefono'),
            ('telefono_consultorio','telefono_consultorio'),
            ('direccion_consultorio','direccion_consultorio'),
            ('especialidad','especialidad'), ('usuario','usuario'),
        ]:
            if data.get(key) is not None:
                fields.append(f"{campo}=%s")
                valores.append(data[key])

        # Solo actualizar activo si el valor es explícitamente 'active' o 'inactive'
        # Esto evita que un campo vacío o mal inicializado pise el valor real de la BD
        if data.get('estado') in ('active', 'inactive', 'activo', 'inactivo'):
            fields.append("activo=%s")
            valores.append(1 if data['estado'] in ('active', 'activo') else 0)
        if data.get('puntos') is not None:
            fields.append("puntos=%s")
            valores.append(data['puntos'])
        if data.get('password'):
            # Hashear nueva contraseña
            nuevo_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            fields.append("contrasena=%s")
            valores.append(nuevo_hash)

        if not fields:
            return jsonify({'success': False, 'message': 'Nada que actualizar'}), 400

        valores.append(user_id)
        cursor.execute(f"UPDATE doctores SET {', '.join(fields)} WHERE Diddoctor=%s", valores)
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Doctor actualizado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@doctores_bp.route('/api/delete-user', methods=['POST'])
@requiere_admin
def delete_user():
    try:
        data    = request.get_json()
        user_id = data.get('userId')
        if not user_id or data.get('userType') != 'doctor':
            return jsonify({'success': False, 'message': 'Datos inválidos'}), 400
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM doctores WHERE Diddoctor=%s", (user_id,))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Doctor eliminado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@doctores_bp.route('/api/change-doctor-password', methods=['POST'])
@requiere_admin
def change_doctor_password():
    try:
        import bcrypt
        data         = request.get_json()
        doctor_id    = data.get('doctor_id')
        new_password = data.get('new_password')
        if not doctor_id or not new_password:
            return jsonify({'success': False, 'message': 'Faltan datos'}), 400
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Mínimo 6 caracteres'}), 400
        nuevo_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE doctores SET contrasena=%s WHERE Diddoctor=%s", (nuevo_hash, doctor_id))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Contraseña actualizada'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
