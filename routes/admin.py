# ============================================================
# routes/admin.py — Rutas del panel de administración
# ============================================================
# Cambio respecto a Fase 2:
#   Todas las rutas ahora tienen @requiere_admin
#   Solo el administrador logueado puede acceder a ellas.
# ============================================================

import base64
from datetime import datetime
from flask import Blueprint, jsonify, request
from database import get_db
from routes.auth import requiere_admin, requiere_login

admin_bp = Blueprint('admin', __name__)


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


# ============================================================
# GET /api/admin/stats
# @requiere_admin → solo admin puede ver las estadísticas
# ============================================================
@admin_bp.route('/api/admin/stats', methods=['GET'])
@requiere_admin
def admin_stats():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as total FROM doctores WHERE activo = 1")
        total_doctores = cursor.fetchone()['total']

        cursor.execute("SHOW COLUMNS FROM citas LIKE 'estado'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) as total FROM citas WHERE estado='activa' OR estado IS NULL")
        else:
            cursor.execute("SELECT COUNT(*) as total FROM citas")
        total_citas = cursor.fetchone()['total']

        cursor.execute("""
            SELECT COUNT(*) as total FROM doctores
            WHERE fecha_registro >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        nuevos_doctores = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE resultado IS NOT NULL")
        citas_completadas = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE resultado IS NULL")
        estudios_pendientes = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as total FROM citas WHERE fecha_eliminacion IS NOT NULL")
        citas_eliminar = cursor.fetchone()['total']

        cursor.execute("""
            SELECT DATE_FORMAT(MIN(fecha_eliminacion), '%d/%m/%Y') as proxima
            FROM citas WHERE fecha_eliminacion IS NOT NULL AND fecha_eliminacion >= CURDATE()
        """)
        proxima_eliminacion = cursor.fetchone()['proxima']

        cursor.execute("SELECT SUM(puntos) as total_puntos FROM doctores")
        total_puntos = cursor.fetchone()['total_puntos'] or 0

        cursor.close()
        db.close()

        return jsonify({
            'totalDoctores': total_doctores,
            'estudiosPendientes': estudios_pendientes,
            'nuevosDoctores': nuevos_doctores,
            'estudiosCompletados': citas_completadas,
            'totalCitas': total_citas,
            'totalPuntos': total_puntos,
            'citasAEliminar': citas_eliminar,
            'proximaEliminacion': proxima_eliminacion or '-'
        })

    except Exception as e:
        print(f"[ERROR] admin_stats: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# GET /api/admin/activity
# @requiere_admin → solo admin
# ============================================================
@admin_bp.route('/api/admin/activity', methods=['GET'])
@requiere_admin
def admin_activity():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                COALESCE(CONCAT('Dr. ', d.nombre), 'Administrador') as usuario_id,
                CASE WHEN d.nombre IS NOT NULL THEN 'doctor' ELSE 'admin' END as tipo_usuario,
                'Nueva cita' as accion,
                DATE_FORMAT(c.fecha, '%Y-%m-%d %H:%i') as fecha,
                CONCAT('Paciente: ', c.paciente, ' - Folio: ', c.numero_folio,
                       ' - Total: $', FORMAT(c.total_estudio, 2)) as detalles
            FROM citas c
            LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
            WHERE c.id_cita IS NOT NULL

            UNION ALL
            SELECT CONCAT('Dr. ', nombre), 'doctor', 'Registro',
                   DATE_FORMAT(fecha_registro, '%Y-%m-%d %H:%i'),
                   CONCAT('ID: ', Diddoctor, ' - ', COALESCE(especialidad,'Sin especialidad'), ' - Puntos: ', puntos)
            FROM doctores WHERE fecha_registro IS NOT NULL

            UNION ALL
            SELECT 'ADMIN', 'admin', 'Cancelar cita', aa.fecha, aa.detalles
            FROM actividad_admin aa WHERE aa.accion = 'CANCELAR_CITA'

            UNION ALL
            SELECT 'ADMIN', 'admin', 'Entregar resultado', aa.fecha, aa.detalles
            FROM actividad_admin aa WHERE aa.accion = 'ENTREGAR_RESULTADO'

            UNION ALL
            SELECT 'ADMIN', 'admin', 'Programar eliminación', aa.fecha, aa.detalles
            FROM actividad_admin aa WHERE aa.accion = 'PROGRAMAR_ELIMINACION'

            UNION ALL
            SELECT 'ADMIN', 'admin', 'Cancelar eliminación', aa.fecha, aa.detalles
            FROM actividad_admin aa WHERE aa.accion = 'CANCELAR_ELIMINACION'

            ORDER BY fecha DESC LIMIT 20
        """)
        actividades = cursor.fetchall()

        if not actividades:
            cursor.execute("""
                SELECT CONCAT('Dr. ', nombre) as usuario_id, 'doctor' as tipo_usuario,
                       'Registro' as accion,
                       DATE_FORMAT(fecha_registro, '%Y-%m-%d %H:%i') as fecha,
                       CONCAT('ID: ', Diddoctor, ' - ', COALESCE(especialidad,'Sin especialidad')) as detalles
                FROM doctores WHERE fecha_registro IS NOT NULL
                ORDER BY fecha_registro DESC LIMIT 10
            """)
            actividades = cursor.fetchall()

        cursor.close()
        db.close()

        if not actividades:
            actividades = [{
                'usuario_id': 'Sistema', 'tipo_usuario': 'admin',
                'accion': 'Bienvenida', 'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'detalles': 'Sistema de radiología iniciado'
            }]

        return jsonify(actividades)

    except Exception as e:
        print(f"[ERROR] admin_activity: {e}")
        return jsonify([{
            'usuario_id': 'Sistema', 'tipo_usuario': 'admin',
            'accion': 'Sistema activo', 'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'detalles': 'Sistema funcionando correctamente'
        }])


