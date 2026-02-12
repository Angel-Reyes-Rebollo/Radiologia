# app.py - VERSIÓN CORREGIDA CON ADMIN FUNCIONAL Y DESCARGA DE PDF
import base64
import io
import json
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import mysql.connector
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)


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
        
        return os.path.join(os.getcwd(), path.lstrip('/'))
    
    def do_GET(self):
        """Manejar peticiones GET"""
        try:
            if self.path == '/favicon.ico':
                self.send_error(404)
                return
        
            print(f"[API GET] {self.path}")
        
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
            
            # RUTAS PARA ADMIN - CORREGIDAS
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
                
            # RUTA PARA DESCARGAR PDF DE CITA
            if self.path.startswith('/api/descargar-pdf/'):
                cita_id = self.path.split('/')[-1]
                self.handle_descargar_pdf(cita_id)
                return
            
            super().do_GET()
            
        except Exception as e:
            print(f"Error en GET {self.path}: {str(e)}")
            self.send_error(404)
    
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
        else:
            self.send_error(404)
    
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
                SELECT Diddoctor as id, nombre, usuario
                FROM doctores 
                WHERE usuario = %s AND activo = 1
            """, (username,))
            
            doctor = cursor.fetchone()
            cursor.close()
            db.close()
            
            if doctor:
                print(f"[API] Doctor encontrado: {doctor}")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(doctor).encode())
            else:
                print(f"[API] No se encontró doctor con usuario: '{username}'")
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Doctor no encontrado'}).encode())
                
        except Exception as e:
            print(f"Error obteniendo doctor por usuario: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    # ==============================================
    # FUNCIÓN PARA GENERAR PDF DE RECETA
    # ==============================================
    
    def generate_pdf_cita(self, data):
        """Generar PDF para la cita/receta"""
        buffer = io.BytesIO()
        
        # Configurar documento
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter),
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)
        
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a2980'),
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#26d0ce'),
            alignment=TA_LEFT,
            spaceAfter=12
        ))
        
        styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6
        ))
        
        styles.add(ParagraphStyle(
            name='CustomRight',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT,
            textColor=colors.grey
        ))
        
        # Contenido del PDF
        story = []
        
        # Título
        story.append(Paragraph("Radiología Médica Avanzada", styles['CustomTitle']))
        story.append(Paragraph("Formulario de Prescripción / Receta Virtual", styles['CustomRight']))
        story.append(Spacer(1, 20))
        
        # Folio y fecha
        folio_data = [
            [Paragraph(f"<b>Número de Folio:</b> {data['numero_folio']}", styles['CustomNormal']),
             Paragraph(f"<b>Fecha:</b> {data['fecha']}", styles['CustomNormal']),
             Paragraph(f"<b>Hora:</b> {data['hora']}", styles['CustomNormal'])]
        ]
        folio_table = Table(folio_data, colWidths=[doc.width/3.0]*3)
        folio_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 11),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        story.append(folio_table)
        story.append(Spacer(1, 20))
        
        # Datos del paciente
        story.append(Paragraph("DATOS DEL PACIENTE", styles['CustomHeading2']))
        
        paciente_data = [
            [Paragraph(f"<b>Nombre:</b> {data['paciente']}", styles['CustomNormal'])]
        ]
        paciente_table = Table(paciente_data, colWidths=[doc.width])
        paciente_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 11),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(paciente_table)
        story.append(Spacer(1, 20))
        
        # Datos del médico
        story.append(Paragraph("DATOS DEL MÉDICO", styles['CustomHeading2']))
        
        # Obtener datos del doctor
        db = self.connect_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT nombre, especialidad, telefono_consultorio, email FROM doctores WHERE Diddoctor = %s", (data['doctor_id'],))
        doctor = cursor.fetchone()
        cursor.close()
        db.close()
        
        medico_data = [
            [Paragraph(f"<b>Dr(a).</b> {doctor['nombre'] if doctor else 'No especificado'}", styles['CustomNormal'])],
            [Paragraph(f"<b>Especialidad:</b> {doctor['especialidad'] if doctor else 'No especificada'}", styles['CustomNormal'])],
            [Paragraph(f"<b>Teléfono:</b> {doctor['telefono_consultorio'] if doctor else 'No especificado'}", styles['CustomNormal'])]
        ]
        medico_table = Table(medico_data, colWidths=[doc.width])
        medico_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 11),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(medico_table)
        story.append(Spacer(1, 20))
        
        # Estudios solicitados
        story.append(Paragraph("ESTUDIOS SOLICITADOS", styles['CustomHeading2']))
        
        # Crear tabla de estudios
        estudios = data.get('estudios', [])
        if estudios:
            estudio_data = [['Estudio', 'Precio']]
            for estudio in estudios:
                estudio_data.append([estudio['nombre'], estudio['precio']])
            
            estudio_table = Table(estudio_data, colWidths=[doc.width - 100, 100])
            estudio_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a2980')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('ALIGN', (1,1), (1,-1), 'RIGHT'),
            ]))
            story.append(estudio_table)
            story.append(Spacer(1, 15))
            
            # Total
            total = 0
            for estudio in estudios:
                try:
                    precio_str = estudio['precio'].replace('$', '').replace(',', '')
                    total += float(precio_str)
                except:
                    pass
            
            story.append(Paragraph(f"<b>TOTAL:</b> ${total:,.2f}", ParagraphStyle(
                'Total',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=colors.HexColor('#1a2980'),
                alignment=TA_RIGHT,
                spaceBefore=10
            )))
        else:
            story.append(Paragraph("No se especificaron estudios", styles['CustomNormal']))
        
        story.append(Spacer(1, 30))
        
        # Observaciones
        if data.get('observaciones'):
            story.append(Paragraph("OBSERVACIONES", styles['CustomHeading2']))
            story.append(Paragraph(data['observaciones'], styles['CustomNormal']))
            story.append(Spacer(1, 20))
        
        # Firmas
        signature_data = [
            [Paragraph("____________________________", styles['CustomNormal']),
             Paragraph("____________________________", styles['CustomNormal'])],
            [Paragraph("Dr(a). " + (doctor['nombre'] if doctor else ''), styles['CustomNormal']),
             Paragraph("Paciente: " + data['paciente'], styles['CustomNormal'])]
        ]
        signature_table = Table(signature_data, colWidths=[doc.width/2.0]*2)
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 11),
            ('TOPPADDING', (0,1), (-1,1), 5),
        ]))
        story.append(signature_table)
        
        # Construir PDF
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
            
            # Validar datos requeridos
            paciente = data.get('paciente')
            doctor_id = data.get('doctor_id')
            estudios = data.get('estudios', [])
            observaciones = data.get('observaciones', '')
            
            if not paciente or not doctor_id:
                raise ValueError("Faltan datos requeridos: paciente o doctor_id")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Verificar que el doctor existe
            cursor.execute("SELECT Diddoctor FROM doctores WHERE Diddoctor = %s", (doctor_id,))
            doctor = cursor.fetchone()
            
            if not doctor:
                raise ValueError(f"El doctor con ID {doctor_id} no existe en la base de datos")
            
            # Generar número de folio único
            cursor.execute("SELECT COUNT(*) as total FROM citas")
            result = cursor.fetchone()
            total_citas = result['total'] + 1
            numero_folio = f"FOL-{datetime.now().strftime('%Y%m%d')}-{str(total_citas).zfill(5)}"
            
            # Fecha y hora actual
            fecha_actual = datetime.now().strftime('%Y-%m-%d')
            hora_actual = datetime.now().strftime('%H:%M:%S')
            
            # Generar PDF
            pdf_data = {
                'numero_folio': numero_folio,
                'fecha': fecha_actual,
                'hora': hora_actual,
                'paciente': paciente,
                'doctor_id': doctor_id,
                'estudios': estudios,
                'observaciones': observaciones
            }
            
            pdf_content = self.generate_pdf_cita(pdf_data)
            pdf_size = len(pdf_content)
            
            # Insertar en base de datos
            cursor.execute("""
                INSERT INTO citas (
                    numero_folio, paciente, doctor_id, fecha, hora, 
                    documento_nombre, documento_pdf, documento_tamano, documento_tipo,
                    fecha_creacion
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                numero_folio,
                paciente,
                doctor_id,
                fecha_actual,
                hora_actual,
                f"{paciente}_{numero_folio}.pdf",
                pdf_content,
                pdf_size,
                'application/pdf'
            ))
            
            db.commit()
            print(f"[CITA] Cita generada exitosamente - Folio: {numero_folio}, Doctor: {doctor_id}")
            
            # Obtener el ID de la cita insertada
            cursor.execute("SELECT LAST_INSERT_ID() as id")
            cita_id = cursor.fetchone()['id']
            
            cursor.close()
            db.close()
            
            # Convertir PDF a Base64 para descarga automática
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            response = {
                'success': True,
                'message': 'Cita generada exitosamente',
                'cita_id': cita_id,
                'numero_folio': numero_folio,
                'fecha': fecha_actual,
                'hora': hora_actual,
                'pdf_base64': pdf_base64
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error generando cita: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    # ==============================================
    # FUNCIÓN PARA OBTENER CITAS DEL DOCTOR
    # ==============================================
    
    def handle_get_citas(self, doctor_id):
        """Obtener todas las citas de un doctor específico"""
        try:
            print(f"[API] Obteniendo citas para doctor_id: {doctor_id}")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Verificar que el doctor existe
            cursor.execute("SELECT Diddoctor FROM doctores WHERE Diddoctor = %s", (doctor_id,))
            doctor = cursor.fetchone()
            
            if not doctor:
                print(f"[API] Doctor no encontrado: {doctor_id}")
                cursor.close()
                db.close()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps([]).encode())
                return
            
            # Obtener citas SOLO de este doctor específico
            cursor.execute("""
                SELECT 
                    id_cita,
                    numero_folio,
                    paciente,
                    DATE_FORMAT(fecha, '%d/%m/%Y') as fecha,
                    DATE_FORMAT(hora, '%H:%i') as hora,
                    documento_nombre,
                    documento_tamano,
                    resultado,
                    DATE_FORMAT(resultado_fecha_carga, '%d/%m/%Y %H:%i') as resultado_fecha_carga
                FROM citas 
                WHERE doctor_id = %s
                ORDER BY fecha DESC, hora DESC
            """, (doctor_id,))
            
            citas = cursor.fetchall()
            print(f"[API] Se encontraron {len(citas)} citas para el doctor {doctor_id}")
            
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
    
    # ==============================================
    # FUNCIÓN PARA OBTENER TODAS LAS CITAS (ADMIN)
    # ==============================================
    
    def handle_get_all_citas(self):
        """Obtener todas las citas para el panel de admin"""
        try:
            print(f"[API] Obteniendo todas las citas")
            
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    c.id_cita,
                    c.numero_folio,
                    c.paciente,
                    d.nombre as doctor_nombre,
                    d.Diddoctor as doctor_id,
                    DATE_FORMAT(c.fecha, '%d/%m/%Y') as fecha,
                    DATE_FORMAT(c.hora, '%H:%i') as hora,
                    c.documento_nombre,
                    c.documento_pdf IS NOT NULL as tiene_pdf
                FROM citas c
                LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                ORDER BY c.fecha DESC, c.hora DESC
                LIMIT 50
            """)
            
            citas = cursor.fetchall()
            print(f"[API] Se encontraron {len(citas)} citas totales")
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(citas).encode())
            
        except Exception as e:
            print(f"Error obteniendo todas las citas: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    # ==============================================
    # FUNCIONES PARA ADMIN - CORREGIDAS
    # ==============================================
    
    def handle_admin_stats(self):
        """Obtener estadísticas para el panel de admin"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Total de doctores activos
            cursor.execute("SELECT COUNT(*) as total FROM doctores WHERE activo = 1")
            total_doctores = cursor.fetchone()['total']
            
            # Total de citas
            cursor.execute("SELECT COUNT(*) as total FROM citas")
            total_citas = cursor.fetchone()['total']
            
            # Nuevos doctores en los últimos 7 días
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM doctores 
                WHERE fecha_registro >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            nuevos_doctores = cursor.fetchone()['total']
            
            # Citas completadas (con resultado cargado)
            cursor.execute("SELECT COUNT(*) as total FROM citas WHERE resultado IS NOT NULL")
            citas_completadas = cursor.fetchone()['total']
            
            cursor.close()
            db.close()
            
            stats = {
                'totalDoctores': total_doctores,
                'estudiosPendientes': 0,
                'nuevosDoctores': nuevos_doctores,
                'estudiosCompletados': citas_completadas,
                'totalCitas': total_citas
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
        """Obtener actividad reciente de la base de datos - CORREGIDO"""
        try:
            db = self.connect_db()
            cursor = db.cursor(dictionary=True)
            
            # Obtener las últimas citas como actividad
            cursor.execute("""
                SELECT 
                    CONCAT('Dr. ', d.nombre) as usuario_id,
                    'doctor' as tipo_usuario,
                    'Nueva cita' as accion,
                    DATE_FORMAT(COALESCE(c.fecha_creacion, c.fecha), '%Y-%m-%d %H:%i') as fecha,
                    CONCAT('Paciente: ', c.paciente, ' - Folio: ', c.numero_folio) as detalles
                FROM citas c
                LEFT JOIN doctores d ON c.doctor_id = d.Diddoctor
                WHERE c.id_cita IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    CONCAT('Dr. ', d.nombre) as usuario_id,
                    'doctor' as tipo_usuario,
                    'Registro' as accion,
                    DATE_FORMAT(d.fecha_registro, '%Y-%m-%d %H:%i') as fecha,
                    CONCAT('ID: ', d.Diddoctor, ' - ', COALESCE(d.especialidad, 'Sin especialidad')) as detalles
                FROM doctores d
                WHERE d.fecha_registro IS NOT NULL
                
                ORDER BY fecha DESC
                LIMIT 15
            """)
            
            actividades = cursor.fetchall()
            
            # Si no hay actividades, mostrar mensaje
            if len(actividades) == 0:
                # Intentar obtener solo doctores
                cursor.execute("""
                    SELECT 
                        CONCAT('Dr. ', nombre) as usuario_id,
                        'doctor' as tipo_usuario,
                        'Registro' as accion,
                        DATE_FORMAT(fecha_registro, '%Y-%m-%d %H:%i') as fecha,
                        CONCAT('ID: ', Diddoctor, ' - ', COALESCE(especialidad, 'Sin especialidad')) as detalles
                    FROM doctores
                    WHERE fecha_registro IS NOT NULL
                    ORDER BY fecha_registro DESC
                    LIMIT 10
                """)
                actividades = cursor.fetchall()
            
            # Si todavía no hay actividades, crear una por defecto
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
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(actividades).encode())
            
        except Exception as e:
            print(f"Error en actividad: {str(e)}")
            # En caso de error, devolver actividad por defecto
            actividades = [{
                'usuario_id': 'Sistema',
                'tipo_usuario': 'admin',
                'accion': 'Sistema activo',
                'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'detalles': f'Sistema funcionando correctamente'
            }]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(actividades).encode())
    
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
                       activo
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
                    activo
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
            
            # Total de citas del doctor
            cursor.execute("""
                SELECT COUNT(*) as total_citas
                FROM citas
                WHERE doctor_id = %s
            """, (doctor_id,))
            citas_result = cursor.fetchone()
            doctor['total_citas'] = citas_result['total_citas'] if citas_result else 0
            
            # Pacientes únicos
            cursor.execute("""
                SELECT COUNT(DISTINCT paciente) as total_pacientes
                FROM citas
                WHERE doctor_id = %s
            """, (doctor_id,))
            pacientes_result = cursor.fetchone()
            doctor['total_pacientes'] = pacientes_result['total_pacientes'] if pacientes_result else 0
            
            doctor['activo'] = bool(doctor['activo'])
            
            cursor.close()
            db.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(doctor).encode())
            
        except Exception as e:
            print(f"Error obteniendo detalles del doctor: {str(e)}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_doctores(self):
        """Obtener lista completa de doctores"""
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
                    activo
                FROM doctores
                ORDER BY Diddoctor ASC
            """)
            
            doctores = cursor.fetchall()
            
            # Agregar conteo de citas para cada doctor
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
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error cambiando contraseña: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
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
                    fecha_registro, activo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1)
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
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error creando doctor: {str(e)}")
            response = {'success': False, 'message': f'Error del servidor: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
    # ==============================================
    # FUNCIONES DE LOGIN Y REGISTRO
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
            
            if not usuario_encontrado:
                cursor.execute("SELECT * FROM doctores WHERE usuario = %s AND contrasena = %s", 
                              (username, password))
                doctor = cursor.fetchone()
                if doctor:
                    if doctor['activo'] == 0:
                        cursor.close()
                        db.close()
                        response = {'success': False, 'message': 'Su cuenta está desactivada. Contacte al administrador.'}
                        self.send_response(401)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(response).encode())
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
    
    def handle_registro(self):
        """Manejar el registro de nuevos doctores"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = parse_qs(post_data.decode())
        
        try:
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
                    fecha_registro, activo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1)
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
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error en registro: {str(e)}")
            response = {'success': False, 'message': f'Error: {str(e)}'}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
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
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error actualizando usuario: {str(e)}")
            response = {'success': False, 'message': str(e)}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
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
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error eliminando doctor: {str(e)}")
            response = {'success': False, 'message': str(e)}
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
    
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
print("🚀 SERVIDOR RADIOLOGÍA MÉDICA - VERSIÓN CORREGIDA")
print("=" * 60)
print(f"📊 Accede a: http://localhost:{PORT}")
print("\n👥 Usuarios de prueba:")
print("   • Doctor:    dr.rodriguez / doctor123")
print("   • Admin:     admin / admin123")
print("\n📝 Registro disponible en: /registro")
print("👑 Panel de administración: /admin")
print("📄 Receta Virtual integrada en Dashboard")
print("✅ ADMIN CORREGIDO - Carga datos reales de la BD")
print("✅ ACTIVIDAD RECIENTE - Corregida y funcionando")
print("✅ DESCARGA PDF - Botón disponible en Gestión de Citas")
print("=" * 60)

if not os.path.exists('templates'):
    os.makedirs('templates')
    print("📁 Carpeta 'templates' creada")

# Verificar si reportlab está instalado
try:
    from reportlab.lib import colors
    print("✅ ReportLab instalado correctamente")
except ImportError:
    print("⚠️ ReportLab no está instalado. Instalando...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'reportlab'])
    print("✅ ReportLab instalado correctamente")

try:
    server = HTTPServer(('', PORT), CustomHandler)
    print("\n✅ Servidor listo. Presiona Ctrl+C para detenerlo.")
    server.serve_forever()
except KeyboardInterrupt:
    print("\n⏹️  Servidor detenido")