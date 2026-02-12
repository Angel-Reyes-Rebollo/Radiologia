# app.py
import base64
import hashlib
import json
import os
import random
import string
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import mysql.connector


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
        elif path == '/paciente-doctor':
            return os.path.join(os.getcwd(), 'templates', 'paciente-doctor.html')
        elif path == '/resultados-doctor':
            return os.path.join(os.getcwd(), 'templates', 'resultados-doctor.html')
        elif path == '/configuracion-doctor':
            return os.path.join(os.getcwd(), 'templates', 'configuracion-doctor.html')
        elif path == '/RecetaV':
            return os.path.join(os.getcwd(), 'templates', 'RecetaV.html')
        elif path.endswith('.html'):
            filename = os.path.basename(path)
            return os.path.join(os.getcwd(), 'templates', filename)
        
        return os.path.join(os.getcwd(), path.lstrip('/'))
    
    def do_GET(self):
        """Manejar peticiones GET"""
        try:
            if self.path == '/favicon.ico':
                self.send_error(404)
                return
        
            print(f"[API GET] {self.path}")
        
            # RUTAS ESPECÍFICAS PARA AGENDA
            if self.path.startswith('/api/doctor-appointments/'):
                parts = self.path.split('/')
                if len(parts) >= 4:
                    doctor_id = parts[3]
                    self.handle_get_doctor_appointments(doctor_id)
                    return
            
            # RUTAS PARA RESULTADOS
            if self.path.startswith('/api/doctor-studies/'):
                parts = self.path.split('/')
                if len(parts) >= 4:
                    doctor_id = parts[3]
                    self.handle_get_doctor_studios(doctor_id)
                    return
            
            if self.path.startswith('/api/doctor-study-stats/'):
                parts = self.path.split('/')
                if len(parts) >= 4:
                    doctor_id = parts[3]
                    self.handle_get_doctor_study_stats(doctor_id)
                    return
            
            # RUTA PARA VER PDF DE CITA
            if self.path.startswith('/api/cita-pdf/'):
                cita_id = self.path.split('/')[-1]
                self.handle_get_cita_pdf(cita_id)
                return
            
            if self.path == '/api/dashboard/doctor-stats':
                self.handle_doctor_dashboard_stats()
                return
            elif self.path.startswith('/api/dashboard/doctor/'):
                doctor_id = self.path.split('/')[-1]
                self.handle_dashboard_doctor_data(doctor_id)
                return
            elif self.path == '/api/admin/stats':
                self.handle_admin_stats()
                return
            elif self.path == '/api/admin/activity':
                self.handle_admin_activity()
                return
            elif self.path.startswith('/api/doctor/'):
                if self.path.endswith('/stats'):
                    parts = self.path.split('/')
                    if len(parts) == 4:
                        doctor_id = parts[2]
                        self.handle_doctor_stats(doctor_id)
                        return
            elif self.path.startswith('/api/doctores'):
                if self.path == '/api/doctores':
                    self.handle_get_doctores()
                else:
                    doctor_id = self.path.split('/')[-1]
                    self.handle_get_doctor(doctor_id)
                return
            elif self.path.startswith('/api/citas'):
                if self.path == '/api/citas':
                    self.handle_get_citas()
                else:
                    cita_id = self.path.split('/')[-1]
                    self.handle_get_cita(cita_id)
                return
            elif self.path == '/api/estudios':
                self.handle_get_estudios()
                return
            elif self.path.startswith('/api/usuarios/'):
                partes = self.path.split('/')
                if len(partes) == 5:
                    tipo = partes[3]
                    user_id = partes[4]
                    self.handle_get_usuario(user_id, tipo)
                    return
            elif self.path.startswith('/api/doctor-patients'):
                self.handle_get_doctor_patients()
                return
            elif self.path.startswith('/api/doctor-patient-citas/'):
                parts = self.path.split('/')
                if len(parts) == 5:
                    paciente_id = parts[-1]
                    self.handle_get_patient_citas(paciente_id)
                return
            elif self.path.startswith('/api/doctor-info/'):
                doctor_id = self.path.split('/')[-1]
                self.handle_get_doctor_info(doctor_id)
                return
            
            super().do_GET()
        except Exception as e:
            print(f"Error en GET {self.path}: {str(e)}")
            self.send_error(404)
    
    def do_POST(self):
        """Manejar login, registro y API admin"""
        print(f"[API POST] {self.path}")
        if self.path == '/login':
            self.handle_login()
        elif self.path == '/registrar':
            self.handle_registro()
        elif self.path == '/api/update-user':
            self.handle_update_user()
        elif self.path == '/api/delete-user':
            self.handle_delete_user()
        elif self.path == '/api/update-cita':
            self.handle_update_cita()
        elif self.path == '/api/delete-cita':
            self.handle_delete_cita()
        elif self.path == '/api/create-cita':
            self.handle_create_cita()
        elif self.path == '/api/update-patient-status':
            self.handle_update_patient_status()
        elif self.path == '/api/upload-study-result':
            self.handle_upload_study_result()
        elif self.path == '/api/update-study-status':
            self.handle_update_study_status()
        else:
            self.send_error(404)
    
    # ==============================================
    # FUNCIÓN PARA VER PDF DE CITA
    # ==============================================
    
    def handle_get_cita_pdf(self, cita_id):
        """Obtener el PDF de una cita específica"""
        print(f"[API] handle_get_cita_pdf para cita_id: {cita_id}")
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT documento_pdf, documento_nombre, documento_tipo
                FROM citas
                WHERE id_cita = %s AND documento_pdf IS NOT NULL
            """, (cita_id,))
            
            cita = cursor.fetchone()
            cursor.close()
            db.close()
            
            if not cita or not cita['documento_pdf']:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'PDF no encontrado'}).encode())
                return
            
            # Convertir el BLOB a base64 para enviarlo en JSON
            pdf_base64 = base64.b64encode(cita['documento_pdf']).decode('utf-8')
            
            response = {
                'success': True,
                'pdf_data': pdf_base64,
                'nombre': cita['documento_nombre'] or f'cita_{cita_id}.pdf',
                'tipo': cita['documento_tipo'] or 'application/pdf'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error obteniendo PDF de cita: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    # ==============================================
    # FUNCIONES PARA RESULTADOS DOCTOR
    # ==============================================
    def handle_get_doctor_studios(self, doctor_id):
        """Obtener estudios asignados a un doctor específico"""
        print(f"[API] handle_get_doctor_studios para doctor_id: {doctor_id}")
        try:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
        
            estado = query_params.get('estado', ['all'])[0] if query_params.get('estado') else 'all'
            tipo = query_params.get('tipo', ['all'])[0] if query_params.get('tipo') else 'all'
        
            print(f"[API] Parámetros: estado={estado}, tipo={tipo}")
        
            if '?' in doctor_id:
                doctor_id = doctor_id.split('?')[0]
        
            print(f"[API] Doctor ID limpio: {doctor_id}")
        
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
        
            query = """
                SELECT e.id_estudio as id, 
                    e.Pidpaciente as paciente_id,
                    p.nombre as paciente_nombre,
                    e.Diddoctor as doctor_id,
                    d.nombre as doctor_nombre,
                    e.tipo_estudio as tipo,
                    e.estudio_especifico,
                    DATE_FORMAT(e.fecha_realizacion, '%%Y-%%m-%%d') as fecha,
                    e.resultado,
                    e.estado,
                    e.archivo_url,
                    DATE_FORMAT(e.fecha_creacion, '%%Y-%%m-%%d %%H:%%i:%%s') as fecha_creacion
                FROM estudios e
                LEFT JOIN pacientes p ON e.Pidpaciente = p.Pidpaciente
                LEFT JOIN doctores d ON e.Diddoctor = d.Diddoctor
                WHERE e.Diddoctor = %s
            """
        
            params = [doctor_id]
            conditions = []
        
            if estado and estado != 'all' and estado != '':
                conditions.append("e.estado = %s")
                params.append(estado)
        
            if tipo and tipo != 'all' and tipo != '':
                conditions.append("e.tipo_estudio = %s")
                params.append(tipo)
        
            if conditions:
                query += " AND " + " AND ".join(conditions)
        
            query += " ORDER BY e.fecha_realizacion DESC"
        
            print(f"[API] Query ejecutada: {query}")
            cursor.execute(query, tuple(params))
            estudios = cursor.fetchall()
        
            print(f"[API] Número de estudios encontrados para doctor {doctor_id}: {len(estudios)}")
        
            cursor.close()
            db.close()
        
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(estudios).encode())
        
        except Exception as e:
            print(f"Error obteniendo estudios del doctor: {str(e)}")
            import traceback
            traceback.print_exc()
        
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_doctor_study_stats(self, doctor_id):
        """Obtener estadísticas de estudios de un doctor específico"""
        print(f"[API] handle_get_doctor_study_stats para doctor_id: {doctor_id}")
        try:
            if '?' in doctor_id:
                doctor_id = doctor_id.split('?')[0]
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM estudios 
                WHERE Diddoctor = %s
            """, (doctor_id,))
            result = cursor.fetchone()
            total_estudios = result['total'] if result and result['total'] is not None else 0
            
            cursor.execute("""
                SELECT COUNT(*) as completados 
                FROM estudios 
                WHERE Diddoctor = %s AND estado = 'completado'
            """, (doctor_id,))
            result = cursor.fetchone()
            estudios_completados = result['completados'] if result and result['completados'] is not None else 0
            
            cursor.execute("""
                SELECT COUNT(*) as pendientes 
                FROM estudios 
                WHERE Diddoctor = %s AND estado = 'pendiente'
            """, (doctor_id,))
            result = cursor.fetchone()
            estudios_pendientes = result['pendientes'] if result and result['pendientes'] is not None else 0
            
            cursor.execute("""
                SELECT COUNT(*) as revision 
                FROM estudios 
                WHERE Diddoctor = %s AND estado = 'revision'
            """, (doctor_id,))
            result = cursor.fetchone()
            estudios_revision = result['revision'] if result and result['revision'] is not None else 0
            
            cursor.close()
            db.close()
            
            stats = {
                'totalEstudios': total_estudios,
                'estudiosCompletados': estudios_completados,
                'estudiosPendientes': estudios_pendientes,
                'estudiosRevision': estudios_revision
            }
            
            print(f"[API] Estadísticas de estudios para doctor {doctor_id}: {stats}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
            
        except Exception as e:
            print(f"Error obteniendo estadísticas de estudios: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_upload_study_result(self):
        """Subir resultado de un estudio"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            estudio_id = data.get('estudio_id')
            resultado = data.get('resultado')
            estado = data.get('estado', 'completado')
            
            if not estudio_id:
                raise ValueError("Falta el ID del estudio")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("""
                UPDATE estudios 
                SET resultado = %s, estado = %s 
                WHERE id_estudio = %s
            """, (resultado, estado, estudio_id))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Resultado del estudio cargado correctamente'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error cargando resultado del estudio: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_update_study_status(self):
        """Actualizar estado de un estudio"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            estudio_id = data.get('estudio_id')
            nuevo_estado = data.get('estado')
            
            if not estudio_id or not nuevo_estado:
                raise ValueError("Faltan datos requeridos")
            
            estados_validos = ['pendiente', 'completado', 'revision']
            if nuevo_estado not in estados_validos:
                raise ValueError("Estado no válido")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("""
                UPDATE estudios 
                SET estado = %s 
                WHERE id_estudio = %s
            """, (nuevo_estado, estudio_id))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Estado del estudio actualizado correctamente'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error actualizando estado del estudio: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    # ==============================================
    # MANEJO DE CITAS PARA AGENDA
    # ==============================================
    
    def handle_get_doctor_appointments(self, doctor_id):
        """Obtener citas de un doctor específico"""
        print(f"[API] handle_get_doctor_appointments para doctor_id: {doctor_id}")
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            query = """
                SELECT c.id_cita as id, 
                       c.Pidpaciente as paciente_id,
                       p.nombre as paciente_nombre,
                       c.Diddoctor as doctor_id,
                       d.nombre as doctor_nombre,
                       c.tipo_estudio as tipo,
                       DATE_FORMAT(c.fecha, '%%Y-%%m-%%d') as fecha,
                       TIME_FORMAT(c.hora, '%%H:%%i') as hora,
                       c.estado,
                       c.notas,
                       c.estudio_especifico
                FROM citas c
                LEFT JOIN pacientes p ON c.Pidpaciente = p.Pidpaciente
                LEFT JOIN doctores d ON c.Diddoctor = d.Diddoctor
                WHERE c.Diddoctor = %s
                ORDER BY c.fecha DESC, c.hora DESC
            """
            
            cursor.execute(query, (doctor_id,))
            citas = cursor.fetchall()
            
            cursor.close()
            db.close()
            
            print(f"[API] Citas encontradas para doctor {doctor_id}: {len(citas)}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(citas).encode())
            
        except Exception as e:
            print(f"Error obteniendo citas del doctor: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_create_cita(self):
        """Crear una nueva cita"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            Pidpaciente = data.get('paciente_id')
            Diddoctor = data.get('doctor_id')
            tipo_estudio = data.get('tipo_estudio')
            estudio_especifico = data.get('estudio_especifico')
            fecha = data.get('fecha')
            hora = data.get('hora')
            notas = data.get('notas')
            
            if not all([Pidpaciente, Diddoctor, tipo_estudio, fecha, hora]):
                missing = []
                if not Pidpaciente: missing.append('paciente_id')
                if not Diddoctor: missing.append('doctor_id')
                if not tipo_estudio: missing.append('tipo_estudio')
                if not fecha: missing.append('fecha')
                if not hora: missing.append('hora')
                raise ValueError(f"Faltan campos obligatorios: {', '.join(missing)}")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            # Generar número de folio único
            cursor.execute("SELECT COUNT(*) as count FROM citas")
            result = cursor.fetchone()
            count = result[0] + 1
            numero_folio = f"FOL-{datetime.now().strftime('%Y%m%d')}-{str(count).zfill(4)}"
            
            cursor.execute("SELECT nombre FROM pacientes WHERE Pidpaciente = %s", (Pidpaciente,))
            paciente = cursor.fetchone()
            if not paciente:
                raise ValueError(f"Paciente con ID {Pidpaciente} no encontrado")
            
            cursor.execute("SELECT nombre FROM doctores WHERE Diddoctor = %s", (Diddoctor,))
            doctor = cursor.fetchone()
            if not doctor:
                raise ValueError(f"Doctor con ID {Diddoctor} no encontrado")
            
            cursor.execute("""
                INSERT INTO citas (numero_folio, Pidpaciente, Diddoctor, tipo_estudio, estudio_especifico, fecha, hora, estado, notas)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendiente', %s)
            """, (numero_folio, Pidpaciente, Diddoctor, tipo_estudio, estudio_especifico, fecha, hora, notas))
            
            cita_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO estudios (Pidpaciente, Diddoctor, tipo_estudio, estudio_especifico, fecha_realizacion, estado)
                VALUES (%s, %s, %s, %s, %s, 'pendiente')
            """, (Pidpaciente, Diddoctor, tipo_estudio, estudio_especifico, fecha))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Cita creada exitosamente',
                'cita_id': cita_id
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error creando cita: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_update_cita(self):
        """Actualizar una cita"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('citaId')
            fecha = data.get('fecha')
            hora = data.get('hora')
            estado = data.get('estado')
            notas = data.get('notas')
            tipo_estudio = data.get('tipo_estudio')
            
            if not cita_id:
                raise ValueError("Falta el ID de la cita")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            update_fields = []
            params = []
            
            if fecha:
                update_fields.append("fecha = %s")
                params.append(fecha)
            
            if hora:
                update_fields.append("hora = %s")
                params.append(hora)
            
            if estado:
                if estado not in ['pendiente', 'confirmada', 'completada', 'cancelada']:
                    raise ValueError("Estado no válido")
                update_fields.append("estado = %s")
                params.append(estado)
            
            if notas is not None:
                update_fields.append("notas = %s")
                params.append(notas)
            
            if tipo_estudio:
                update_fields.append("tipo_estudio = %s")
                params.append(tipo_estudio)
            
            if update_fields:
                query = f"UPDATE citas SET {', '.join(update_fields)} WHERE id_cita = %s"
                params.append(cita_id)
                
                cursor.execute(query, params)
                db.commit()
            
            cursor.close()
            db.close()
            
            response = {'success': True, 'message': 'Cita actualizada correctamente'}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error actualizando cita: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    # ==============================================
    # FUNCIONES PARA ADMIN (MODIFICADAS)
    # ==============================================
    
    def handle_admin_stats(self):
        """Obtener estadísticas para el panel de admin (SOLO DOCTORES)"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("SELECT COUNT(*) as total FROM doctores WHERE activo = TRUE")
            total_doctores = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM citas WHERE fecha = CURDATE()")
            citas_hoy = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM estudios WHERE estado = 'pendiente'")
            estudios_pendientes = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM estudios WHERE estado = 'completado' AND MONTH(fecha_creacion) = MONTH(CURDATE())")
            estudios_completados = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(*) as total FROM doctores WHERE fecha_registro >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
            nuevos_doctores = cursor.fetchone()['total']
            
            cursor.execute("SELECT COUNT(DISTINCT tipo_estudio) as total FROM estudios")
            tipos_estudios = cursor.fetchone()['total']
            
            cursor.close()
            db.close()
            
            stats = {
                'totalDoctores': total_doctores,
                'citasHoy': citas_hoy,
                'estudiosPendientes': estudios_pendientes,
                'estudiosCompletados': estudios_completados,
                'nuevosDoctores': nuevos_doctores,
                'tiposEstudios': tipos_estudios
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
            
        except Exception as e:
            print(f"Error en stats: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_admin_activity(self):
        """Obtener actividad reciente"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT usuario_id, tipo_usuario, titulo as accion, 
                       DATE_FORMAT(fecha_creacion, '%%Y-%%m-%%d %%H:%%i') as fecha,
                       mensaje as detalles
                FROM notificaciones 
                ORDER BY fecha_creacion DESC 
                LIMIT 10
            """)
            actividades = cursor.fetchall()
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(actividades).encode())
            
        except Exception as e:
            print(f"Error en actividad: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    # ==============================================
    # FUNCIONES PARA DOCTORES (MODIFICADAS)
    # ==============================================
    
    def handle_get_doctores(self):
        """Obtener lista de doctores con datos del consultorio"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT d.Diddoctor as id, d.nombre, d.especialidad, d.email, d.telefono, 
                       d.telefono_consultorio, d.direccion_consultorio, d.activo,
                       DATE_FORMAT(d.fecha_registro, '%%Y-%%m-%%d') as fecha_registro,
                       (SELECT COUNT(*) FROM pacientes p WHERE p.doctor_asignado = d.Diddoctor) as total_pacientes
                FROM doctores d
                ORDER BY d.Diddoctor ASC
            """)
            doctores = cursor.fetchall()
            
            for doctor in doctores:
                doctor['pacientes'] = doctor['total_pacientes']
                doctor['activo'] = bool(doctor['activo'])
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(doctores).encode())
            
        except Exception as e:
            print(f"Error obteniendo doctores: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_doctor(self, doctor_id):
        """Obtener un doctor específico con datos del consultorio"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT d.Diddoctor as id, d.nombre, d.especialidad, d.email, d.telefono, 
                       d.telefono_consultorio, d.direccion_consultorio, d.usuario, d.activo,
                       DATE_FORMAT(d.fecha_registro, '%%Y-%%m-%%d') as fecha_registro
                FROM doctores d
                WHERE d.Diddoctor = %s
            """, (doctor_id,))
            
            doctor = cursor.fetchone()
            
            if not doctor:
                cursor.close()
                db.close()
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Doctor no encontrado'}).encode())
                return
            
            doctor['activo'] = bool(doctor['activo'])
            
            cursor.execute("""
                SELECT p.Pidpaciente as id, p.nombre, p.edad, p.estado_paciente
                FROM pacientes p
                WHERE p.doctor_asignado = %s
            """, (doctor_id,))
            pacientes = cursor.fetchall()
            doctor['pacientes_asignados'] = pacientes
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(doctor).encode())
            
        except Exception as e:
            print(f"Error obteniendo doctor {doctor_id}: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_usuario(self, user_id, tipo):
        """Obtener usuario específico (MODIFICADO - SOLO DOCTORES)"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            if tipo == 'doctor':
                cursor.execute("""
                    SELECT d.Diddoctor as id, d.nombre, d.especialidad, d.email, d.telefono, 
                           d.telefono_consultorio, d.direccion_consultorio, d.usuario, d.activo,
                           DATE_FORMAT(d.fecha_registro, '%Y-%m-%d') as fecha_registro
                    FROM doctores d
                    WHERE d.Diddoctor = %s
                """, (user_id,))
            else:
                cursor.close()
                db.close()
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Tipo de usuario no válido'}).encode())
                return
            
            usuario = cursor.fetchone()
            
            if not usuario:
                cursor.close()
                db.close()
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Usuario no encontrado'}).encode())
                return
            
            usuario['activo'] = bool(usuario['activo'])
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(usuario).encode())
            
        except Exception as e:
            print(f"Error obteniendo usuario {user_id} ({tipo}): {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_update_user(self):
        """Actualizar usuario (MODIFICADO - SOLO DOCTORES con datos de consultorio)"""
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
                
                if email:
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
                
                if password:
                    update_fields.append("contrasena = %s")
                    params.append(password)
                
            else:
                raise ValueError("Tipo de usuario no válido")
            
            if update_fields:
                query = f"UPDATE {table} SET {', '.join(update_fields)} WHERE {id_field} = %s"
                params.append(user_id)
                
                cursor.execute(query, params)
                db.commit()
            
            cursor.close()
            db.close()
            
            response = {'success': True, 'message': 'Doctor actualizado correctamente'}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error actualizando usuario: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_delete_user(self):
        """Eliminar usuario (SOLO DOCTORES)"""
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
                table = 'doctores'
                id_field = 'Diddoctor'
            else:
                raise ValueError("Tipo de usuario no válido")
            
            cursor.execute(f"DELETE FROM {table} WHERE {id_field} = %s", (user_id,))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {'success': True, 'message': 'Doctor eliminado correctamente'}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error eliminando doctor: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    # ==============================================
    # RESTA DE FUNCIONES
    # ==============================================
    
    def handle_login(self):
        """Manejar el inicio de sesión"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = parse_qs(post_data.decode())
        
        username = data.get('username', [''])[0]
        password = data.get('password', [''])[0]
        
        print(f"[LOGIN] Intento de login: usuario={username}")
        
        try:
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
                print(f"[LOGIN] Usuario encontrado: admin {user_id}")
            
            if not usuario_encontrado:
                cursor.execute("SELECT * FROM doctores WHERE usuario = %s AND contrasena = %s", 
                              (username, password))
                doctor = cursor.fetchone()
                if doctor:
                    usuario_encontrado = True
                    tipo_usuario = 'doctor'
                    user_id = doctor['Diddoctor']
                    user_name = doctor['nombre']
                    print(f"[LOGIN] Usuario encontrado: doctor {user_id}")
            
            if not usuario_encontrado:
                cursor.execute("SELECT * FROM pacientes WHERE usuario = %s AND contrasena = %s", 
                              (username, password))
                paciente = cursor.fetchone()
                if paciente:
                    usuario_encontrado = True
                    tipo_usuario = 'paciente'
                    user_id = paciente['Pidpaciente']
                    user_name = paciente['nombre']
                    print(f"[LOGIN] Usuario encontrado: paciente {user_id}")
            
            cursor.close()
            db.close()
            
            if usuario_encontrado:
                if tipo_usuario == 'doctor':
                    redirect_url = f'/dashboard?doctor_id={user_id}'
                elif tipo_usuario == 'paciente':
                    redirect_url = '/paciente'
                else:
                    redirect_url = '/admin'
                
                response = {
                    'success': True,
                    'tipo': tipo_usuario,
                    'user_id': user_id,
                    'user_name': user_name,
                    'redirect': redirect_url
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            else:
                response = {'success': False, 'message': 'Credenciales incorrectas'}
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            print(f"Error en login: {str(e)}")
            response = {'success': False, 'message': 'Error del servidor'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_get_doctor_info(self, doctor_id):
        """Obtener información básica del doctor"""
        print(f"[API] handle_get_doctor_info para doctor_id: {doctor_id}")
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT Diddoctor as id, nombre, especialidad, email, telefono, usuario,
                       telefono_consultorio, direccion_consultorio
                FROM doctores 
                WHERE Diddoctor = %s
            """, (doctor_id,))
            
            doctor = cursor.fetchone()
            
            if not doctor:
                cursor.close()
                db.close()
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Doctor no encontrado'}).encode())
                return
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(doctor).encode())
            
        except Exception as e:
            print(f"Error obteniendo información del doctor: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_doctor_patients(self):
        """Obtener pacientes asignados a un doctor específico"""
        try:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            doctor_id = query_params.get('doctor_id', [None])[0]
            filter_type = query_params.get('filter', ['all'])[0]
            
            if not doctor_id:
                raise ValueError("Se requiere el ID del doctor")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            query = """
                SELECT p.Pidpaciente as id, p.nombre, p.edad, p.email, p.telefono,
                       p.estado_paciente as estado, 
                       DATE_FORMAT(p.fecha_registro, '%%Y-%%m-%%d') as fecha_registro,
                       p.doctor_asignado,
                       d.nombre as doctor_nombre
                FROM pacientes p
                LEFT JOIN doctores d ON p.doctor_asignado = d.Diddoctor
                WHERE p.doctor_asignado = %s AND p.activo = TRUE
            """
            
            params = [doctor_id]
            
            if filter_type == 'citas_hoy':
                query += """
                    AND p.Pidpaciente IN (
                        SELECT DISTINCT Pidpaciente 
                        FROM citas 
                        WHERE Diddoctor = %s AND fecha = CURDATE()
                        AND estado IN ('pendiente', 'confirmada')
                    )
                """
                params.append(doctor_id)
            elif filter_type == 'estudios_pendientes':
                query += """
                    AND p.Pidpaciente IN (
                        SELECT DISTINCT Pidpaciente 
                        FROM estudios 
                        WHERE Diddoctor = %s AND estado = 'pendiente'
                    )
                """
                params.append(doctor_id)
            elif filter_type == 'nuevos':
                query += " AND p.fecha_registro >= DATE_SUB(CURDATE(), INTERVAL 5 DAY)"
            elif filter_type == 'cronicos':
                query += " AND p.estado_paciente = 'cronico'"
            
            query += " ORDER BY p.nombre ASC"
            
            cursor.execute(query, params)
            pacientes = cursor.fetchall()
            
            for paciente in pacientes:
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM citas 
                    WHERE Pidpaciente = %s AND fecha = CURDATE()
                    AND estado IN ('pendiente', 'confirmada')
                """, (paciente['id'],))
                resultado = cursor.fetchone()
                paciente['citas_hoy'] = resultado['count'] if resultado else 0
                
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM estudios 
                    WHERE Pidpaciente = %s AND estado = 'pendiente'
                """, (paciente['id'],))
                resultado = cursor.fetchone()
                paciente['estudios_pendientes'] = resultado['count'] if resultado else 0
                
                cursor.execute("""
                    SELECT DATE_FORMAT(fecha, '%%Y-%%m-%%d') as fecha, tipo_estudio 
                    FROM citas 
                    WHERE Pidpaciente = %s 
                    ORDER BY fecha DESC 
                    LIMIT 1
                """, (paciente['id'],))
                ultima_cita = cursor.fetchone()
                paciente['ultima_cita'] = ultima_cita
                
                nombre_parts = paciente['nombre'].split()
                iniciales = ''
                for part in nombre_parts[:2]:
                    if part:
                        iniciales += part[0].upper()
                if len(iniciales) < 2 and len(nombre_parts) > 0:
                    iniciales = nombre_parts[0][0].upper() * 2
                paciente['iniciales'] = iniciales
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(pacientes).encode())
            
        except Exception as e:
            print(f"Error obteniendo pacientes del doctor: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_patient_citas(self, paciente_id):
        """Obtener citas de un paciente específico"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT c.id_cita as id, 
                       c.tipo_estudio as tipo,
                       DATE_FORMAT(c.fecha, '%%Y-%%m-%%d') as fecha,
                       TIME_FORMAT(c.hora, '%%H:%%i') as hora,
                       c.estado,
                       c.notas,
                       d.nombre as doctor_nombre
                FROM citas c
                LEFT JOIN doctores d ON c.Diddoctor = d.Diddoctor
                WHERE c.Pidpaciente = %s AND c.fecha < CURDATE()
                ORDER BY c.fecha DESC
                LIMIT 10
            """, (paciente_id,))
            citas_pasadas = cursor.fetchall()
            
            cursor.execute("""
                SELECT c.id_cita as id, 
                       c.tipo_estudio as tipo,
                       DATE_FORMAT(c.fecha, '%%Y-%%m-%%d') as fecha,
                       TIME_FORMAT(c.hora, '%%H:%%i') as hora,
                       c.estado,
                       c.notas,
                       d.nombre as doctor_nombre
                FROM citas c
                LEFT JOIN doctores d ON c.Diddoctor = d.Diddoctor
                WHERE c.Pidpaciente = %s AND c.fecha >= CURDATE()
                ORDER BY c.fecha ASC
            """, (paciente_id,))
            citas_futuras = cursor.fetchall()
            
            cursor.close()
            db.close()
            
            response = {
                'pasadas': citas_pasadas,
                'futuras': citas_futuras
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error obteniendo citas del paciente: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_update_patient_status(self):
        """Actualizar estado de un paciente (solo doctores)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            paciente_id = data.get('paciente_id')
            nuevo_estado = data.get('estado')
            
            if not paciente_id or not nuevo_estado:
                raise ValueError("Faltan datos requeridos")
            
            estados_validos = ['agudo', 'cronico', 'seguimiento', 'recuperado']
            if nuevo_estado not in estados_validos:
                raise ValueError("Estado no válido")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("""
                UPDATE pacientes 
                SET estado_paciente = %s 
                WHERE Pidpaciente = %s
            """, (nuevo_estado, paciente_id))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': 'Estado del paciente actualizado correctamente'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error actualizando estado del paciente: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_dashboard_doctor_data(self, doctor_id):
        """Obtener todos los datos del dashboard para un doctor"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
        
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM pacientes 
                WHERE doctor_asignado = %s AND activo = TRUE
            """, (doctor_id,))
            result = cursor.fetchone()
            total_pacientes = result['total'] if result else 0
        
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM citas 
                WHERE Diddoctor = %s AND fecha = CURDATE() 
                AND estado IN ('confirmada', 'pendiente')
            """, (doctor_id,))
            result = cursor.fetchone()
            citas_hoy = result['total'] if result else 0
        
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM estudios 
                WHERE Diddoctor = %s AND estado = 'pendiente'
            """, (doctor_id,))
            result = cursor.fetchone()
            estudios_pendientes = result['total'] if result else 0
        
            cursor.execute("""
                SELECT c.id_cita, c.tipo_estudio, c.estado, TIME_FORMAT(c.hora, '%H:%i') as hora,
                    p.nombre as paciente_nombre
                FROM citas c
                JOIN pacientes p ON c.Pidpaciente = p.Pidpaciente
                WHERE c.Diddoctor = %s AND c.fecha = CURDATE()
                AND c.estado IN ('confirmada', 'pendiente')
                ORDER BY c.hora ASC
            """, (doctor_id,))
            citas_detalle = cursor.fetchall()
        
            cursor.execute("""
                SELECT Diddoctor as id, nombre, especialidad, email, telefono, usuario,
                       telefono_consultorio, direccion_consultorio
                FROM doctores 
                WHERE Diddoctor = %s
            """, (doctor_id,))
            doctor_info = cursor.fetchone()
        
            cursor.close()
            db.close()
        
            response = {
                'success': True,
                'doctor': doctor_info,
                'stats': {
                    'totalPacientes': total_pacientes,
                    'citasHoy': citas_hoy,
                    'estudiosPendientes': estudios_pendientes
                },
                'citasHoy': citas_detalle
            }
        
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        
        except Exception as e:
            print(f"Error obteniendo datos dashboard: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def handle_doctor_dashboard_stats(self):
        """Manejar estadísticas del dashboard del doctor"""
        try:
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            doctor_id = query_params.get('doctor_id', [None])[0]
        
            if not doctor_id:
                raise ValueError("Se requiere el ID del doctor")
        
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
        
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM pacientes WHERE doctor_asignado = %s AND activo = TRUE) as total_pacientes,
                    (SELECT COUNT(*) FROM citas WHERE Diddoctor = %s AND fecha = CURDATE() 
                    AND estado IN ('confirmada', 'pendiente')) as citas_hoy,
                    (SELECT COUNT(*) FROM estudios WHERE Diddoctor = %s AND estado = 'pendiente') as estudios_pendientes
            """, (doctor_id, doctor_id, doctor_id))
        
            stats = cursor.fetchone()
        
            cursor.execute("SELECT nombre FROM doctores WHERE Diddoctor = %s", (doctor_id,))
            doctor = cursor.fetchone()
        
            cursor.close()
            db.close()
        
            response = {
                'success': True,
                'doctor': doctor,
                'stats': stats
            }
        
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        
        except Exception as e:
            print(f"Error en doctor dashboard stats: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_doctor_stats(self, doctor_id):
        """Obtener estadísticas específicas para un doctor"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("SELECT COUNT(*) as total FROM pacientes WHERE doctor_asignado = %s", (doctor_id,))
            result_pacientes = cursor.fetchone()
            total_pacientes = result_pacientes['total'] if result_pacientes else 0
            
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM citas 
                WHERE Diddoctor = %s AND fecha = CURDATE() 
                AND estado IN ('confirmada', 'pendiente')
            """, (doctor_id,))
            result_citas = cursor.fetchone()
            citas_hoy = result_citas['total'] if result_citas else 0
            
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM estudios 
                WHERE Diddoctor = %s AND estado = 'pendiente'
            """, (doctor_id,))
            result_estudios = cursor.fetchone()
            estudios_pendientes = result_estudios['total'] if result_estudios else 0
            
            cursor.execute("""
                SELECT c.id_cita, c.tipo_estudio, c.estado, TIME_FORMAT(c.hora, '%%H:%%i') as hora,
                       p.nombre as paciente_nombre
                FROM citas c
                JOIN pacientes p ON c.Pidpaciente = p.Pidpaciente
                WHERE c.Diddoctor = %s AND c.fecha = CURDATE()
                AND c.estado IN ('confirmada', 'pendiente')
                ORDER BY c.hora ASC
            """, (doctor_id,))
            citas_detalle = cursor.fetchall()
            
            cursor.close()
            db.close()
            
            stats = {
                'totalPacientes': total_pacientes,
                'citasHoy': citas_hoy,
                'estudiosPendientes': estudios_pendientes,
                'citasDetalle': citas_detalle,
                'doctorId': doctor_id
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
            
        except Exception as e:
            print(f"Error en stats doctor: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_citas(self):
        """Obtener lista de citas para admin - MODIFICADO para mostrar solo N° Folio, Paciente, Doctor, Fecha, Hora"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            filter_type = query_params.get('filter', ['all'])[0]
            
            # Construir query base
            query = """
                SELECT c.id_cita as id, 
                       c.numero_folio as folio,
                       p.nombre as paciente_nombre,
                       d.nombre as doctor_nombre,
                       DATE_FORMAT(c.fecha, '%%Y-%%m-%%d') as fecha,
                       TIME_FORMAT(c.hora, '%%H:%%i') as hora,
                       CASE 
                           WHEN c.documento_pdf IS NOT NULL THEN 1 
                           ELSE 0 
                       END as tiene_pdf
                FROM citas c
                LEFT JOIN pacientes p ON c.Pidpaciente = p.Pidpaciente
                LEFT JOIN doctores d ON c.Diddoctor = d.Diddoctor
            """
            
            # Aplicar filtros
            if filter_type == 'today':
                query += " WHERE c.fecha = CURDATE()"
            else:
                query += " WHERE 1=1"
            
            query += " ORDER BY c.fecha DESC, c.hora DESC"
            
            cursor.execute(query)
            citas = cursor.fetchall()
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(citas).encode())
            
        except Exception as e:
            print(f"Error obteniendo citas: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_cita(self, cita_id):
        """Obtener una cita específica"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT c.id_cita as id, 
                       c.numero_folio as folio,
                       c.Pidpaciente as paciente_id,
                       p.nombre as paciente_nombre,
                       c.Diddoctor as doctor_id,
                       d.nombre as doctor_nombre,
                       c.tipo_estudio as tipo,
                       DATE_FORMAT(c.fecha, '%%Y-%%m-%%d') as fecha,
                       TIME_FORMAT(c.hora, '%%H:%%i') as hora,
                       c.estado,
                       c.notas,
                       CASE 
                           WHEN c.documento_pdf IS NOT NULL THEN 1 
                           ELSE 0 
                       END as tiene_pdf,
                       c.documento_nombre,
                       DATE_FORMAT(c.fecha_creacion, '%%Y-%%m-%%d %%H:%%i') as fecha_creacion
                FROM citas c
                LEFT JOIN pacientes p ON c.Pidpaciente = p.Pidpaciente
                LEFT JOIN doctores d ON c.Diddoctor = d.Diddoctor
                WHERE c.id_cita = %s
            """, (cita_id,))
            
            cita = cursor.fetchone()
            
            if not cita:
                cursor.close()
                db.close()
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Cita no encontrada'}).encode())
                return
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(cita).encode())
            
        except Exception as e:
            print(f"Error obteniendo cita {cita_id}: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_estudios(self):
        """Obtener lista de estudios"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            doctor_id = query_params.get('doctor_id', [None])[0]
            estado = query_params.get('estado', [None])[0]
            
            query = """
                SELECT e.id_estudio as id, 
                       e.Pidpaciente as paciente_id,
                       p.nombre as paciente_nombre,
                       e.Diddoctor as doctor_id,
                       d.nombre as doctor_nombre,
                       e.tipo_estudio as tipo,
                       DATE_FORMAT(e.fecha_realizacion, '%%Y-%%m-%%d') as fecha,
                       e.resultado,
                       e.estado,
                       DATE_FORMAT(e.fecha_creacion, '%%Y-%%m-%%d %%H:%%i') as fecha_creacion
                FROM estudios e
                LEFT JOIN pacientes p ON e.Pidpaciente = p.Pidpaciente
                LEFT JOIN doctores d ON e.Diddoctor = d.Diddoctor
                WHERE 1=1
            """
            
            params = []
            
            if doctor_id:
                query += " AND e.Diddoctor = %s"
                params.append(doctor_id)
            
            if estado:
                query += " AND e.estado = %s"
                params.append(estado)
            
            query += " ORDER BY e.fecha_realizacion DESC LIMIT 50"
            
            cursor.execute(query, params)
            estudios = cursor.fetchall()
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(estudios).encode())
            
        except Exception as e:
            print(f"Error obteniendo estudios: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_delete_cita(self):
        """Eliminar una cita"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode())
            
            cita_id = data.get('citaId')
            
            if not cita_id:
                raise ValueError("Falta el ID de la cita")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            cursor.execute("DELETE FROM citas WHERE id_cita = %s", (cita_id,))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {'success': True, 'message': 'Cita eliminada correctamente'}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error eliminando cita: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    def handle_registro(self):
        """Manejar el registro de nuevos doctores"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = parse_qs(post_data.decode())
        
        try:
            # Obtener datos del formulario
            nombre_completo = data.get('nombre', [''])[0] + " " + data.get('apellidos', [''])[0]
            usuario = data.get('usuario', [''])[0]
            contrasena = data.get('contrasena', [''])[0]
            especialidad = data.get('especialidad', [''])[0]
            email = data.get('correo', [''])[0]
            telefono = data.get('telefono', [''])[0]
            direccion_consultorio = data.get('direccion_consultorio', [''])[0]
            telefono_consultorio = data.get('telefono_consultorio', [''])[0]
            
            # Validar campos obligatorios
            if not all([nombre_completo, usuario, contrasena, especialidad, email, telefono, direccion_consultorio, telefono_consultorio]):
                missing = []
                if not nombre_completo: missing.append('nombre completo')
                if not usuario: missing.append('usuario')
                if not contrasena: missing.append('contraseña')
                if not especialidad: missing.append('especialidad')
                if not email: missing.append('email')
                if not telefono: missing.append('teléfono')
                if not direccion_consultorio: missing.append('dirección del consultorio')
                if not telefono_consultorio: missing.append('teléfono del consultorio')
                raise ValueError(f"Faltan campos obligatorios: {', '.join(missing)}")
            
            db = self.connect_db()
            cursor = db.cursor()
            
            # Verificar si el usuario ya existe
            cursor.execute("SELECT usuario FROM doctores WHERE usuario = %s UNION SELECT usuario FROM pacientes WHERE usuario = %s UNION SELECT usuario FROM administradores WHERE usuario = %s", 
                          (usuario, usuario, usuario))
            if cursor.fetchone():
                raise ValueError("El nombre de usuario ya está en uso")
            
            # Verificar si el email ya existe
            cursor.execute("SELECT email FROM doctores WHERE email = %s UNION SELECT email FROM pacientes WHERE email = %s UNION SELECT email FROM administradores WHERE email = %s", 
                          (email, email, email))
            if cursor.fetchone():
                raise ValueError("El correo electrónico ya está registrado")
            
            # Generar nuevo ID para doctor
            cursor.execute("SELECT MAX(CAST(SUBSTRING(Diddoctor, 2) AS UNSIGNED)) as max_id FROM doctores")
            result = cursor.fetchone()
            max_id = result[0] if result[0] else 0
            nuevo_id = f"D{str(max_id + 1).zfill(3)}"
            
            # Insertar nuevo doctor con todos los campos
            cursor.execute("""
                INSERT INTO doctores (
                    Diddoctor, 
                    nombre, 
                    usuario, 
                    contrasena, 
                    especialidad, 
                    email, 
                    telefono, 
                    direccion_consultorio, 
                    telefono_consultorio,
                    fecha_registro,
                    activo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1)
            """, (
                nuevo_id, 
                nombre_completo, 
                usuario, 
                contrasena, 
                especialidad, 
                email, 
                telefono, 
                direccion_consultorio, 
                telefono_consultorio
            ))
            
            # Crear notificación de bienvenida
            cursor.execute("""
                INSERT INTO notificaciones (usuario_id, tipo_usuario, titulo, mensaje)
                VALUES (%s, 'doctor', 'Bienvenido al sistema', %s)
            """, (nuevo_id, f'Bienvenido Dr. {nombre_completo}. Su cuenta ha sido creada exitosamente.'))
            
            db.commit()
            cursor.close()
            db.close()
            
            response = {
                'success': True,
                'message': f'Doctor registrado exitosamente. Su ID es: {nuevo_id}',
                'redirect': '/'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except ValueError as ve:
            response = {'success': False, 'message': str(ve)}
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error en registro: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
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
            print("💡 Solución: Asegúrate de que:")
            print("   1. XAMPP esté corriendo")
            print("   2. MySQL esté iniciado")
            print("   3. La base de datos 'radiologia_db' exista")
            print("   4. Ejecutes tu archivo DB.sql en phpMyAdmin")
            raise

# Configuración del servidor
PORT = 8000

print("=" * 60)
print("🚀 SERVIDOR RADIOLOGÍA MÉDICA")
print("=" * 60)
print(f"📊 Accede a: http://localhost:{PORT}")
print("\n👥 Usuarios de prueba:")
print("   • Doctor:    dr.rodriguez / doctor123")
print("   • Paciente:  carlos.lopez / paciente123")
print("   • Admin:     admin / admin123")
print("\n📝 Registro disponible en: /registro")
print("👑 Panel de administración: /admin")
print("=" * 60)

if not os.path.exists('templates'):
    os.makedirs('templates')
    print("📁 Carpeta 'templates' creada")
    print("   ⚠️  Mueve tus archivos HTML a la carpeta 'templates'")

try:
    server = HTTPServer(('', PORT), CustomHandler)
    print("\n✅ Servidor listo. Presiona Ctrl+C para detenerlo.")
    print("📡 Escuchando en puerto", PORT)
    server.serve_forever()
except KeyboardInterrupt:
    print("\n⏹️  Servidor detenido")
except Exception as e:
    print(f"\n❌ Error al iniciar el servidor: {e}")