# ============================================================
# GET /api/citas-sin-resultado  @requiere_admin
# ============================================================
@admin_bp.route('/api/citas-sin-resultado', methods=['GET'])
@requiere_admin
def get_citas_sin_resultado():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.id_cita, c.numero_folio, c.paciente,
                   COALESCE(d.nombre, 'Administrador') as doctor_nombre, c.doctor_id,
                   DATE_FORMAT(c.fecha_cita, '%d/%m/%Y') as fecha_cita,
                   TIME_FORMAT(c.hora_cita, '%H:%i') as hora_cita,
                   CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                   CASE WHEN c.resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                   c.documento_nombre
            FROM citas c
            LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
            WHERE c.resultado IS NULL AND c.fecha_eliminacion IS NULL
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


# ============================================================
# GET /api/citas-eliminar  @requiere_admin
# ============================================================
@admin_bp.route('/api/citas-eliminar', methods=['GET'])
@requiere_admin
def get_citas_eliminar():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.id_cita, c.numero_folio, c.paciente,
                   COALESCE(d.nombre, 'Administrador') as doctor_nombre, c.doctor_id,
                   DATE_FORMAT(c.fecha_cita, '%d/%m/%Y') as fecha_cita,
                   TIME_FORMAT(c.hora_cita, '%H:%i') as hora_cita,
                   CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                   CASE WHEN c.resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                   DATE_FORMAT(c.fecha_eliminacion, '%d/%m/%Y') as fecha_eliminacion_formateada,
                   c.fecha_eliminacion
            FROM citas c
            LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
            WHERE c.fecha_eliminacion IS NOT NULL
            ORDER BY c.fecha_eliminacion ASC
        """)
        citas = cursor.fetchall()
        cursor.close()
        db.close()
        for cita in citas:
            cita['total_estudio'] = float(cita['total_estudio'] or 0)
        return jsonify(citas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# POST /api/entregar-resultado  @requiere_admin
# ============================================================
@admin_bp.route('/api/entregar-resultado', methods=['POST'])
@requiere_admin
def entregar_resultado():
    try:
        data             = request.get_json()
        cita_id          = data.get('cita_id')
        resultado_base64 = data.get('resultado_base64')
        resultado_nombre = data.get('resultado_nombre')
        resultado_tipo   = data.get('resultado_tipo')

        if not all([cita_id, resultado_base64, resultado_nombre, resultado_tipo]):
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400

        resultado_bytes  = base64.b64decode(resultado_base64)
        resultado_tamano = len(resultado_bytes)

        if resultado_tamano > 50 * 1024 * 1024:
            return jsonify({'success': False,
                            'message': f'Archivo demasiado grande ({resultado_tamano/1024/1024:.1f}MB). Máximo 50MB'}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT total_estudio, doctor_id, paciente, numero_folio FROM citas WHERE id_cita = %s",
            (cita_id,)
        )
        cita = cursor.fetchone()
        if not cita:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Cita no encontrada'}), 404

        total_estudio    = float(cita['total_estudio'] or 0)
        doctor_id        = cita['doctor_id']
        puntos_a_asignar = int(total_estudio / 100)

        cursor.execute("""
            UPDATE citas
            SET resultado=%s, resultado_nombre=%s, resultado_tipo=%s,
                resultado_tamano=%s, resultado_fecha_carga=NOW(), fecha_eliminacion=NULL
            WHERE id_cita=%s
        """, (resultado_bytes, resultado_nombre, resultado_tipo, resultado_tamano, cita_id))
        db.commit()

        if doctor_id != 'ADMIN' and puntos_a_asignar > 0:
            cursor.execute(
                "UPDATE doctores SET puntos = puntos + %s WHERE Diddoctor = %s",
                (puntos_a_asignar, doctor_id)
            )
            db.commit()

        cursor.close()
        db.close()

        registrar_actividad('ADMIN', 'ENTREGAR_RESULTADO',
                            f'Resultado entregado para cita {cita["numero_folio"]} - '
                            f'Paciente: {cita["paciente"]} - '
                            f'Puntos: {puntos_a_asignar} - '
                            f'Tamaño: {resultado_tamano/1024:.1f}KB')

        return jsonify({
            'success': True,
            'message': f'✅ Resultado subido. Se añadieron {puntos_a_asignar} puntos al doctor.',
            'puntos_asignados': puntos_a_asignar,
            'tamano': f"{resultado_tamano/1024:.1f}KB"
        })

    except Exception as e:
        print(f"[ERROR] entregar_resultado: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/upload-resultado', methods=['POST'])
@requiere_admin
def upload_resultado():
    return entregar_resultado()


# ============================================================
# POST /api/programar-eliminacion  @requiere_admin
# ============================================================
@admin_bp.route('/api/programar-eliminacion', methods=['POST'])
@requiere_admin
def programar_eliminacion():
    try:
        data              = request.get_json()
        cita_id           = data.get('cita_id')
        fecha_eliminacion = data.get('fecha_eliminacion')

        if not cita_id or not fecha_eliminacion:
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id_cita, numero_folio, paciente FROM citas WHERE id_cita = %s", (cita_id,))
        cita = cursor.fetchone()
        if not cita:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'La cita no existe'}), 404

        cursor.execute("UPDATE citas SET fecha_eliminacion=%s WHERE id_cita=%s", (fecha_eliminacion, cita_id))
        db.commit()
        cursor.close()
        db.close()

        registrar_actividad('ADMIN', 'PROGRAMAR_ELIMINACION',
                            f'Eliminación programada: {cita["numero_folio"]} - '
                            f'Paciente: {cita["paciente"]} - Fecha: {fecha_eliminacion}')

        return jsonify({'success': True, 'message': 'Eliminación programada', 'cita_id': cita_id})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# POST /api/cancelar-eliminacion  @requiere_admin
# ============================================================
@admin_bp.route('/api/cancelar-eliminacion', methods=['POST'])
@requiere_admin
def cancelar_eliminacion():
    try:
        data    = request.get_json()
        cita_id = data.get('cita_id')

        if not cita_id:
            return jsonify({'success': False, 'message': 'ID de cita no proporcionado'}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id_cita, numero_folio, paciente FROM citas WHERE id_cita = %s", (cita_id,))
        cita = cursor.fetchone()
        if not cita:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'La cita no existe'}), 404

        cursor.execute("UPDATE citas SET fecha_eliminacion=NULL WHERE id_cita=%s", (cita_id,))
        db.commit()
        cursor.close()
        db.close()

        registrar_actividad('ADMIN', 'CANCELAR_ELIMINACION',
                            f'Eliminación cancelada: {cita["numero_folio"]} - Paciente: {cita["paciente"]}')

        return jsonify({'success': True, 'message': 'Eliminación cancelada', 'cita_id': cita_id})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================
# POST /api/ajustar-puntos  @requiere_admin
# ============================================================
@admin_bp.route('/api/ajustar-puntos', methods=['POST'])
@requiere_admin
def ajustar_puntos():
    try:
        data          = request.get_json()
        doctor_id     = data.get('doctor_id')
        puntos_nuevos = data.get('puntos_nuevos')
        tipo_ajuste   = data.get('tipo_ajuste')
        cantidad      = data.get('cantidad')
        motivo        = data.get('motivo', 'Ajuste manual')

        if not doctor_id or puntos_nuevos is None:
            return jsonify({'success': False, 'message': 'Faltan datos requeridos'}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT Diddoctor, nombre, puntos FROM doctores WHERE Diddoctor = %s", (doctor_id,))
        doctor = cursor.fetchone()
        if not doctor:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Doctor no encontrado'}), 404

        puntos_anteriores = doctor['puntos']
        cursor.execute("UPDATE doctores SET puntos=%s WHERE Diddoctor=%s", (puntos_nuevos, doctor_id))
        db.commit()
        cursor.close()
        db.close()

        registrar_actividad('ADMIN', 'AJUSTAR_PUNTOS',
                            f'Puntos: Dr. {doctor["nombre"]} — {puntos_anteriores} → {puntos_nuevos}. Motivo: {motivo}')

        return jsonify({
            'success': True,
            'message': f'Puntos ajustados: {puntos_anteriores} → {puntos_nuevos}',
            'puntos_anteriores': puntos_anteriores,
            'puntos_nuevos': puntos_nuevos
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
