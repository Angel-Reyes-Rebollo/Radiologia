# ============================================================
# routes/citas.py — Rutas de citas (Fase 3: con protección)
# ============================================================
# Cambio respecto a Fase 2:
#   Todas las rutas tienen @requiere_login
#   Excepción: /api/consultar-folio es pública (pacientes
#   necesitan acceder sin login para ver sus resultados)
# ============================================================

import base64
from datetime import datetime
from flask import Blueprint, jsonify, request, Response
from database import get_db
from routes.auth import requiere_login

citas_bp = Blueprint('citas', __name__)


def get_file_extension(mime_type):
    extension_map = {
        'application/zip': '.zip', 'application/x-zip-compressed': '.zip',
        'application/pdf': '.pdf', 'image/jpeg': '.jpg', 'image/png': '.png',
        'image/gif': '.gif', 'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    }
    return extension_map.get(mime_type, '')


def registrar_actividad(usuario_id, accion, detalles):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actividad_admin (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id VARCHAR(50), accion VARCHAR(100),
                detalles TEXT, fecha DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "INSERT INTO actividad_admin (usuario_id, accion, detalles, fecha) VALUES (%s,%s,%s,NOW())",
            (usuario_id, accion, detalles)
        )
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"[ERROR] registrar_actividad: {e}")


# ── Todas las rutas con @requiere_login ──────────────────────

