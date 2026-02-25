# app.py - VERSIÓN COMPLETA CON GESTIÓN DE RESULTADOS, ELIMINACIÓN PROGRAMADA, PDF MEJORADO Y CONSULTA PÚBLICA DE RESULTADOS
import base64
import io
import json
import os
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import mysql.connector
from mysql.connector import Error
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)


class CustomJSONEncoder(json.JSONEncoder):
    """Encoder JSON personalizado para manejar tipos especiales"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.strftime('%H:%M:%S')
        elif isinstance(obj, timedelta):
            return str(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        return super().default(obj)


class CustomHandler(SimpleHTTPRequestHandler):
    
    def translate_path(self, path):
        # Redirigir todas las peticiones a la carpeta templates
        path = urlparse(path).path
        
        if path == '/':
            return os.path.join(os.getcwd(), 'templates', 'login.html')
        elif path == '/dashboard':
            return os.path.join(os.getcwd(), 'templates', 'index.html')
        elif path == '/registro':
            return os.path.join(os.getcwd(), 'templates', 'registro.html')
        elif path == '/admin':
            return os.path.join(os.getcwd(), 'templates', 'admin.html')
        elif path == '/RecetaV':
            return os.path.join(os.getcwd(), 'templates', 'RecetaV.html')
        elif path.endswith('.html'):
            filename = os.path.basename(path)
            return os.path.join(os.getcwd(), 'templates', filename)
        elif path.endswith('.jpg') or path.endswith('.png') or path.endswith('.jpeg'):
            return os.path.join(os.getcwd(), path.lstrip('/'))
        
        return os.path.join(os.getcwd(), path.lstrip('/'))
    
    def do_GET(self):
        """Manejar peticiones GET"""
        try:
            if self.path == '/favicon.ico':
                self.send_error(404)
                return
        
            print(f"[API GET] {self.path}")
        
            # ==============================================
            # NUEVA RUTA: CONSULTAR FOLIO PARA DESCARGAR RESULTADOS
            # ==============================================
            if self.path.startswith('/api/consultar-folio/'):
                folio = self.path.split('/')[-1]
                self.handle_consultar_folio(folio)
                return
        
            # RUTA PARA OBTENER DOCTOR POR USUARIO
            if self.path.startswith('/api/doctor-by-user/'):
                username = self.path.split('/')[-1]
                self.handle_get_doctor_by_user(username)
                return
        
            # RUTAS PARA ESTADÍSTICAS DEL DOCTOR
            if self.path.startswith('/api/doctor-info/'):
                doctor_id = self.path.split('/')[-1]
                self.handle_get_doctor_info(doctor_id)
                return
            
            if self.path == '/api/doctores':
                self.handle_get_doctores()
                return
            
            # RUTA PARA OBTENER CITAS DEL DOCTOR
            if self.path.startswith('/api/citas/'):
                doctor_id = self.path.split('/')[-1]
                self.handle_get_citas(doctor_id)
                return
            
            # RUTA PARA OBTENER RESULTADOS DEL DOCTOR
            if self.path.startswith('/api/resultados/'):
                doctor_id = self.path.split('/')[-1]
                self.handle_get_resultados(doctor_id)
                return
            
            # RUTAS PARA ADMIN
            if self.path == '/api/admin/stats':
                self.handle_admin_stats()
                return
            if self.path == '/api/admin/activity':
                self.handle_admin_activity()
                return
            
            # RUTA PARA OBTENER DETALLES DE UN DOCTOR ESPECÍFICO
            if self.path.startswith('/api/usuarios/doctor/'):
                doctor_id = self.path.split('/')[-1]
                self.handle_get_doctor_details(doctor_id)
                return
            
            # RUTA PARA OBTENER CITAS (TODAS)
            if self.path == '/api/citas':
                self.handle_get_all_citas()
                return
            
            # RUTA: CITAS A ELIMINAR
            if self.path == '/api/citas-eliminar':
                self.handle_get_citas_eliminar()
                return
            
            # RUTA: CITAS SIN RESULTADO PARA GESTIÓN DE RESULTADOS
            if self.path == '/api/citas-sin-resultado':
                self.handle_get_citas_sin_resultado()
                return
                
            # RUTA PARA OBTENER DETALLES DE UNA CITA ESPECÍFICA
            if self.path.startswith('/api/cita/'):
                cita_id = self.path.split('/')[-1]
                print(f"[API] Solicitando detalles de cita ID: {cita_id}")
                self.handle_get_cita_details(cita_id)
                return
                
            # RUTA PARA DESCARGAR PDF DE CITA
            if self.path.startswith('/api/descargar-pdf/'):
                cita_id = self.path.split('/')[-1]
                self.handle_descargar_pdf(cita_id)
                return
            
            # RUTA PARA DESCARGAR RESULTADO
            if self.path.startswith('/api/descargar-resultado/'):
                cita_id = self.path.split('/')[-1]
                self.handle_descargar_resultado(cita_id)
                return
            
            # Servir archivos estáticos (imágenes, etc.)
            if self.path.endswith('.jpg') or self.path.endswith('.png') or self.path.endswith('.jpeg'):
                file_path = self.translate_path(self.path)
                if os.path.exists(file_path):
                    self.send_response(200)
                    if self.path.endswith('.jpg') or self.path.endswith('.jpeg'):
                        self.send_header('Content-type', 'image/jpeg')
                    elif self.path.endswith('.png'):
                        self.send_header('Content-type', 'image/png')
                    self.end_headers()
                    with open(file_path, 'rb') as f:
                        self.wfile.write(f.read())
                    return
            
            super().do_GET()
            
        except Exception as e:
            print(f"Error en GET {self.path}: {str(e)}")
            self.send_error(500, f"Error interno: {str(e)}")
    
    def do_POST(self):
        """Manejar login, registro y cambio de contraseña"""
        print(f"[API POST] {self.path}")
        
        if self.path == '/login':
            self.handle_login()
        elif self.path == '/registrar':
            self.handle_registro()
        elif self.path == '/api/change-doctor-password':
            self.handle_change_doctor_password()
        elif self.path == '/api/update-user':
            self.handle_update_user()
        elif self.path == '/api/delete-user':
            self.handle_delete_user()
        elif self.path == '/api/create-doctor':
            self.handle_create_doctor()
        elif self.path == '/api/generate-cita':
            self.handle_generate_cita()
        elif self.path == '/api/upload-resultado':
            self.handle_upload_resultado()
        elif self.path == '/api/update-cita':
            self.handle_update_cita()
        elif self.path == '/api/update-cita-fecha-hora':
            self.handle_update_cita_fecha_hora()
        elif self.path == '/api/cancelar-cita':
            self.handle_cancelar_cita()
        elif self.path == '/api/entregar-resultado':
            self.handle_entregar_resultado()
        elif self.path == '/api/programar-eliminacion':
            self.handle_programar_eliminacion()
        elif self.path == '/api/cancelar-eliminacion':
            self.handle_cancelar_eliminacion()
        else:
            self.send_error(404)
    
    def send_json_response(self, data, status=200):
        """Enviar respuesta JSON con encoder personalizado"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, cls=CustomJSONEncoder).encode())
    
    # ==============================================
    # NUEVA FUNCIÓN: CONSULTAR Y DESCARGAR RESULTADOS POR FOLIO
    # ==============================================
    
    def handle_consultar_folio(self, folio):
        """Consultar y descargar resultados por número de folio (acceso público)"""
        try:
            print(f"[API] Consultando folio público: {folio}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Buscar la cita por número de folio
            cursor.execute("""
                SELECT 
                    id_cita,
                    numero_folio,
                    paciente,
                    resultado,
                    resultado_nombre,
                    resultado_tipo,
                    resultado_tamano,
                    CASE WHEN resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado
                FROM citas 
                WHERE numero_folio = %s
            """, (folio,))
            
            cita = cursor.fetchone()
            
            if not cita:
                cursor.close()
                db.close()
                # Folio no encontrado
                self.send_json_response({
                    'disponible': False,
                    'error': 'Folio no encontrado',
                    'message': 'El folio ingresado no existe en el sistema'
                }, 404)
                return
            
            if not cita['tiene_resultado'] or not cita['resultado']:
                cursor.close()
                db.close()
                # Folio encontrado pero sin resultados
                self.send_json_response({
                    'disponible': False,
                    'error': 'resultados_no_disponibles',
                    'message': 'Resultados aún no disponibles',
                    'folio': folio,
                    'paciente': cita['paciente']
                }, 200)  # Usamos 200 para poder diferenciar del error 404
                return
            
            # Tiene resultado - proceder con la descarga
            resultado_content = cita['resultado']
            filename = cita['resultado_nombre'] or f"resultado_{cita['numero_folio']}{self.get_file_extension(cita['resultado_tipo'])}"
            content_type = cita['resultado_tipo'] or 'application/octet-stream'
            
            print(f"[API] Enviando resultado para folio {folio}: {filename}, tipo: {content_type}, tamaño: {len(resultado_content)} bytes")
            
            cursor.close()
            db.close()
            
            # Enviar el archivo
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(resultado_content)))
            self.send_header('Content-Transfer-Encoding', 'binary')
            self.end_headers()
            
            # Enviar en chunks para archivos grandes
            chunk_size = 8192
            for i in range(0, len(resultado_content), chunk_size):
                self.wfile.write(resultado_content[i:i+chunk_size])
            
        except mysql.connector.Error as e:
            print(f"Error MySQL consultando folio: {str(e)}")
            self.send_json_response({
                'disponible': False,
                'error': 'Error de base de datos',
                'message': f'Error al consultar el folio: {str(e)}'
            }, 500)
        except Exception as e:
            print(f"Error general consultando folio: {str(e)}")
            self.send_json_response({
                'disponible': False,
                'error': 'Error del servidor',
                'message': f'Error del servidor: {str(e)}'
            }, 500)
    
    # ==============================================
    # FUNCIONES: ELIMINACIÓN PROGRAMADA
    # ==============================================
    
    def handle_get_citas_eliminar(self):
        """Obtener todas las citas programadas para eliminar"""
        try:
            print(f"[API] Obteniendo citas programadas para eliminar")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Verificar si existe la columna fecha_eliminacion
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'fecha_eliminacion'")
            if not cursor.fetchone():
                # Si no existe, crear la columna
                cursor.execute("ALTER TABLE citas ADD COLUMN fecha_eliminacion DATE NULL")
                db.commit()
                print("[API] Columna fecha_eliminacion creada exitosamente")
            
            cursor.execute("""
                SELECT 
                    c.id_cita,
                    c.numero_folio,
                    c.paciente,
                    COALESCE(d.nombre, 'Administrador') as doctor_nombre,
                    c.doctor_id,
                    DATE_FORMAT(c.fecha_cita, '%d/%m/%Y') as fecha_cita,
                    TIME_FORMAT(c.hora_cita, '%H:%i') as hora_cita,
                    CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                    CASE WHEN c.resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                    DATE_FORMAT(c.fecha_eliminacion, '%d/%m/%Y') as fecha_eliminacion_formateada,
                    c.fecha_eliminacion
                FROM citas c
                LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                WHERE c.fecha_eliminacion IS NOT NULL
                ORDER BY c.fecha_eliminacion ASC, c.fecha_cita DESC
            """)
            
            citas = cursor.fetchall()
            print(f"[API] Se encontraron {len(citas)} citas programadas para eliminar")
            
            # Convertir total_estudio a float
            for cita in citas:
                if cita['total_estudio'] is None:
                    cita['total_estudio'] = 0.00
                else:
                    cita['total_estudio'] = float(cita['total_estudio'])
            
            cursor.close()
            db.close()
            
            self.send_json_response(citas, 200)
            
        except Exception as e:
            print(f"Error obteniendo citas a eliminar: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    def handle_programar_eliminacion(self):
        """Programar una fecha de eliminación para una cita"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('cita_id')
            fecha_eliminacion = data.get('fecha_eliminacion')
            
            if not cita_id or not fecha_eliminacion:
                raise ValueError("Faltan datos requeridos")
            
            print(f"[ELIMINACION] Programando eliminación para cita ID: {cita_id}, fecha: {fecha_eliminacion}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Verificar que la cita existe
            cursor.execute("""
                SELECT id_cita, numero_folio, paciente, doctor_id
                FROM citas 
                WHERE id_cita = %s
            """, (cita_id,))
            
            cita = cursor.fetchone()
            
            if not cita:
                cursor.close()
                db.close()
                response = {
                    'success': False,
                    'message': 'La cita no existe'
                }
                self.send_json_response(response, 404)
                return
            
            # Verificar si existe la columna fecha_eliminacion
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'fecha_eliminacion'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE citas ADD COLUMN fecha_eliminacion DATE NULL")
                db.commit()
                print("[API] Columna fecha_eliminacion creada durante la operación")
            
            # Actualizar la cita con la fecha de eliminación
            cursor.execute("""
                UPDATE citas 
                SET fecha_eliminacion = %s
                WHERE id_cita = %s
            """, (fecha_eliminacion, cita_id))
            
            db.commit()
            
            # Registrar en log de actividad
            self.registrar_actividad_admin(
                usuario_id='ADMIN',
                accion='PROGRAMAR_ELIMINACION',
                detalles=f'Eliminación programada para cita {cita["numero_folio"]} - Paciente: {cita["paciente"]} - Fecha: {fecha_eliminacion}'
            )
            
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Eliminación programada exitosamente',
                'cita_id': cita_id,
                'fecha_eliminacion': fecha_eliminacion
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error programando eliminación: {str(e)}")
            response = {
                'success': False,
                'message': f'Error del servidor: {str(e)}'
            }
            self.send_json_response(response, 500)
    
    def handle_cancelar_eliminacion(self):
        """Cancelar la eliminación programada de una cita"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('cita_id')
            
            if not cita_id:
                raise ValueError("ID de cita no proporcionado")
            
            print(f"[ELIMINACION] Cancelando eliminación para cita ID: {cita_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Verificar que la cita existe
            cursor.execute("""
                SELECT id_cita, numero_folio, paciente, doctor_id
                FROM citas 
                WHERE id_cita = %s
            """, (cita_id,))
            
            cita = cursor.fetchone()
            
            if not cita:
                cursor.close()
                db.close()
                response = {
                    'success': False,
                    'message': 'La cita no existe'
                }
                self.send_json_response(response, 404)
                return
            
            # Eliminar la fecha de eliminación
            cursor.execute("""
                UPDATE citas 
                SET fecha_eliminacion = NULL
                WHERE id_cita = %s
            """, (cita_id,))
            
            db.commit()
            
            # Registrar en log de actividad
            self.registrar_actividad_admin(
                usuario_id='ADMIN',
                accion='CANCELAR_ELIMINACION',
                detalles=f'Eliminación cancelada para cita {cita["numero_folio"]} - Paciente: {cita["paciente"]}'
            )
            
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Eliminación cancelada exitosamente',
                'cita_id': cita_id
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error cancelando eliminación: {str(e)}")
            response = {
                'success': False,
                'message': f'Error del servidor: {str(e)}'
            }
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIÓN PARA OBTENER CITAS SIN RESULTADO
    # ==============================================
    
    def handle_get_citas_sin_resultado(self):
        """Obtener todas las citas que aún no tienen resultado cargado"""
        try:
            print(f"[API] Obteniendo citas sin resultado")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    c.id_cita,
                    c.numero_folio,
                    c.paciente,
                    COALESCE(d.nombre, 'Administrador') as doctor_nombre,
                    c.doctor_id,
                    DATE_FORMAT(c.fecha_cita, '%d/%m/%Y') as fecha_cita,
                    TIME_FORMAT(c.hora_cita, '%H:%i') as hora_cita,
                    CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                    CASE WHEN c.resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                    c.documento_nombre
                FROM citas c
                LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                WHERE c.resultado IS NULL AND c.fecha_eliminacion IS NULL
                ORDER BY c.fecha_cita DESC, c.hora_cita DESC
            """)
            
            citas = cursor.fetchall()
            print(f"[API] Se encontraron {len(citas)} citas sin resultado")
            
            # Convertir total_estudio a float
            for cita in citas:
                if cita['total_estudio'] is None:
                    cita['total_estudio'] = 0.00
                else:
                    cita['total_estudio'] = float(cita['total_estudio'])
            
            cursor.close()
            db.close()
            
            self.send_json_response(citas, 200)
            
        except Exception as e:
            print(f"Error obteniendo citas sin resultado: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    # ==============================================
    # FUNCIÓN MEJORADA: ENTREGAR RESULTADO
    # ==============================================

    def handle_entregar_resultado(self):
        """Subir resultado y asignar puntos al doctor basado en el total del estudio"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('cita_id')
            resultado_base64 = data.get('resultado_base64')
            resultado_nombre = data.get('resultado_nombre')
            resultado_tipo = data.get('resultado_tipo')
            
            if not all([cita_id, resultado_base64, resultado_nombre, resultado_tipo]):
                raise ValueError("Faltan datos requeridos para subir el resultado")
            
            # Decodificar el archivo base64
            resultado_pdf = base64.b64decode(resultado_base64)
            resultado_tamano = len(resultado_pdf)
            
            # Verificar tamaño (máximo 50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if resultado_tamano > max_size:
                raise ValueError(f"El archivo es demasiado grande ({resultado_tamano/1024/1024:.1f}MB). Máximo 50MB")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Obtener el total_estudio de la cita para calcular puntos
            cursor.execute("""
                SELECT total_estudio, doctor_id, paciente, numero_folio
                FROM citas 
                WHERE id_cita = %s
            """, (cita_id,))
            
            cita = cursor.fetchone()
            
            if not cita:
                raise ValueError("Cita no encontrada")
            
            total_estudio = float(cita['total_estudio'] or 0)
            doctor_id = cita['doctor_id']
            
            # Calcular puntos: 1 punto por cada 100 pesos
            puntos_a_asignar = int(total_estudio / 100)
            
            # Verificar si existe la columna fecha_eliminacion
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'fecha_eliminacion'")
            tiene_fecha_eliminacion = cursor.fetchone() is not None
            
            # Actualizar la cita con el resultado
            if tiene_fecha_eliminacion:
                cursor.execute("""
                    UPDATE citas 
                    SET resultado = %s,
                        resultado_nombre = %s,
                        resultado_tipo = %s,
                        resultado_tamano = %s,
                        resultado_fecha_carga = NOW(),
                        fecha_eliminacion = NULL
                    WHERE id_cita = %s
                """, (resultado_pdf, resultado_nombre, resultado_tipo, resultado_tamano, cita_id))
            else:
                cursor.execute("""
                    UPDATE citas 
                    SET resultado = %s,
                        resultado_nombre = %s,
                        resultado_tipo = %s,
                        resultado_tamano = %s,
                        resultado_fecha_carga = NOW()
                    WHERE id_cita = %s
                """, (resultado_pdf, resultado_nombre, resultado_tipo, resultado_tamano, cita_id))
            
            db.commit()
            
            # Asignar puntos al doctor (solo si no es ADMIN)
            if doctor_id != 'ADMIN' and puntos_a_asignar > 0:
                cursor.execute("""
                    UPDATE doctores 
                    SET puntos = puntos + %s 
                    WHERE Diddoctor = %s
                """, (puntos_a_asignar, doctor_id))
                db.commit()
                print(f"[PUNTOS] Doctor {doctor_id} ganó {puntos_a_asignar} puntos por cita {cita_id} (Total: ${total_estudio})")
            
            # Registrar en log de actividad
            self.registrar_actividad_admin(
                usuario_id='ADMIN',
                accion='ENTREGAR_RESULTADO',
                detalles=f'Resultado entregado para cita {cita["numero_folio"]} - Paciente: {cita["paciente"]} - Puntos asignados: {puntos_a_asignar} - Tamaño: {resultado_tamano/1024:.1f}KB'
            )
            
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': f'✅ Resultado subido exitosamente. Se han añadido {puntos_a_asignar} puntos al doctor.',
                'puntos_asignados': puntos_a_asignar,
                'tamano': f"{resultado_tamano/1024:.1f}KB"
            }
            
            self.send_json_response(response, 200)
            
        except ValueError as e:
            print(f"Error de validación: {str(e)}")
            response = {'success': False, 'message': str(e)}
            self.send_json_response(response, 400)
        except mysql.connector.Error as e:
            print(f"Error MySQL: {str(e)}")
            if e.errno == 2013:
                response = {'success': False, 'message': 'Error: El archivo es demasiado grande para la base de datos.'}
            else:
                response = {'success': False, 'message': f'Error de base de datos: {str(e)}'}
            self.send_json_response(response, 500)
        except Exception as e:
            print(f"Error entregando resultado: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_json_response(response, 500)

    # ==============================================
    # FUNCIÓN: CANCELAR/ELIMINAR CITA
    # ==============================================
    
    def handle_cancelar_cita(self):
        """Cancelar/eliminar una cita"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('cita_id')
            
            if not cita_id:
                raise ValueError("ID de cita no proporcionado")
            
            print(f"[CANCELAR] Intentando cancelar cita ID: {cita_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Verificar si la cita existe y obtener datos para el log
            cursor.execute("""
                SELECT id_cita, numero_folio, paciente, doctor_id
                FROM citas 
                WHERE id_cita = %s
            """, (cita_id,))
            
            cita = cursor.fetchone()
            
            if not cita:
                cursor.close()
                db.close()
                response = {
                    'success': False,
                    'message': 'La cita no existe'
                }
                self.send_json_response(response, 404)
                return
            
            folio = cita['numero_folio']
            paciente = cita['paciente']
            doctor_id = cita['doctor_id']
            
            # Verificar si existe la columna estado
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'estado'")
            tiene_columna_estado = cursor.fetchone()
            
            if tiene_columna_estado:
                cursor.execute("""
                    UPDATE citas 
                    SET estado = 'cancelada',
                        fecha_cancelacion = NOW()
                    WHERE id_cita = %s
                """, (cita_id,))
                print(f"[CANCELAR] Cita marcada como cancelada")
            else:
                cursor.execute("DELETE FROM citas WHERE id_cita = %s", (cita_id,))
                print(f"[CANCELAR] Cita eliminada permanentemente")
            
            db.commit()
            
            # Registrar en log de actividad
            self.registrar_actividad_admin(
                usuario_id='ADMIN',
                accion='CANCELAR_CITA',
                detalles=f'Cita cancelada: {folio} - Paciente: {paciente}'
            )
            
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Cita cancelada exitosamente',
                'cita_id': cita_id,
                'folio': folio,
                'paciente': paciente
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error cancelando cita: {str(e)}")
            response = {
                'success': False,
                'message': f'Error del servidor: {str(e)}'
            }
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIÓN AUXILIAR: REGISTRAR ACTIVIDAD ADMIN
    # ==============================================
    
    def registrar_actividad_admin(self, usuario_id, accion, detalles):
        """Registra actividad en el log para el panel de administración"""
        try:
            db = self.connect_db()
            cursor = db.cursor()
            
            # Verificar si existe la tabla actividad_admin
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS actividad_admin (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    usuario_id VARCHAR(50),
                    accion VARCHAR(100),
                    detalles TEXT,
                    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO actividad_admin (usuario_id, accion, detalles, fecha)
                VALUES (%s, %s, %s, NOW())
            """, (usuario_id, accion, detalles))
            
            db.commit()
            cursor.close()
            db.close()
            print(f"[ACTIVIDAD] Registrada: {accion} - {detalles}")
            
        except Exception as e:
            print(f"Error registrando actividad: {str(e)}")
    
    # ==============================================
    # FUNCIÓN PARA ACTUALIZAR SOLO FECHA Y HORA DE LA CITA
    # ==============================================
    
    def handle_update_cita_fecha_hora(self):
        """Actualizar solo la fecha y hora de una cita existente"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('cita_id')
            fecha_cita = data.get('fecha_cita')
            hora_cita = data.get('hora_cita')
            
            if not cita_id or not fecha_cita or not hora_cita:
                raise ValueError("Faltan datos requeridos para actualizar la cita")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("""
                UPDATE citas 
                SET fecha_cita = %s,
                    hora_cita = %s
                WHERE id_cita = %s
            """, (fecha_cita, hora_cita, cita_id))
            
            db.commit()
            print(f"[CITA] Fecha/hora de cita ID {cita_id} actualizada exitosamente")
            
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Fecha y hora de la cita actualizadas exitosamente',
                'cita_id': cita_id
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error actualizando fecha/hora de cita: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIÓN PARA OBTENER DETALLES DE UNA CITA ESPECÍFICA
    # ==============================================
    
    def handle_get_cita_details(self, cita_id):
        """Obtener todos los detalles de una cita específica para edición"""
        try:
            print(f"[API] Obteniendo detalles de cita ID: {cita_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("SELECT id_cita FROM citas WHERE id_cita = %s", (cita_id,))
            if not cursor.fetchone():
                cursor.close()
                db.close()
                self.send_json_response({'error': 'Cita no encontrada'}, 404)
                return
            
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'observaciones'")
            tiene_observaciones = cursor.fetchone() is not None
            
            if tiene_observaciones:
                cursor.execute("""
                    SELECT 
                        c.id_cita,
                        c.numero_folio,
                        c.paciente,
                        c.doctor_id,
                        COALESCE(d.nombre, 'Administrador') as doctor_nombre,
                        DATE_FORMAT(c.fecha_cita, '%Y-%m-%d') as fecha_cita,
                        c.hora_cita,
                        CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                        c.observaciones,
                        c.documento_pdf,
                        c.documento_nombre,
                        c.fecha,
                        c.hora
                    FROM citas c
                    LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                    WHERE c.id_cita = %s
                """, (cita_id,))
            else:
                cursor.execute("""
                    SELECT 
                        c.id_cita,
                        c.numero_folio,
                        c.paciente,
                        c.doctor_id,
                        COALESCE(d.nombre, 'Administrador') as doctor_nombre,
                        DATE_FORMAT(c.fecha_cita, '%Y-%m-%d') as fecha_cita,
                        c.hora_cita,
                        CAST(c.total_estudio AS DECIMAL(10,2)) as total_estudio,
                        '' as observaciones,
                        c.documento_pdf,
                        c.documento_nombre,
                        c.fecha,
                        c.hora
                    FROM citas c
                    LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                    WHERE c.id_cita = %s
                """, (cita_id,))
            
            cita = cursor.fetchone()
            
            if not cita:
                cursor.close()
                db.close()
                self.send_json_response({'error': 'Cita no encontrada'}, 404)
                return
            
            if 'documento_pdf' in cita and cita['documento_pdf']:
                del cita['documento_pdf']
            
            if cita.get('total_estudio'):
                cita['total_estudio'] = float(cita['total_estudio'])
            
            cursor.close()
            db.close()
            
            self.send_json_response(cita, 200)
            
        except mysql.connector.Error as e:
            print(f"Error MySQL obteniendo detalles de cita: {str(e)}")
            self.send_json_response({'error': f'Error de base de datos: {str(e)}'}, 500)
        except Exception as e:
            print(f"Error general obteniendo detalles de cita: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    # ==============================================
    # FUNCIÓN PARA ACTUALIZAR UNA CITA EXISTENTE (COMPLETA)
    # ==============================================
    
    def handle_update_cita(self):
        """Actualizar una cita existente (formulario completo)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('cita_id')
            paciente = data.get('paciente')
            paciente_tel = data.get('pacienteTel', '')
            doctor_id = data.get('doctor_id')
            fecha_cita = data.get('fecha_cita')
            hora_cita = data.get('hora_cita')
            total_estudio = float(data.get('total_estudio', 0))
            observaciones = data.get('observaciones', '')
            formato_entrega = data.get('formato_entrega', 'Digital')
            formato_fotografia = data.get('formato_fotografia', 'USB')
            
            # Agregar formatos a observaciones si no están ya
            if f"Formato de entrega: {formato_entrega}" not in observaciones:
                observaciones = f"Formato de entrega: {formato_entrega}\n" + observaciones
            if f"Formato de fotografías: {formato_fotografia}" not in observaciones:
                observaciones = f"Formato de fotografías: {formato_fotografia}\n" + observaciones
            if paciente_tel and f"Teléfono: {paciente_tel}" not in observaciones:
                observaciones = f"Teléfono: {paciente_tel}\n" + observaciones
            
            if not cita_id or not paciente or not doctor_id or not fecha_cita or not hora_cita:
                raise ValueError("Faltan datos requeridos para actualizar la cita")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'observaciones'")
            tiene_observaciones = cursor.fetchone() is not None
            
            if tiene_observaciones:
                cursor.execute("""
                    UPDATE citas 
                    SET paciente = %s,
                        doctor_id = %s,
                        fecha_cita = %s,
                        hora_cita = %s,
                        total_estudio = %s,
                        observaciones = %s
                    WHERE id_cita = %s
                """, (paciente, doctor_id, fecha_cita, hora_cita, total_estudio, observaciones, cita_id))
            else:
                cursor.execute("""
                    UPDATE citas 
                    SET paciente = %s,
                        doctor_id = %s,
                        fecha_cita = %s,
                        hora_cita = %s,
                        total_estudio = %s
                    WHERE id_cita = %s
                """, (paciente, doctor_id, fecha_cita, hora_cita, total_estudio, cita_id))
            
            db.commit()
            print(f"[CITA] Cita ID {cita_id} actualizada exitosamente")
            
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Cita actualizada exitosamente',
                'cita_id': cita_id
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error actualizando cita: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIÓN PARA SUBIR RESULTADO
    # ==============================================
    
    def handle_upload_resultado(self):
        """Subir un archivo de resultado para una cita"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('cita_id')
            resultado_base64 = data.get('resultado_base64')
            resultado_nombre = data.get('resultado_nombre')
            resultado_tipo = data.get('resultado_tipo')
            
            if not all([cita_id, resultado_base64, resultado_nombre, resultado_tipo]):
                raise ValueError("Faltan datos requeridos para subir el resultado")
            
            resultado_pdf = base64.b64decode(resultado_base64)
            resultado_tamano = len(resultado_pdf)
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("""
                UPDATE citas 
                SET resultado = %s,
                    resultado_nombre = %s,
                    resultado_tipo = %s,
                    resultado_tamano = %s,
                    resultado_fecha_carga = NOW()
                WHERE id_cita = %s
            """, (resultado_pdf, resultado_nombre, resultado_tipo, resultado_tamano, cita_id))
            
            db.commit()
            
            cursor.execute("""
                UPDATE doctores d
                JOIN citas c ON d.Diddoctor = c.doctor_id
                SET d.puntos = d.puntos + 10
                WHERE c.id_cita = %s
            """, (cita_id,))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Resultado subido exitosamente. Se han añadido 10 puntos al doctor.'
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error subiendo resultado: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIÓN PARA DESCARGAR RESULTADO
    # ==============================================
    
    def handle_descargar_resultado(self, cita_id):
        """Descargar el resultado de una cita específica (cualquier tipo de archivo)"""
        try:
            print(f"[API] Descargando resultado para cita ID: {cita_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT resultado, resultado_nombre, resultado_tipo, numero_folio, paciente
                FROM citas 
                WHERE id_cita = %s AND resultado IS NOT NULL
            """, (cita_id,))
            
            cita = cursor.fetchone()
            cursor.close()
            db.close()
            
            if not cita or not cita['resultado']:
                print(f"[API] No se encontró resultado para la cita {cita_id}")
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Resultado no encontrado'}).encode())
                return
            
            resultado_content = cita['resultado']
            filename = cita['resultado_nombre'] or f"resultado_{cita['numero_folio']}{self.get_file_extension(cita['resultado_tipo'])}"
            content_type = cita['resultado_tipo'] or 'application/octet-stream'
            
            print(f"[API] Enviando resultado: {filename}, tipo: {content_type}, tamaño: {len(resultado_content)} bytes")
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(resultado_content)))
            self.send_header('Content-Transfer-Encoding', 'binary')
            self.end_headers()
            
            chunk_size = 8192
            for i in range(0, len(resultado_content), chunk_size):
                self.wfile.write(resultado_content[i:i+chunk_size])
            
        except Exception as e:
            print(f"Error descargando resultado: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def get_file_extension(self, mime_type):
        """Obtener extensión de archivo basada en el tipo MIME"""
        extension_map = {
            'application/zip': '.zip',
            'application/x-zip-compressed': '.zip',
            'application/pdf': '.pdf',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        }
        return extension_map.get(mime_type, '')

    # ==============================================
    # FUNCIÓN PARA OBTENER RESULTADOS DEL DOCTOR
    # ==============================================
    
    def handle_get_resultados(self, doctor_id):
        """Obtener todos los resultados de un doctor específico - EXCLUYE BLOBS"""
        try:
            print(f"[API] Obteniendo resultados para doctor_id: {doctor_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("SELECT Diddoctor FROM doctores WHERE Diddoctor = %s", (doctor_id,))
            doctor = cursor.fetchone()
            
            if not doctor:
                print(f"[API] Doctor no encontrado: {doctor_id}")
                cursor.close()
                db.close()
                self.send_json_response([], 200)
                return
            
            cursor.execute("""
                SELECT 
                    id_cita,
                    numero_folio,
                    paciente,
                    resultado_nombre,
                    resultado_tamano,
                    DATE_FORMAT(resultado_fecha_carga, '%d/%m/%Y %H:%i') as fecha_carga,
                    CASE WHEN resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado
                FROM citas 
                WHERE doctor_id = %s AND resultado IS NOT NULL
                ORDER BY resultado_fecha_carga DESC
            """, (doctor_id,))
            
            resultados = cursor.fetchall()
            print(f"[API] Se encontraron {len(resultados)} resultados para el doctor {doctor_id}")
            
            cursor.close()
            db.close()
            
            self.send_json_response(resultados, 200)
            
        except Exception as e:
            print(f"Error obteniendo resultados: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    # ==============================================
    # FUNCIÓN PARA DESCARGAR PDF DE CITA
    # ==============================================
    
    def handle_descargar_pdf(self, cita_id):
        """Descargar el PDF de una cita específica"""
        try:
            print(f"[API] Descargando PDF para cita ID: {cita_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT documento_pdf, documento_nombre, numero_folio, paciente, doctor_id
                FROM citas 
                WHERE id_cita = %s
            """, (cita_id,))
            
            cita = cursor.fetchone()
            cursor.close()
            db.close()
            
            if not cita or not cita['documento_pdf']:
                print(f"[API] No se encontró PDF para la cita {cita_id}")
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'PDF no encontrado'}).encode())
                return
            
            pdf_content = cita['documento_pdf']
            filename = cita['documento_nombre'] or f"cita_{cita['numero_folio']}.pdf"
            
            print(f"[API] Enviando PDF: {filename}, tamaño: {len(pdf_content)} bytes")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(len(pdf_content)))
            self.end_headers()
            self.wfile.write(pdf_content)
            
        except Exception as e:
            print(f"Error descargando PDF: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    # ==============================================
    # FUNCIÓN PARA OBTENER DOCTOR POR USUARIO
    # ==============================================
    
    def handle_get_doctor_by_user(self, username):
        """Obtener ID del doctor por nombre de usuario"""
        print(f"[API] Buscando doctor por usuario: '{username}'")
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT Diddoctor as id, nombre, usuario, puntos
                FROM doctores 
                WHERE usuario = %s AND activo = 1
            """, (username,))
            
            doctor = cursor.fetchone()
            cursor.close()
            db.close()
            
            if doctor:
                print(f"[API] Doctor encontrado: {doctor}")
                self.send_json_response(doctor, 200)
            else:
                print(f"[API] No se encontró doctor con usuario: '{username}'")
                self.send_json_response({'error': 'Doctor no encontrado'}, 404)
                
        except Exception as e:
            print(f"Error obteniendo doctor por usuario: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    # ==============================================
    # FUNCIÓN MEJORADA PARA GENERAR PDF DE RECETA
    # ==============================================
    
    def generate_pdf_cita(self, data):
        """
        Genera un PDF para la cita/receta mostrando SOLO los estudios seleccionados.
        Incluye teléfono del paciente, teléfono de consultorio del doctor y formato de entrega.
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                               rightMargin=36, leftMargin=36,
                               topMargin=36, bottomMargin=36)
        
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='CustomTitle', parent=styles['Heading1'],
            fontSize=16, textColor=colors.HexColor('#2d1b4a'),
            alignment=TA_LEFT, spaceAfter=6, fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='SectionHeader', parent=styles['Heading2'],
            fontSize=12, textColor=colors.HexColor('#6b3fa0'),
            alignment=TA_LEFT, spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold',
            borderPadding=(0, 0, 2, 0), borderWidth=1, borderColor=colors.HexColor('#d9c9f0')
        ))
        styles.add(ParagraphStyle(
            name='SubSectionHeader', parent=styles['Heading3'],
            fontSize=10, textColor=colors.HexColor('#2d1b4a'),
            alignment=TA_LEFT, spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='InfoLabel', parent=styles['Normal'],
            fontSize=9, textColor=colors.HexColor('#666666'),
            alignment=TA_LEFT, spaceAfter=1, fontName='Helvetica'
        ))
        styles.add(ParagraphStyle(
            name='InfoValue', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#000000'),
            alignment=TA_LEFT, spaceAfter=2, fontName='Helvetica'
        ))
        styles.add(ParagraphStyle(
            name='InfoRow', parent=styles['Normal'],
            fontSize=10, textColor=colors.HexColor('#000000'),
            alignment=TA_LEFT, spaceAfter=2, fontName='Helvetica'
        ))
        styles.add(ParagraphStyle(
            name='StudyStyle', parent=styles['Normal'],
            fontSize=9, alignment=TA_LEFT, leftIndent=10, fontName='Helvetica',
            spaceAfter=2
        ))
        styles.add(ParagraphStyle(
            name='FooterStyle', parent=styles['Normal'],
            fontSize=8, textColor=colors.grey, alignment=TA_CENTER
        ))
        
        story = []
        
        def get_checkbox_symbol():
            return "◉"
        
        def load_image(image_path, width=1*inch, height=1*inch):
            if os.path.exists(image_path):
                return Image(image_path, width=width, height=height)
            else:
                return None
        
        db = self.connect_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT nombre, especialidad, telefono_consultorio, email FROM doctores WHERE Diddoctor = %s", (data['doctor_id'],))
        doctor = cursor.fetchone()
        cursor.close()
        db.close()
        
        if not doctor and data['doctor_id'] == 'ADMIN':
            doctor = {'nombre': 'Administrador', 'especialidad': 'Administración', 'telefono_consultorio': 'N/A', 'email': 'admin@4digital.com'}
        
        # ==============================================
        # PÁGINA 1 - ENCABEZADO Y DATOS BÁSICOS
        # ==============================================
        
        header_data = []
        logo1 = load_image('LOGO4Digital.jpg', width=0.8*inch, height=0.8*inch)
        if logo1:
            header_data.append([logo1, Paragraph("614 6631185 / 614 5395488<br/><b>4DIGITAL</b><br/>Radiológica Dental Chihuahua", styles['InfoLabel'])])
        else:
            header_data.append([Paragraph("<b>4DIGITAL</b><br/>Radiológica Dental Chihuahua", styles['InfoLabel']), 
                               Paragraph("614 6631185 / 614 5395488", styles['InfoLabel'])])
        
        header_table = Table(header_data, colWidths=[1*inch, doc.width-1*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 12))
        
        info_data = [
            [Paragraph("<b>Paciente:</b> " + data['paciente'], styles['InfoRow'])],
        ]
        
        if data.get('pacienteTel'):
            info_data.append([Paragraph("<b>Teléfono:</b> " + data['pacienteTel'], styles['InfoRow'])])
        
        info_data.append([Paragraph("<b>Doctor(a):</b> " + (doctor['nombre'] if doctor else 'Administrador'), styles['InfoRow'])])
        info_data.append([Paragraph("<b>Especialidad:</b> " + (doctor['especialidad'] if doctor else 'Administración'), styles['InfoRow'])])
        
        if doctor and doctor.get('telefono_consultorio'):
            info_data.append([Paragraph("<b>Tel. Consultorio:</b> " + doctor['telefono_consultorio'], styles['InfoRow'])])
        
        info_table = Table(info_data, colWidths=[doc.width])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 6))
        
        if data.get('observaciones') and data['observaciones'] != 'Ninguna':
            story.append(Paragraph("<b>Observaciones:</b>", styles['InfoLabel']))
            story.append(Paragraph(data.get('observaciones', 'Ninguna'), styles['InfoValue']))
            story.append(Spacer(1, 6))
        
        # ==============================================
        # FORMATO DE ENTREGA
        # ==============================================
        story.append(Paragraph("<b>Formato de Entrega:</b>", styles['SubSectionHeader']))
        entrega = data.get('formato_entrega', 'Digital')
        story.append(Paragraph(f"{get_checkbox_symbol()} {entrega}", styles['StudyStyle']))
        story.append(Spacer(1, 6))
        
        story.append(Paragraph("_" * 100, styles['FooterStyle']))
        story.append(Spacer(1, 6))
        
        craneos_img = load_image('Craneos.png', width=doc.width-20, height=1.5*inch)
        if craneos_img:
            story.append(craneos_img)
            story.append(Spacer(1, 6))
        
        # ==============================================
        # ESTUDIOS SELECCIONADOS
        # ==============================================
        
        estudios_seleccionados = data.get('estudios', [])
        
        if estudios_seleccionados:
            categorias = {
                'RADIOGRAFÍAS 2D': [],
                'TOMOGRAFÍAS 3D': [],
                'ESTEREOLITOGRAFÍA': [],
                'ANÁLISIS CEFALOMÉTRICO': [],
                'FOTOGRAFÍA CLÍNICA': [],
                'ESCANEO E IMPRESIÓN 3D': [],
                'OTROS ESTUDIOS': []
            }
            
            for estudio in estudios_seleccionados:
                nombre = estudio['nombre']
                precio = estudio['precio']
                
                if isinstance(precio, (int, float)):
                    precio_formateado = f"${precio:,.2f}"
                else:
                    precio_formateado = str(precio)
                    if '$' not in precio_formateado:
                        precio_formateado = f"${precio_formateado}"
                
                texto_estudio = f"{get_checkbox_symbol()} {nombre} - {precio_formateado}"
                
                if any(p in nombre for p in ['Ortopantomografía', 'Panorámica', 'Lateral', 'P-A', 'A-P', 'Waters', 'ATM', 'Digito', 'Periapical', 'Oclusal', 'Senos paranasales']):
                    categorias['RADIOGRAFÍAS 2D'].append(texto_estudio)
                elif any(p in nombre for p in ['Tomografía', 'Endodoncia', 'Cirugía Ortognática', 'Ortodoncia 3D', 'Biblioteca de implantes']):
                    categorias['TOMOGRAFÍAS 3D'].append(texto_estudio)
                elif any(p in nombre for p in ['Maxilar', 'Mandibular', 'Hemimaxilar', 'Hemimandibular', 'Estereolitografía']):
                    categorias['ESTEREOLITOGRAFÍA'].append(texto_estudio)
                elif 'Cefalométrico' in nombre:
                    categorias['ANÁLISIS CEFALOMÉTRICO'].append(texto_estudio)
                elif any(p in nombre for p in ['Fotos', 'Fotografía']):
                    categorias['FOTOGRAFÍA CLÍNICA'].append(texto_estudio)
                elif any(p in nombre for p in ['Escaneo', 'Modelo', 'Guarda', 'Guía', 'iTero']):
                    categorias['ESCANEO E IMPRESIÓN 3D'].append(texto_estudio)
                else:
                    categorias['OTROS ESTUDIOS'].append(texto_estudio)
            
            for categoria, estudios_cat in categorias.items():
                if estudios_cat:
                    story.append(Paragraph(categoria, styles['SectionHeader']))
                    
                    if len(estudios_cat) > 8:
                        mitad = len(estudios_cat) // 2
                        col1 = estudios_cat[:mitad]
                        col2 = estudios_cat[mitad:]
                        
                        col1_parrafos = [Paragraph(est, styles['StudyStyle']) for est in col1]
                        col2_parrafos = [Paragraph(est, styles['StudyStyle']) for est in col2]
                        
                        while len(col1_parrafos) < len(col2_parrafos):
                            col1_parrafos.append(Paragraph("", styles['StudyStyle']))
                        while len(col2_parrafos) < len(col1_parrafos):
                            col2_parrafos.append(Paragraph("", styles['StudyStyle']))
                        
                        col_table_data = []
                        for i in range(len(col1_parrafos)):
                            col_table_data.append([col1_parrafos[i], col2_parrafos[i]])
                        
                        col_table = Table(col_table_data, colWidths=[doc.width/2.2, doc.width/2.2])
                        col_table.setStyle(TableStyle([
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                            ('LEFTPADDING', (0,0), (-1,-1), 5),
                            ('RIGHTPADDING', (0,0), (-1,-1), 5),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                        ]))
                        story.append(col_table)
                    else:
                        for est in estudios_cat:
                            story.append(Paragraph(est, styles['StudyStyle']))
                    
                    story.append(Spacer(1, 4))
            
            if data.get('formato_fotografia') and any('Fotos' in str(e) or 'Fotografía' in str(e) for e in estudios_seleccionados):
                story.append(Paragraph(f"Formato de fotografías: {data['formato_fotografia']}", styles['StudyStyle']))
                story.append(Spacer(1, 4))
        
        else:
            story.append(Paragraph("No se seleccionaron estudios", styles['StudyStyle']))
        
        # ==============================================
        # PÁGINA 2 - DESGLOSE DE PRECIOS Y FIRMAS
        # ==============================================
        story.append(PageBreak())
        
        story.append(Paragraph("4Digital - Radiología Médica", styles['CustomTitle']))
        story.append(Paragraph(f"Folio: {data['numero_folio']} - Paciente: {data['paciente']}", styles['FooterStyle']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("DESGLOSE DE ESTUDIOS", styles['SectionHeader']))
        
        if estudios_seleccionados:
            table_data = [['Estudio Solicitado', 'Precio']]
            total = 0
            
            for estudio in estudios_seleccionados:
                nombre = estudio['nombre']
                precio_str = estudio['precio']
                
                if isinstance(precio_str, str):
                    precio_limpio = precio_str.replace('$', '').replace(',', '').strip()
                    try:
                        precio_valor = float(precio_limpio)
                        total += precio_valor
                        precio_mostrar = f"${precio_valor:,.2f}"
                    except ValueError:
                        precio_valor = 0
                        precio_mostrar = precio_str
                else:
                    precio_valor = float(precio_str)
                    total += precio_valor
                    precio_mostrar = f"${precio_valor:,.2f}"
                
                table_data.append([nombre, precio_mostrar])
            
            # Agregar formato de entrega al desglose si tiene costo adicional
            formato_entrega = data.get('formato_entrega', 'Digital')
            if formato_entrega == 'USB':
                total += 50
                table_data.append(['Cargo por USB', '$50.00'])
            elif formato_entrega == 'DICOM':
                total += 100
                table_data.append(['Cargo por DICOM', '$100.00'])
            elif formato_entrega == 'Impreso':
                total += 30
                table_data.append(['Cargo por impresión', '$30.00'])
            
            price_table = Table(table_data, colWidths=[doc.width - 100, 100])
            price_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d1b4a')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('ALIGN', (1,0), (1,-1), 'RIGHT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d9c9f0')),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f5f0fa')),
            ]))
            story.append(price_table)
            story.append(Spacer(1, 15))
            
            story.append(Paragraph(f"<b>TOTAL:</b> ${total:,.2f}", ParagraphStyle(
                'Total',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=colors.HexColor('#2d1b4a'),
                alignment=TA_RIGHT,
                spaceBefore=5,
                spaceAfter=20
            )))
        else:
            story.append(Paragraph("No se especificaron estudios.", styles['StudyStyle']))
            story.append(Spacer(1, 20))
        
        story.append(Spacer(1, 30))
        story.append(Paragraph("FIRMAS", styles['SectionHeader']))
        
        signature_data = [
            [Paragraph("____________________________", styles['FooterStyle']),
             Paragraph("____________________________", styles['FooterStyle'])],
            [Paragraph("Firma del Paciente", styles['FooterStyle']),
             Paragraph(f"Firma del Dr(a). {doctor['nombre'] if doctor else 'Administrador'}", styles['FooterStyle'])]
        ]
        signature_table = Table(signature_data, colWidths=[doc.width/2.0]*2)
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,1), (-1,1), 5),
        ]))
        story.append(signature_table)
        story.append(Spacer(1, 20))
        
        story.append(Paragraph(f"Receta generada por: Administrador el {data['fecha_registro']} a las {data['hora_registro']}", styles['FooterStyle']))
        
        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        
        return pdf
    
    # ==============================================
    # FUNCIÓN PARA GENERAR CITA (RECETA VIRTUAL)
    # ==============================================

    def handle_generate_cita(self):
        """Generar una nueva cita desde receta virtual"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            paciente = data.get('paciente')
            paciente_tel = data.get('pacienteTel', '')
            doctor_id = data.get('doctor_id')
            estudios = data.get('estudios', [])
            observaciones = data.get('observaciones', '')
            fecha_cita = data.get('fecha_cita')
            hora_cita = data.get('hora_cita')
            total_estudio = float(data.get('total_estudio', 0))
            formato_entrega = data.get('formato_entrega', 'Digital')
            formato_fotografia = data.get('formato_fotografia', 'USB')
            
            # Agregar formatos a observaciones
            if paciente_tel:
                observaciones = f"Teléfono: {paciente_tel}\n" + observaciones
            observaciones = f"Formato de entrega: {formato_entrega}\n" + observaciones
            observaciones = f"Formato de fotografías: {formato_fotografia}\n" + observaciones
            
            if not paciente or not doctor_id:
                raise ValueError("Faltan datos requeridos: paciente o doctor_id")
            
            if not fecha_cita or not hora_cita:
                raise ValueError("Faltan datos de la cita: fecha y hora son requeridos")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            doctor_nombre = "Administrador"
            if doctor_id != 'ADMIN':
                cursor.execute("SELECT Diddoctor, nombre FROM doctores WHERE Diddoctor = %s", (doctor_id,))
                doctor = cursor.fetchone()
                
                if not doctor:
                    raise ValueError(f"El doctor con ID {doctor_id} no existe en la base de datos")
                doctor_nombre = doctor['nombre']
            
            cursor.execute("SELECT COUNT(*) as total FROM citas")
            result = cursor.fetchone()
            total_citas = result['total'] + 1
            numero_folio = f"FOL-{datetime.now().strftime('%Y%m%d')}-{str(total_citas).zfill(5)}"
            
            fecha_registro = datetime.now().strftime('%Y-%m-%d')
            hora_registro = datetime.now().strftime('%H:%M:%S')
            
            fecha_cita_formateada = datetime.strptime(fecha_cita, '%Y-%m-%d').strftime('%d/%m/%Y')
            hora_cita_formateada = hora_cita
            
            pdf_data = {
                'numero_folio': numero_folio,
                'fecha_registro': fecha_registro,
                'hora_registro': hora_registro,
                'fecha_cita': fecha_cita_formateada,
                'hora_cita': hora_cita_formateada,
                'paciente': paciente,
                'pacienteTel': paciente_tel,
                'doctor_id': doctor_id,
                'doctor_nombre': doctor_nombre,
                'estudios': estudios,
                'observaciones': observaciones,
                'total': total_estudio,
                'recepcionista': 'Administrador' if doctor_id == 'ADMIN' else 'Sistema',
                'formato_entrega': formato_entrega,
                'formato_fotografia': formato_fotografia
            }
            
            pdf_content = self.generate_pdf_cita(pdf_data)
            pdf_size = len(pdf_content)
            
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'observaciones'")
            tiene_observaciones = cursor.fetchone() is not None
            
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'fecha_eliminacion'")
            tiene_fecha_eliminacion = cursor.fetchone() is not None
            
            if tiene_observaciones and tiene_fecha_eliminacion:
                cursor.execute("""
                    INSERT INTO citas (
                        numero_folio, paciente, doctor_id, fecha, hora, 
                        fecha_cita, hora_cita, total_estudio, observaciones,
                        documento_nombre, documento_pdf, documento_tamano, documento_tipo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    numero_folio,
                    paciente,
                    doctor_id,
                    fecha_registro,
                    hora_registro,
                    fecha_cita,
                    hora_cita,
                    total_estudio,
                    observaciones,
                    f"{paciente}_{numero_folio}.pdf".replace(' ', '_'),
                    pdf_content,
                    pdf_size,
                    'application/pdf'
                ))
            elif tiene_observaciones:
                cursor.execute("""
                    INSERT INTO citas (
                        numero_folio, paciente, doctor_id, fecha, hora, 
                        fecha_cita, hora_cita, total_estudio, observaciones,
                        documento_nombre, documento_pdf, documento_tamano, documento_tipo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    numero_folio,
                    paciente,
                    doctor_id,
                    fecha_registro,
                    hora_registro,
                    fecha_cita,
                    hora_cita,
                    total_estudio,
                    observaciones,
                    f"{paciente}_{numero_folio}.pdf".replace(' ', '_'),
                    pdf_content,
                    pdf_size,
                    'application/pdf'
                ))
            else:
                cursor.execute("""
                    INSERT INTO citas (
                        numero_folio, paciente, doctor_id, fecha, hora, 
                        fecha_cita, hora_cita, total_estudio,
                        documento_nombre, documento_pdf, documento_tamano, documento_tipo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    numero_folio,
                    paciente,
                    doctor_id,
                    fecha_registro,
                    hora_registro,
                    fecha_cita,
                    hora_cita,
                    total_estudio,
                    f"{paciente}_{numero_folio}.pdf".replace(' ', '_'),
                    pdf_content,
                    pdf_size,
                    'application/pdf'
                ))
            
            db.commit()
            print(f"[CITA] Cita generada exitosamente - Folio: {numero_folio}, Doctor: {doctor_id}, Total: ${total_estudio}")
            
            cursor.execute("SELECT LAST_INSERT_ID() as id")
            cita_id = cursor.fetchone()['id']
            
            cursor.close()
            db.close()
            
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            response = {
                'success': True,
                'message': 'Cita generada exitosamente',
                'cita_id': cita_id,
                'numero_folio': numero_folio,
                'fecha': fecha_registro,
                'hora': hora_registro,
                'pdf_base64': pdf_base64
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error generando cita: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIÓN PARA OBTENER CITAS DEL DOCTOR
    # ==============================================
    
    def handle_get_citas(self, doctor_id):
        """Obtener todas las citas de un doctor específico"""
        try:
            print(f"[API] Obteniendo citas para doctor_id: {doctor_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("SELECT Diddoctor FROM doctores WHERE Diddoctor = %s", (doctor_id,))
            doctor = cursor.fetchone()
            
            if not doctor and doctor_id != 'ADMIN':
                print(f"[API] Doctor no encontrado: {doctor_id}")
                cursor.close()
                db.close()
                self.send_json_response([], 200)
                return
            
            cursor.execute("""
                SELECT 
                    id_cita,
                    numero_folio,
                    paciente,
                    DATE_FORMAT(fecha, '%d/%m/%Y') as fecha_registro,
                    TIME_FORMAT(hora, '%H:%i') as hora_registro,
                    DATE_FORMAT(fecha_cita, '%Y-%m-%d') as fecha_cita,
                    TIME_FORMAT(hora_cita, '%H:%i') as hora_cita,
                    CAST(total_estudio AS DECIMAL(10,2)) as total_estudio,
                    CASE WHEN documento_pdf IS NOT NULL THEN 1 ELSE 0 END as tiene_pdf,
                    CASE WHEN resultado IS NOT NULL THEN 1 ELSE 0 END as tiene_resultado,
                    DATE_FORMAT(resultado_fecha_carga, '%d/%m/%Y %H:%i') as resultado_fecha_carga
                FROM citas 
                WHERE doctor_id = %s
                ORDER BY fecha_cita DESC, hora_cita DESC
            """, (doctor_id,))
            
            citas = cursor.fetchall()
            print(f"[API] Se encontraron {len(citas)} citas para el doctor {doctor_id}")
            
            for cita in citas:
                if cita['total_estudio'] is None:
                    cita['total_estudio'] = 0.00
                else:
                    cita['total_estudio'] = float(cita['total_estudio'])
            
            cursor.close()
            db.close()
            
            self.send_json_response(citas, 200)
            
        except Exception as e:
            print(f"Error obteniendo citas: {str(e)}")
            self.send_json_response({'error': str(e), 'citas': []}, 500)

    # ==============================================
    # FUNCIÓN PARA OBTENER TODAS LAS CITAS (ADMIN)
    # ==============================================
    
    def handle_get_all_citas(self):
        """Obtener todas las citas para el panel de admin (solo activas)"""
        try:
            print(f"[API] Obteniendo todas las citas activas")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'estado'")
            tiene_estado = cursor.fetchone()
            
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'fecha_eliminacion'")
            tiene_fecha_eliminacion = cursor.fetchone() is not None
            
            if tiene_estado:
                cursor.execute("""
                    SELECT 
                        c.id_cita,
                        c.numero_folio,
                        c.paciente,
                        COALESCE(d.nombre, 'Administrador') as doctor_nombre,
                        c.doctor_id,
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
                    FROM citas c
                    LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                    WHERE (c.estado = 'activa' OR c.estado IS NULL)
                    ORDER BY c.fecha_cita DESC, c.hora_cita DESC
                """)
            else:
                cursor.execute("""
                    SELECT 
                        c.id_cita,
                        c.numero_folio,
                        c.paciente,
                        COALESCE(d.nombre, 'Administrador') as doctor_nombre,
                        c.doctor_id,
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
                    FROM citas c
                    LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                    ORDER BY c.fecha_cita DESC, c.hora_cita DESC
                """)
            
            citas = cursor.fetchall()
            print(f"[API] Se encontraron {len(citas)} citas activas")
            
            for cita in citas:
                if cita['total_estudio'] is None:
                    cita['total_estudio'] = 0.00
                else:
                    cita['total_estudio'] = float(cita['total_estudio'])
            
            cursor.close()
            db.close()
            
            self.send_json_response(citas, 200)
            
        except Exception as e:
            print(f"Error obteniendo todas las citas: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)

    # ==============================================
    # FUNCIONES PARA ADMIN
    # ==============================================
    
    def handle_admin_stats(self):
        """Obtener estadísticas para el panel de admin"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("SELECT COUNT(*) as total FROM doctores WHERE activo = 1")
            total_doctores = cursor.fetchone()['total']
            
            cursor.execute("SHOW COLUMNS FROM citas LIKE 'estado'")
            tiene_estado = cursor.fetchone()
            
            if tiene_estado:
                cursor.execute("SELECT COUNT(*) as total FROM citas WHERE estado = 'activa' OR estado IS NULL")
            else:
                cursor.execute("SELECT COUNT(*) as total FROM citas")
            total_citas = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM doctores 
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
                FROM citas 
                WHERE fecha_eliminacion IS NOT NULL AND fecha_eliminacion >= CURDATE()
            """)
            proxima_eliminacion = cursor.fetchone()['proxima']
            
            cursor.execute("SELECT SUM(puntos) as total_puntos FROM doctores")
            total_puntos = cursor.fetchone()['total_puntos'] or 0
            
            cursor.close()
            db.close()
            
            stats = {
                'totalDoctores': total_doctores,
                'estudiosPendientes': estudios_pendientes,
                'nuevosDoctores': nuevos_doctores,
                'estudiosCompletados': citas_completadas,
                'totalCitas': total_citas,
                'totalPuntos': total_puntos,
                'citasAEliminar': citas_eliminar,
                'proximaEliminacion': proxima_eliminacion or '-'
            }
            
            self.send_json_response(stats, 200)
            
        except Exception as e:
            print(f"Error en stats: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    def handle_admin_activity(self):
        """Obtener actividad reciente de la base de datos"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    COALESCE(CONCAT('Dr. ', d.nombre), 'Administrador') as usuario_id,
                    CASE WHEN d.nombre IS NOT NULL THEN 'doctor' ELSE 'admin' END as tipo_usuario,
                    'Nueva cita' as accion,
                    DATE_FORMAT(c.fecha, '%Y-%m-%d %H:%i') as fecha,
                    CONCAT('Paciente: ', c.paciente, ' - Folio: ', c.numero_folio, ' - Total: $', FORMAT(c.total_estudio, 2)) as detalles
                FROM citas c
                LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                WHERE c.id_cita IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    CONCAT('Dr. ', d.nombre) as usuario_id,
                    'doctor' as tipo_usuario,
                    'Registro' as accion,
                    DATE_FORMAT(d.fecha_registro, '%Y-%m-%d %H:%i') as fecha,
                    CONCAT('ID: ', d.Diddoctor, ' - ', COALESCE(d.especialidad, 'Sin especialidad'), ' - Puntos: ', d.puntos) as detalles
                FROM doctores d
                WHERE d.fecha_registro IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    'ADMIN' as usuario_id,
                    'admin' as tipo_usuario,
                    'Cancelar cita' as accion,
                    aa.fecha,
                    aa.detalles
                FROM actividad_admin aa
                WHERE aa.accion = 'CANCELAR_CITA'
                
                UNION ALL
                
                SELECT 
                    'ADMIN' as usuario_id,
                    'admin' as tipo_usuario,
                    'Entregar resultado' as accion,
                    aa.fecha,
                    aa.detalles
                FROM actividad_admin aa
                WHERE aa.accion = 'ENTREGAR_RESULTADO'
                
                UNION ALL
                
                SELECT 
                    'ADMIN' as usuario_id,
                    'admin' as tipo_usuario,
                    'Programar eliminación' as accion,
                    aa.fecha,
                    aa.detalles
                FROM actividad_admin aa
                WHERE aa.accion = 'PROGRAMAR_ELIMINACION'
                
                UNION ALL
                
                SELECT 
                    'ADMIN' as usuario_id,
                    'admin' as tipo_usuario,
                    'Cancelar eliminación' as accion,
                    aa.fecha,
                    aa.detalles
                FROM actividad_admin aa
                WHERE aa.accion = 'CANCELAR_ELIMINACION'
                
                ORDER BY fecha DESC
                LIMIT 20
            """)
            
            actividades = cursor.fetchall()
            
            if len(actividades) == 0:
                cursor.execute("""
                    SELECT 
                        CONCAT('Dr. ', nombre) as usuario_id,
                        'doctor' as tipo_usuario,
                        'Registro' as accion,
                        DATE_FORMAT(fecha_registro, '%Y-%m-%d %H:%i') as fecha,
                        CONCAT('ID: ', Diddoctor, ' - ', COALESCE(especialidad, 'Sin especialidad'), ' - Puntos: ', puntos) as detalles
                    FROM doctores
                    WHERE fecha_registro IS NOT NULL
                    ORDER BY fecha_registro DESC
                    LIMIT 10
                """)
                actividades = cursor.fetchall()
            
            if len(actividades) == 0:
                actividades = [{
                    'usuario_id': 'Sistema',
                    'tipo_usuario': 'admin',
                    'accion': 'Bienvenida',
                    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'detalles': 'Sistema de radiología iniciado'
                }]
            
            cursor.close()
            db.close()
            
            self.send_json_response(actividades, 200)
            
        except Exception as e:
            print(f"Error en actividad: {str(e)}")
            actividades = [{
                'usuario_id': 'Sistema',
                'tipo_usuario': 'admin',
                'accion': 'Sistema activo',
                'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'detalles': f'Sistema funcionando correctamente'
            }]
            self.send_json_response(actividades, 200)
    
    # ==============================================
    # FUNCIONES PARA DOCTORES
    # ==============================================
    
    def handle_get_doctor_info(self, doctor_id):
        """Obtener información básica del doctor"""
        print(f"[API] handle_get_doctor_info para doctor_id: {doctor_id}")
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT Diddoctor as id, nombre, especialidad, email, telefono, usuario,
                       direccion_consultorio, telefono_consultorio, 
                       DATE_FORMAT(fecha_registro, '%Y-%m-%d') as fecha_registro,
                       activo, puntos
                FROM doctores 
                WHERE Diddoctor = %s
            """, (doctor_id,))
            
            doctor = cursor.fetchone()
            
            if not doctor:
                cursor.close()
                db.close()
                self.send_json_response({'error': 'Doctor no encontrado'}, 404)
                return
            
            cursor.close()
            db.close()
            
            self.send_json_response(doctor, 200)
            
        except Exception as e:
            print(f"Error obteniendo información del doctor: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    def handle_get_doctor_details(self, doctor_id):
        """Obtener detalles completos de un doctor específico"""
        print(f"[API] handle_get_doctor_details para doctor_id: {doctor_id}")
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    Diddoctor as id, 
                    nombre, 
                    usuario, 
                    contrasena,
                    especialidad, 
                    email, 
                    telefono, 
                    direccion_consultorio,
                    telefono_consultorio,
                    DATE_FORMAT(fecha_registro, '%Y-%m-%d') as fecha_registro,
                    activo,
                    puntos
                FROM doctores 
                WHERE Diddoctor = %s
            """, (doctor_id,))
            
            doctor = cursor.fetchone()
            
            if not doctor:
                cursor.close()
                db.close()
                self.send_json_response({'error': 'Doctor no encontrado'}, 404)
                return
            
            cursor.execute("""
                SELECT COUNT(*) as total_citas
                FROM citas
                WHERE doctor_id = %s
            """, (doctor_id,))
            citas_result = cursor.fetchone()
            doctor['total_citas'] = citas_result['total_citas'] if citas_result else 0
            
            cursor.execute("""
                SELECT COUNT(DISTINCT paciente) as total_pacientes
                FROM citas
                WHERE doctor_id = %s
            """, (doctor_id,))
            pacientes_result = cursor.fetchone()
            doctor['total_pacientes'] = pacientes_result['total_pacientes'] if pacientes_result else 0
            
            cursor.execute("""
                SELECT COUNT(*) as estudios_pendientes
                FROM citas
                WHERE doctor_id = %s AND resultado IS NULL
            """, (doctor_id,))
            pendientes_result = cursor.fetchone()
            doctor['estudios_pendientes'] = pendientes_result['estudios_pendientes'] if pendientes_result else 0
            
            doctor['activo'] = bool(doctor['activo'])
            
            cursor.close()
            db.close()
            
            self.send_json_response(doctor, 200)
            
        except Exception as e:
            print(f"Error obteniendo detalles del doctor: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    def handle_get_doctores(self):
        """Obtener lista completa de doctores (incluyendo ADMIN)"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    Diddoctor as id, 
                    nombre, 
                    usuario, 
                    contrasena,
                    especialidad, 
                    email, 
                    telefono, 
                    direccion_consultorio,
                    telefono_consultorio,
                    DATE_FORMAT(fecha_registro, '%Y-%m-%d') as fecha_registro,
                    activo,
                    puntos
                FROM doctores
                ORDER BY Diddoctor ASC
            """)
            
            doctores = cursor.fetchall()
            
            doctores_admin = [{
                'id': 'ADMIN',
                'nombre': 'Administrador',
                'usuario': 'admin',
                'contrasena': '',
                'especialidad': 'Administración',
                'email': 'admin@radiologia.com',
                'telefono': 'N/A',
                'telefono_consultorio': 'N/A',
                'direccion_consultorio': 'N/A',
                'fecha_registro': datetime.now().strftime('%Y-%m-%d'),
                'activo': True,
                'puntos': 0,
                'total_citas': 0,
                'pacientes': 0,
                'estudios_pendientes': 0
            }]
            
            for doctor in doctores:
                cursor.execute("""
                    SELECT COUNT(*) as total_citas
                    FROM citas
                    WHERE doctor_id = %s
                """, (doctor['id'],))
                citas_result = cursor.fetchone()
                doctor['total_citas'] = citas_result['total_citas'] if citas_result else 0
                
                cursor.execute("""
                    SELECT COUNT(DISTINCT paciente) as total_pacientes
                    FROM citas
                    WHERE doctor_id = %s
                """, (doctor['id'],))
                pacientes_result = cursor.fetchone()
                doctor['pacientes'] = pacientes_result['total_pacientes'] if pacientes_result else 0
                
                cursor.execute("""
                    SELECT COUNT(*) as estudios_pendientes
                    FROM citas
                    WHERE doctor_id = %s AND resultado IS NULL
                """, (doctor['id'],))
                pendientes_result = cursor.fetchone()
                doctor['estudios_pendientes'] = pendientes_result['estudios_pendientes'] if pendientes_result else 0
                
                doctor['activo'] = bool(doctor['activo'])
            
            doctores_combinados = doctores_admin + doctores
            
            cursor.close()
            db.close()
            
            self.send_json_response(doctores_combinados, 200)
            
        except Exception as e:
            print(f"Error obteniendo doctores: {str(e)}")
            self.send_json_response({'error': str(e)}, 500)
    
    # ==============================================
    # FUNCIÓN PARA CAMBIO DE CONTRASEÑA
    # ==============================================
    
    def handle_change_doctor_password(self):
        """Cambiar contraseña de un doctor"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            doctor_id = data.get('doctor_id')
            new_password = data.get('new_password')
            
            if not doctor_id or not new_password:
                raise ValueError("Faltan datos requeridos")
            
            if len(new_password) < 6:
                raise ValueError("La contraseña debe tener al menos 6 caracteres")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("""
                UPDATE doctores 
                SET contrasena = %s 
                WHERE Diddoctor = %s
            """, (new_password, doctor_id))
            
            db.commit()
            
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Contraseña actualizada correctamente'
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error cambiando contraseña: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIÓN PARA CREAR DOCTOR
    # ==============================================
    
    def handle_create_doctor(self):
        """Crear un nuevo doctor"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            nombre = data.get('nombre')
            usuario = data.get('usuario')
            password = data.get('password')
            email = data.get('email')
            telefono = data.get('telefono', '')
            telefono_consultorio = data.get('telefono_consultorio', '')
            direccion_consultorio = data.get('direccion_consultorio', '')
            especialidad = data.get('especialidad', '')
            
            if not all([nombre, usuario, password, email]):
                raise ValueError("Faltan campos obligatorios: nombre, usuario, contraseña y email son requeridos")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT usuario FROM doctores WHERE usuario = %s 
                UNION SELECT usuario FROM administradores WHERE usuario = %s
            """, (usuario, usuario))
            if cursor.fetchone():
                raise ValueError("El nombre de usuario ya está en uso")
            
            cursor.execute("""
                SELECT email FROM doctores WHERE email = %s 
                UNION SELECT email FROM administradores WHERE email = %s
            """, (email, email))
            if cursor.fetchone():
                raise ValueError("El correo electrónico ya está registrado")
            
            cursor.execute("SELECT MAX(CAST(SUBSTRING(Diddoctor, 2) AS UNSIGNED)) as max_id FROM doctores")
            result = cursor.fetchone()
            max_id = result['max_id'] if result['max_id'] else 0
            nuevo_id = f"D{str(max_id + 1).zfill(3)}"
            
            cursor.execute("""
                INSERT INTO doctores (
                    Diddoctor, nombre, usuario, contrasena, especialidad, 
                    email, telefono, direccion_consultorio, telefono_consultorio,
                    fecha_registro, activo, puntos
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1, 0)
            """, (
                nuevo_id, nombre, usuario, password, especialidad, 
                email, telefono, direccion_consultorio, telefono_consultorio
            ))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': f'Doctor registrado exitosamente. Su ID es: {nuevo_id}'
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error creando doctor: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_json_response(response, 500)
    
    # ==============================================
    # FUNCIONES DE LOGIN Y REGISTRO
    # ==============================================
    
    def handle_login(self):
        """Manejar el inicio de sesión"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_qs(post_data.decode())
            
            username = data.get('username', [''])[0]
            password = data.get('password', [''])[0]
            
            print(f"[LOGIN] Intento de login: usuario={username}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            usuario_encontrado = False
            tipo_usuario = ''
            user_id = ''
            user_name = ''
            
            cursor.execute("SELECT * FROM administradores WHERE usuario = %s AND contrasena = %s", 
                          (username, password))
            admin = cursor.fetchone()
            if admin:
                usuario_encontrado = True
                tipo_usuario = 'admin'
                user_id = admin['Aidadmin']
                user_name = admin['nombre']
            
            if not usuario_encontrado:
                cursor.execute("SELECT * FROM doctores WHERE usuario = %s AND contrasena = %s", 
                              (username, password))
                doctor = cursor.fetchone()
                if doctor:
                    if doctor['activo'] == 0:
                        cursor.close()
                        db.close()
                        self.send_json_response({'success': False, 'message': 'Su cuenta está desactivada. Contacte al administrador.'}, 401)
                        return
                    
                    usuario_encontrado = True
                    tipo_usuario = 'doctor'
                    user_id = doctor['Diddoctor']
                    user_name = doctor['usuario']
                    print(f"[LOGIN] Doctor encontrado - ID: {user_id}, Usuario: {user_name}")
            
            cursor.close()
            db.close()
            
            if usuario_encontrado:
                if tipo_usuario == 'doctor':
                    redirect_url = f'/dashboard?doctor_id={user_id}'
                else:
                    redirect_url = '/admin'
                
                response = {
                    'success': True,
                    'tipo': tipo_usuario,
                    'user_id': user_id,
                    'user_name': user_name,
                    'redirect': redirect_url
                }
                
                self.send_json_response(response, 200)
            else:
                self.send_json_response({'success': False, 'message': 'Credenciales incorrectas'}, 401)
                
        except Exception as e:
            print(f"Error en login: {str(e)}")
            self.send_json_response({'success': False, 'message': 'Error del servidor'}, 500)
    
    def handle_registro(self):
        """Manejar el registro de nuevos doctores"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = parse_qs(post_data.decode())
            
            nombre_completo = data.get('nombre', [''])[0] + " " + data.get('apellidos', [''])[0]
            usuario = data.get('usuario', [''])[0]
            contrasena = data.get('contrasena', [''])[0]
            especialidad = data.get('especialidad', [''])[0]
            email = data.get('correo', [''])[0]
            telefono = data.get('telefono', [''])[0]
            direccion_consultorio = data.get('direccion_consultorio', [''])[0]
            telefono_consultorio = data.get('telefono_consultorio', [''])[0]
            
            if not all([nombre_completo, usuario, contrasena, especialidad, email, telefono, direccion_consultorio, telefono_consultorio]):
                raise ValueError("Faltan campos obligatorios")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("SELECT usuario FROM doctores WHERE usuario = %s UNION SELECT usuario FROM administradores WHERE usuario = %s", 
                          (usuario, usuario))
            if cursor.fetchone():
                raise ValueError("El nombre de usuario ya está en uso")
            
            cursor.execute("SELECT email FROM doctores WHERE email = %s UNION SELECT email FROM administradores WHERE email = %s", 
                          (email, email))
            if cursor.fetchone():
                raise ValueError("El correo electrónico ya está registrado")
            
            cursor.execute("SELECT MAX(CAST(SUBSTRING(Diddoctor, 2) AS UNSIGNED)) as max_id FROM doctores")
            result = cursor.fetchone()
            max_id = result[0] if result[0] else 0
            nuevo_id = f"D{str(max_id + 1).zfill(3)}"
            
            cursor.execute("""
                INSERT INTO doctores (
                    Diddoctor, nombre, usuario, contrasena, especialidad, 
                    email, telefono, direccion_consultorio, telefono_consultorio,
                    fecha_registro, activo, puntos
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1, 0)
            """, (
                nuevo_id, nombre_completo, usuario, contrasena, especialidad, 
                email, telefono, direccion_consultorio, telefono_consultorio
            ))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': f'Doctor registrado exitosamente. Su ID es: {nuevo_id}',
                'redirect': '/'
            }
            
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error en registro: {str(e)}")
            self.send_json_response({'success': False, 'message': f'Error: {str(e)}'}, 500)
    
    # ==============================================
    # FUNCIONES DE ADMINISTRACIÓN DE USUARIOS
    # ==============================================
    
    def handle_update_user(self):
        """Actualizar doctor con todos los campos"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            user_id = data.get('userId')
            user_type = data.get('userType')
            nombre = data.get('nombre')
            email = data.get('email')
            telefono = data.get('telefono')
            telefono_consultorio = data.get('telefono_consultorio')
            direccion_consultorio = data.get('direccion_consultorio')
            estado = data.get('estado')
            password = data.get('password')
            especialidad = data.get('especialidad')
            usuario = data.get('usuario')
            puntos = data.get('puntos')
            
            if not user_id or not user_type:
                raise ValueError("Faltan datos requeridos")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            if user_type == 'doctor':
                table = 'doctores'
                id_field = 'Diddoctor'
                
                update_fields = []
                params = []
                
                if nombre:
                    update_fields.append("nombre = %s")
                    params.append(nombre)
                
                if usuario:
                    cursor.execute("""
                        SELECT Diddoctor FROM doctores 
                        WHERE usuario = %s AND Diddoctor != %s
                    """, (usuario, user_id))
                    if cursor.fetchone():
                        raise ValueError("El nombre de usuario ya está en uso")
                    
                    update_fields.append("usuario = %s")
                    params.append(usuario)
                
                if email:
                    cursor.execute("""
                        SELECT Diddoctor FROM doctores 
                        WHERE email = %s AND Diddoctor != %s
                    """, (email, user_id))
                    if cursor.fetchone():
                        raise ValueError("El correo electrónico ya está en uso")
                    
                    update_fields.append("email = %s")
                    params.append(email)
                
                if telefono is not None:
                    update_fields.append("telefono = %s")
                    params.append(telefono)
                
                if telefono_consultorio is not None:
                    update_fields.append("telefono_consultorio = %s")
                    params.append(telefono_consultorio)
                
                if direccion_consultorio is not None:
                    update_fields.append("direccion_consultorio = %s")
                    params.append(direccion_consultorio)
                
                if especialidad:
                    update_fields.append("especialidad = %s")
                    params.append(especialidad)
                
                if estado is not None:
                    activo = 1 if estado == 'active' else 0
                    update_fields.append("activo = %s")
                    params.append(activo)
                
                if puntos is not None:
                    update_fields.append("puntos = %s")
                    params.append(int(puntos))
                
                if password and password.strip():
                    update_fields.append("contrasena = %s")
                    params.append(password)
                
                if update_fields:
                    query = f"UPDATE {table} SET {', '.join(update_fields)} WHERE {id_field} = %s"
                    params.append(user_id)
                    
                    cursor.execute(query, params)
                    db.commit()
            
            cursor.close()
            db.close()
            
            response = {'success': True, 'message': 'Doctor actualizado correctamente'}
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error actualizando usuario: {str(e)}")
            response = {'success': False, 'message': str(e)}
            self.send_json_response(response, 500)
    
    def handle_delete_user(self):
        """Eliminar doctor"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            user_id = data.get('userId')
            user_type = data.get('userType')
            
            if not user_id or not user_type:
                raise ValueError("Faltan datos requeridos")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            if user_type == 'doctor':
                cursor.execute("DELETE FROM doctores WHERE Diddoctor = %s", (user_id,))
                db.commit()
            else:
                raise ValueError("Tipo de usuario no válido")
            
            cursor.close()
            db.close()
            
            response = {'success': True, 'message': 'Doctor eliminado correctamente'}
            self.send_json_response(response, 200)
            
        except Exception as e:
            print(f"Error eliminando doctor: {str(e)}")
            response = {'success': False, 'message': str(e)}
            self.send_json_response(response, 500)
    
    # ==============================================
    # CONEXIÓN A BASE DE DATOS
    # ==============================================
    
    def connect_db(self):
        """Conectar a la base de datos MySQL"""
        try:
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="radiologia_db"
            )
            return connection
        except mysql.connector.Error as e:
            print(f"❌ Error MySQL: {e}")
            raise

# Configuración del servidor
PORT = 8000

print("=" * 60)
print("🚀 SERVIDOR RADIOLOGÍA MÉDICA - VERSIÓN COMPLETA")
print("=" * 60)
print(f"📊 Accede a: http://localhost:{PORT}")
print("\n👥 Usuarios de prueba:")
print("   • Doctor:    dr.rodriguez / doctor123")
print("   • Admin:     admin / admin123")
print("\n📝 Registro disponible en: /registro")
print("👑 Panel de administración: /admin")
print("✅ Gestión de Resultados con puntos automáticos")
print("✅ 1 punto por cada $100 en resultados entregados")
print("✅ Eliminación programada de citas")
print("✅ PDF mejorado con checkboxes y formato profesional")
print("✅ Teléfono de paciente y teléfono de consultorio incluidos")
print("✅ Formato de entrega: Digital, USB, DICOM, Impreso")
print("✅ NUEVO: Consulta pública de resultados por folio")
print("=" * 60)

if not os.path.exists('templates'):
    os.makedirs('templates')
    print("📁 Carpeta 'templates' creada")

try:
    from reportlab.lib import colors
    print("✅ ReportLab instalado correctamente")
except ImportError:
    print("⚠️ ReportLab no está instalado. Instalando...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'reportlab'])
    print("✅ ReportLab instalado correctamente")

if not os.path.exists('LOGO4Digital.jpg'):
    print("⚠️ Logo no encontrado: LOGO4Digital.jpg (el PDF se generará sin logo)")
if not os.path.exists('Craneos.png'):
    print("⚠️ Imagen no encontrada: Craneos.png (el PDF se generará sin la imagen de referencia)")

try:
    server = HTTPServer(('', PORT), CustomHandler)
    print("\n✅ Servidor listo. Presiona Ctrl+C para detenerlo.")
    server.serve_forever()
except KeyboardInterrupt:
    print("\n⏹️  Servidor detenido")