@citas_bp.route('/api/citas', methods=['GET'])
@requiere_login
def get_all_citas():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SHOW COLUMNS FROM citas LIKE 'estado'")
        tiene_estado = cursor.fetchone()

        if tiene_estado:
            cursor.execute("""
                SELECT c.id_cita, c.numero_folio, c.paciente,
                       COALESCE(d.nombre, 'Administrador') as doctor_nombre, c.doctor_id,
                       DATE_FORMAT(c.fecha, '%d/%m/%Y') as fecha,
                       TIME_FORMAT(c.hora, '%H:%i') as hora,
                       DATE_FORMAT(c.fecha_cita, '%d/%m/%Y') as fecha_cita,
                       TIME_FORMAT(c.hora_cita, '%H:%i') as hora_cita,
                       CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                       c.documento_nombre,
                       CASE WHEN c.documento_pdf IS NOT NULL THEN 1 ELSE 0 END as tiene_pdf,
                       CASE WHEN c.resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                       c.estado,
                       DATE_FORMAT(c.fecha_eliminacion, '%d/%m/%Y') as fecha_eliminacion_formateada,
                       c.fecha_eliminacion
                FROM citas c LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                WHERE (c.estado = 'activa' OR c.estado IS NULL)
                ORDER BY c.fecha_cita DESC
            """)
        else:
            cursor.execute("""
                SELECT c.id_cita, c.numero_folio, c.paciente,
                       COALESCE(d.nombre, 'Administrador') as doctor_nombre, c.doctor_id,
                       DATE_FORMAT(c.fecha, '%d/%m/%Y') as fecha,
                       TIME_FORMAT(c.hora, '%H:%i') as hora,
                       DATE_FORMAT(c.fecha_cita, '%d/%m/%Y') as fecha_cita,
                       TIME_FORMAT(c.hora_cita, '%H:%i') as hora_cita,
                       CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                       c.documento_nombre,
                       CASE WHEN c.documento_pdf IS NOT NULL THEN 1 ELSE 0 END as tiene_pdf,
                       CASE WHEN c.resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                       DATE_FORMAT(c.fecha_eliminacion, '%d/%m/%Y') as fecha_eliminacion_formateada,
                       c.fecha_eliminacion
                FROM citas c LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                ORDER BY c.fecha_cita DESC
            """)

        citas = cursor.fetchall()
        cursor.close()
        db.close()
        for cita in citas:
            cita['total_estudio'] = float(cita['total_estudio'] or 0)
        return jsonify(citas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@citas_bp.route('/api/citas/<doctor_id>', methods=['GET'])
@requiere_login
def get_citas_doctor(doctor_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Diddoctor FROM doctores WHERE Diddoctor = %s", (doctor_id,))
        if not cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify([])
        cursor.execute("""
            SELECT id_cita, numero_folio, paciente, doctor_id,
                   DATE_FORMAT(fecha_cita, '%d/%m/%Y') as fecha_cita,
                   TIME_FORMAT(hora_cita, '%H:%i') as hora_cita,
                   CAST(total_estudio AS DECIMAL(10,2)) as total_estudio,
                   documento_nombre,
                   CASE WHEN documento_pdf IS NOT NULL THEN 1 ELSE 0 END as tiene_pdf,
                   CASE WHEN resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado
            FROM citas WHERE doctor_id = %s AND fecha_eliminacion IS NULL
            ORDER BY fecha_cita DESC
        """, (doctor_id,))
        citas = cursor.fetchall()
        cursor.close()
        db.close()
        for cita in citas:
            cita['total_estudio'] = float(cita['total_estudio'] or 0)
        return jsonify(citas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@citas_bp.route('/api/cita/<int:cita_id>', methods=['GET'])
@requiere_login
def get_cita_details(cita_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SHOW COLUMNS FROM citas LIKE 'observaciones'")
        campos_obs = "c.observaciones," if cursor.fetchone() else "'' as observaciones,"
        cursor.execute(f"""
            SELECT c.id_cita, c.numero_folio, c.paciente, c.doctor_id,
                   COALESCE(d.nombre, 'Administrador') as doctor_nombre,
                   DATE_FORMAT(c.fecha_cita, '%Y-%m-%d') as fecha_cita,
                   c.hora_cita, CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                   {campos_obs} c.documento_nombre, c.fecha, c.hora
            FROM citas c LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
            WHERE c.id_cita = %s
        """, (cita_id,))
        cita = cursor.fetchone()
        cursor.close()
        db.close()
        if not cita:
            return jsonify({'error': 'Cita no encontrada'}), 404
        if cita.get('total_estudio'):
            cita['total_estudio'] = float(cita['total_estudio'])
        return jsonify(cita)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Ruta PÚBLICA — pacientes acceden sin login ───────────────
@citas_bp.route('/api/consultar-folio/<folio>', methods=['GET'])
def consultar_folio(folio):
    # ⚠️ Sin @requiere_login — los pacientes necesitan acceder
    # desde fuera del sistema para ver sus resultados
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT id_cita, numero_folio, paciente, resultado,
                   resultado_nombre, resultado_tipo,
                   CASE WHEN resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado
            FROM citas WHERE numero_folio = %s
        """, (folio,))
        cita = cursor.fetchone()
        if not cita:
            cursor.close()
            db.close()
            return jsonify({'disponible': False, 'error': 'Folio no encontrado'}), 404
        if not cita['tiene_resultado']:
            cursor.close()
            db.close()
            return jsonify({
                'disponible': False, 'error': 'resultados_no_disponibles',
                'message': 'Resultados aún no disponibles',
                'folio': folio, 'paciente': cita['paciente']
            })
        resultado_content = cita['resultado']
        filename = cita['resultado_nombre'] or f"resultado_{folio}{get_file_extension(cita['resultado_tipo'])}"
        content_type = cita['resultado_tipo'] or 'application/octet-stream'
        cursor.close()
        db.close()
        return Response(resultado_content, headers={
            'Content-Type': content_type,
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': str(len(resultado_content)),
        })
    except Exception as e:
        return jsonify({'disponible': False, 'error': str(e)}), 500


@citas_bp.route('/api/descargar-pdf/<int:cita_id>', methods=['GET'])
@requiere_login
def descargar_pdf(cita_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT documento_pdf, documento_nombre, numero_folio FROM citas WHERE id_cita=%s", (cita_id,))
        cita = cursor.fetchone()
        cursor.close()
        db.close()
        if not cita or not cita['documento_pdf']:
            return jsonify({'error': 'PDF no encontrado'}), 404
        filename = cita['documento_nombre'] or f"cita_{cita['numero_folio']}.pdf"
        return Response(cita['documento_pdf'], headers={
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': str(len(cita['documento_pdf'])),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@citas_bp.route('/api/descargar-resultado/<int:cita_id>', methods=['GET'])
@requiere_login
def descargar_resultado(cita_id):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT resultado, resultado_nombre, resultado_tipo, numero_folio
            FROM citas WHERE id_cita=%s AND resultado IS NOT NULL
        """, (cita_id,))
        cita = cursor.fetchone()
        cursor.close()
        db.close()
        if not cita or not cita['resultado']:
            return jsonify({'error': 'Resultado no encontrado'}), 404
        filename = cita['resultado_nombre'] or f"resultado_{cita['numero_folio']}{get_file_extension(cita['resultado_tipo'])}"
        return Response(cita['resultado'], headers={
            'Content-Type': cita['resultado_tipo'] or 'application/octet-stream',
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': str(len(cita['resultado'])),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@citas_bp.route('/api/generate-cita', methods=['POST'])
@requiere_login
def generate_cita():
    try:
        data = request.get_json()
        paciente                  = data.get('paciente')
        paciente_edad             = data.get('pacienteEdad', '')
        paciente_fecha_nacimiento = data.get('pacienteFechaNacimiento', '')
        paciente_tel              = data.get('pacienteTel', '')
        paciente_email            = data.get('pacienteEmail', '')
        doctor_id                 = data.get('doctor_id')
        fecha_cita                = data.get('fecha_cita')
        hora_cita                 = data.get('hora_cita')
        estudios                  = data.get('estudios', [])
        total_estudio             = float(data.get('total_estudio', data.get('total', 0)))
        observaciones             = data.get('observaciones', '')
        formato_entrega           = data.get('formato_entrega', 'Digital')
        formato_entrega_fotografias = data.get('formato_entrega_fotografias')

        if not paciente or not doctor_id or not fecha_cita or not hora_cita:
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)

        doctor_nombre = "Administrador"
        if doctor_id != 'ADMIN':
            cursor.execute("SELECT Diddoctor, nombre FROM doctores WHERE Diddoctor = %s", (doctor_id,))
            doctor = cursor.fetchone()
            if not doctor:
                cursor.close()
                db.close()
                return jsonify({'success': False, 'message': f'Doctor {doctor_id} no existe'}), 400
            doctor_nombre = doctor['nombre']

        cursor.execute("SELECT COUNT(*) as total FROM citas")
        total_citas  = cursor.fetchone()['total'] + 1
        numero_folio = f"FOL-{datetime.now().strftime('%Y%m%d')}-{str(total_citas).zfill(5)}"
        fecha_registro = datetime.now().strftime('%Y-%m-%d')
        hora_registro  = datetime.now().strftime('%H:%M:%S')
        fecha_cita_fmt = datetime.strptime(fecha_cita, '%Y-%m-%d').strftime('%d/%m/%Y')
        fecha_nac_fmt  = datetime.strptime(paciente_fecha_nacimiento, '%Y-%m-%d').strftime('%d/%m/%Y') if paciente_fecha_nacimiento else ''

        from routes.pdf_generator import generate_pdf_cita
        pdf_content = generate_pdf_cita({
            'numero_folio': numero_folio, 'fecha_registro': fecha_registro,
            'hora_registro': hora_registro, 'fecha_cita': fecha_cita_fmt,
            'hora_cita': hora_cita, 'paciente': paciente,
            'paciente_edad': paciente_edad, 'paciente_fecha_nacimiento': fecha_nac_fmt,
            'pacienteTel': paciente_tel, 'pacienteEmail': paciente_email,
            'doctor_id': doctor_id, 'doctor_nombre': doctor_nombre,
            'estudios': estudios, 'observaciones': observaciones,
            'total': total_estudio, 'formato_entrega': formato_entrega,
            'formato_entrega_fotografias': formato_entrega_fotografias,
            'recepcionista': 'Administrador' if doctor_id == 'ADMIN' else 'Sistema',
        })
        pdf_size = len(pdf_content)

        cursor.execute("SHOW COLUMNS FROM citas LIKE 'observaciones'")
        tiene_obs = cursor.fetchone() is not None

        campos = "numero_folio, paciente, doctor_id, fecha, hora, fecha_cita, hora_cita, total_estudio, documento_nombre, documento_pdf, documento_tamano, documento_tipo"
        valores = [numero_folio, paciente, doctor_id, fecha_registro, hora_registro,
                   fecha_cita, hora_cita, total_estudio,
                   f"{paciente}_{numero_folio}.pdf".replace(' ', '_'),
                   pdf_content, pdf_size, 'application/pdf']

        if tiene_obs:
            campos = campos.replace("total_estudio,", "total_estudio, observaciones,")
            valores.insert(8, observaciones)

        placeholders = ', '.join(['%s'] * len(valores))
        cursor.execute(f"INSERT INTO citas ({campos}) VALUES ({placeholders})", valores)
        db.commit()

        cursor.execute("SELECT LAST_INSERT_ID() as id")
        cita_id = cursor.fetchone()['id']
        cursor.close()
        db.close()

        return jsonify({
            'success': True, 'message': 'Cita generada exitosamente',
            'cita_id': cita_id, 'numero_folio': numero_folio,
            'fecha': fecha_registro, 'hora': hora_registro,
            'pdf_base64': base64.b64encode(pdf_content).decode('utf-8')
        })

    except Exception as e:
        print(f"[ERROR] generate_cita: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@citas_bp.route('/api/update-cita', methods=['POST'])
@requiere_login
def update_cita():
    try:
        data          = request.get_json()
        cita_id       = data.get('cita_id')
        paciente      = data.get('paciente')
        doctor_id     = data.get('doctor_id')
        fecha_cita    = data.get('fecha_cita')
        hora_cita     = data.get('hora_cita')
        total_estudio = float(data.get('total_estudio', 0))
        observaciones = data.get('observaciones', '')

        if not all([cita_id, paciente, doctor_id, fecha_cita, hora_cita]):
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SHOW COLUMNS FROM citas LIKE 'observaciones'")
        if cursor.fetchone():
            cursor.execute("""
                UPDATE citas SET paciente=%s, doctor_id=%s, fecha_cita=%s,
                hora_cita=%s, total_estudio=%s, observaciones=%s WHERE id_cita=%s
            """, (paciente, doctor_id, fecha_cita, hora_cita, total_estudio, observaciones, cita_id))
        else:
            cursor.execute("""
                UPDATE citas SET paciente=%s, doctor_id=%s, fecha_cita=%s,
                hora_cita=%s, total_estudio=%s WHERE id_cita=%s
            """, (paciente, doctor_id, fecha_cita, hora_cita, total_estudio, cita_id))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Cita actualizada', 'cita_id': cita_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@citas_bp.route('/api/update-cita-fecha-hora', methods=['POST'])
@requiere_login
def update_cita_fecha_hora():
    try:
        data       = request.get_json()
        cita_id    = data.get('cita_id')
        fecha_cita = data.get('fecha_cita')
        hora_cita  = data.get('hora_cita')
        if not all([cita_id, fecha_cita, hora_cita]):
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE citas SET fecha_cita=%s, hora_cita=%s WHERE id_cita=%s",
                       (fecha_cita, hora_cita, cita_id))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Fecha y hora actualizadas', 'cita_id': cita_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@citas_bp.route('/api/cancelar-cita', methods=['POST'])
@requiere_login
def cancelar_cita():
    try:
        data    = request.get_json()
        cita_id = data.get('cita_id')
        if not cita_id:
            return jsonify({'success': False, 'message': 'ID de cita no proporcionado'}), 400
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id_cita, numero_folio, paciente FROM citas WHERE id_cita=%s", (cita_id,))
        cita = cursor.fetchone()
        if not cita:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'La cita no existe'}), 404
        cursor.execute("SHOW COLUMNS FROM citas LIKE 'estado'")
        if cursor.fetchone():
            cursor.execute("UPDATE citas SET estado='cancelada', fecha_cancelacion=NOW() WHERE id_cita=%s", (cita_id,))
        else:
            cursor.execute("DELETE FROM citas WHERE id_cita=%s", (cita_id,))
        db.commit()
        cursor.close()
        db.close()
        registrar_actividad('ADMIN', 'CANCELAR_CITA',
                            f'Cita cancelada: {cita["numero_folio"]} - Paciente: {cita["paciente"]}')
        return jsonify({'success': True, 'message': 'Cita cancelada', 'cita_id': cita_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
