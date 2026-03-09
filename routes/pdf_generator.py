# ============================================================
# routes/pdf_generator.py — Generación de PDFs con ReportLab
# ============================================================
# Este archivo contiene ÚNICAMENTE la lógica de generación
# de PDFs. Antes estaba dentro de CustomHandler mezclada
# con todo lo demás. Ahora es reutilizable e independiente.
# ============================================================

import io
import os
from reportlab.lib import colors

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from database import get_db


def generate_pdf_cita(data):
    """
    Genera el PDF de una cita y lo devuelve como bytes.
    Recibe un diccionario 'data' con todos los datos de la cita.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=20, leftMargin=20,
                            topMargin=15, bottomMargin=15)

    styles = getSampleStyleSheet()

    color_primario      = colors.HexColor('#1C1C26')
    color_acento        = colors.HexColor('#3A3A4F')
    color_texto_oscuro  = colors.HexColor('#333333')
    color_texto_claro   = colors.white

    styles.add(ParagraphStyle(
        name='Subtitulo', parent=styles['Heading2'],
        fontSize=10, textColor=color_primario,
        alignment=TA_LEFT, spaceBefore=4, spaceAfter=2,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='EtiquetaCampo', parent=styles['Normal'],
        fontSize=7, textColor=colors.HexColor('#666666'),
        alignment=TA_LEFT, spaceAfter=0,
        fontName='Helvetica-Oblique'
    ))
    styles.add(ParagraphStyle(
        name='ValorCampo', parent=styles['Normal'],
        fontSize=8, textColor=color_texto_oscuro,
        alignment=TA_LEFT, spaceAfter=1,
        fontName='Helvetica', leading=10
    ))
    styles.add(ParagraphStyle(
        name='EstudioItem', parent=styles['Normal'],
        fontSize=8, textColor=color_texto_oscuro,
        alignment=TA_LEFT, leftIndent=5,
        fontName='Helvetica', spaceAfter=1, leading=10
    ))

    story = []

    def load_image(path, width=0.5*inch, height=0.5*inch):
        if os.path.exists(path):
            return Image(path, width=width, height=height)
        return None

    # Obtener datos del doctor desde la BD
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT nombre, especialidad, telefono_consultorio, email FROM doctores WHERE Diddoctor = %s",
            (data['doctor_id'],)
        )
        doctor = cursor.fetchone()
        cursor.close()
        db.close()
    except Exception:
        doctor = None

    if not doctor and data.get('doctor_id') == 'ADMIN':
        doctor = {
            'nombre': 'Administrador', 'especialidad': 'Administración',
            'telefono_consultorio': 'N/A', 'email': 'admin@4digital.com'
        }

    # ── Encabezado ──────────────────────────────────────────
    header_bar = Table([['']], colWidths=[doc.width])
    header_bar.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color_primario),
        ('HEIGHT', (0, 0), (-1, -1), 0.08*inch),
    ]))
    story.append(header_bar)
    story.append(Spacer(1, 2))

    logo = load_image(os.path.join(BASE_DIR, 'static', 'LOGO4Digital.jpg'), width=0.5*inch, height=0.5*inch)
    if logo:
        header_data = [[logo, Paragraph(
            "<font size=11><b>4DIGITAL</b></font> <font size=7>Rad.Dental Chih.</font>",
            ParagraphStyle('HT', parent=styles['Normal'], textColor=color_primario, alignment=TA_RIGHT)
        )]]
    else:
        header_data = [[
            Paragraph("<font size=13><b>4DIGITAL</b></font>",
                      ParagraphStyle('HT', parent=styles['Normal'], textColor=color_primario)),
            Paragraph("614 6631185", styles['EtiquetaCampo'])
        ]]

    header_table = Table(header_data, colWidths=[0.7*inch, doc.width - 0.7*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)

    story.append(Paragraph(
        f"<font size=7>FOLIO:</font> <font size=9 color='#1C1C26'><b>{data['numero_folio']}</b></font>",
        ParagraphStyle('Folio', parent=styles['Normal'], alignment=TA_RIGHT)
    ))
    story.append(Spacer(1, 2))

    # ── Sección 1: Datos del paciente ───────────────────────
    story.append(Paragraph("PACIENTE", styles['Subtitulo']))

    paciente_rows = []
    nombre_line = f"<b>Nombre:</b> {data['paciente']}"
    if data.get('paciente_edad'):
        nombre_line += f" | <b>Edad:</b> {data['paciente_edad']}"
    if data.get('paciente_fecha_nacimiento'):
        nombre_line += f" | <b>F. Nac:</b> {data['paciente_fecha_nacimiento']}"
    paciente_rows.append([Paragraph(nombre_line, styles['ValorCampo'])])

    contacto = ""
    if data.get('pacienteTel'):
        contacto += f"<b>Tel:</b> {data['pacienteTel']}"
    if data.get('pacienteEmail'):
        contacto += f" | <b>Email:</b> {data['pacienteEmail']}" if contacto else f"<b>Email:</b> {data['pacienteEmail']}"
    if contacto:
        paciente_rows.append([Paragraph(contacto, styles['ValorCampo'])])

    paciente_table = Table(paciente_rows, colWidths=[doc.width])
    paciente_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F8FA')),
        ('BOX', (0, 0), (-1, -1), 0.5, color_acento),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(paciente_table)
    story.append(Spacer(1, 4))

    # ── Sección 2: Datos del médico ──────────────────────────
    story.append(Paragraph("DATOS DEL MÉDICO", styles['Subtitulo']))

    medico_rows = []
    medico_line = f"<b>Médico:</b> {doctor['nombre'] if doctor else 'N/A'}"
    if doctor and doctor.get('especialidad'):
        medico_line += f" | <b>Especialidad:</b> {doctor['especialidad'][:20]}"
    medico_rows.append([Paragraph(medico_line, styles['ValorCampo'])])

    contacto_med = ""
    if doctor and doctor.get('email'):
        contacto_med += f"<b>Email:</b> {doctor['email']}"
    if doctor and doctor.get('telefono_consultorio'):
        sep = " | " if contacto_med else ""
        contacto_med += f"{sep}<b>Tel. Consultorio:</b> {doctor['telefono_consultorio']}"
    if contacto_med:
        medico_rows.append([Paragraph(contacto_med, styles['ValorCampo'])])

    medico_table = Table(medico_rows, colWidths=[doc.width])
    medico_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F8FA')),
        ('BOX', (0, 0), (-1, -1), 0.5, color_acento),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(medico_table)
    story.append(Spacer(1, 4))

    # ── Sección 3: Fecha y hora de cita ─────────────────────
    cita_info = (f"<b>Fecha de cita:</b> {data['fecha_cita']} - {data['hora_cita']} "
                 f"| <b>Registro:</b> {data['fecha_registro']}")
    cita_table = Table([[Paragraph(cita_info, styles['ValorCampo'])]], colWidths=[doc.width])
    cita_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F0F5')),
        ('BOX', (0, 0), (-1, -1), 0.5, color_acento),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(cita_table)
    story.append(Spacer(1, 4))

    # ── Sección 4: Formato de entrega ────────────────────────
    fmt_rows = [
        [Paragraph("<b>Formato de entrega general:</b>", styles['EtiquetaCampo']),
         Paragraph(f"{data.get('formato_entrega', 'Digital')}", styles['ValorCampo'])]
    ]
    fmt_foto = data.get('formato_entrega_fotografias')
    if fmt_foto:
        fmt_rows.append([
            Paragraph("<b>Formato de entrega fotografías:</b>", styles['EtiquetaCampo']),
            Paragraph(f"{fmt_foto}", styles['ValorCampo'])
        ])

    fmt_table = Table(fmt_rows, colWidths=[1.6*inch, doc.width - 1.6*inch])
    fmt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F8FA')),
        ('BOX', (0, 0), (-1, -1), 0.5, color_acento),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, colors.HexColor('#CCCCCC')),
    ]))
    story.append(fmt_table)
    story.append(Spacer(1, 4))

    # ── Sección 5: Estudios seleccionados ───────────────────
    estudios = data.get('estudios', [])
    categorias = {
        'ORTODÓNTICOS': [], 'RADIOGRAFÍAS 2D': [],
        'FOTOGRAFÍAS': [], 'MODELOS 3D': [], 'TOMOGRAFÍAS 3D': []
    }

    for estudio in estudios:
        nombre = estudio['nombre']
        precio = estudio['precio']
        precio_fmt = f"${precio:,.0f}" if isinstance(precio, (int, float)) else str(precio)
        texto = f"✓ {nombre[:35]} - {precio_fmt}"

        if "Ortodóntico" in nombre:
            categorias['ORTODÓNTICOS'].append(texto)
        elif any(p in nombre for p in ['Ortopantomografía', 'Panorámica', 'Lateral', 'P-A',
                                        'A-P', 'Waters', 'ATM', 'Digito', 'Periapical',
                                        'Oclusal', 'Senos']):
            categorias['RADIOGRAFÍAS 2D'].append(texto)
        elif any(p in nombre for p in ['Fotos', 'Fotografía', 'Escaneo facial']):
            categorias['FOTOGRAFÍAS'].append(texto)
        elif "Modelo dental" in nombre:
            categorias['MODELOS 3D'].append(texto)
        elif any(p in nombre for p in ['Tomografía', 'Endodoncia', 'Cirugía', 'Endoscan']):
            categorias['TOMOGRAFÍAS 3D'].append(texto)

    for cat_nombre, items in categorias.items():
        if not items:
            continue

        cat_title = Paragraph(
            f"<b>{cat_nombre}</b>",
            ParagraphStyle('Cat', parent=styles['Normal'],
                           textColor=color_texto_claro, fontSize=8, leading=9)
        )
        cat_table = Table([[cat_title]], colWidths=[doc.width])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), color_primario),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(cat_table)

        if len(items) > 5:
            mitad = len(items) // 2
            col1, col2 = items[:mitad], items[mitad:]
            while len(col1) < len(col2):
                col1.append("")
            while len(col2) < len(col1):
                col2.append("")

            rows = [[Paragraph(c1, styles['EstudioItem']), Paragraph(c2, styles['EstudioItem'])]
                    for c1, c2 in zip(col1, col2)]
            items_table = Table(rows, colWidths=[doc.width/2.1, doc.width/2.1])
            items_table.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(items_table)
        else:
            for item in items:
                story.append(Paragraph(item, styles['EstudioItem']))

        story.append(Spacer(1, 2))

    if not estudios:
        story.append(Paragraph("No se seleccionaron estudios", styles['EstudioItem']))

    # ── Sección 6: Total ─────────────────────────────────────
    story.append(Spacer(1, 4))
    total_str = f"<b>TOTAL: ${float(data.get('total', 0)):,.2f}</b>"
    total_table = Table(
        [[Paragraph(total_str, ParagraphStyle('Total', parent=styles['Normal'],
                                               fontSize=10, alignment=TA_RIGHT,
                                               textColor=color_primario))]],
        colWidths=[doc.width]
    )
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F0F5')),
        ('BOX', (0, 0), (-1, -1), 0.5, color_acento),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(total_table)

    # ── Observaciones ────────────────────────────────────────
    if data.get('observaciones'):
        story.append(Spacer(1, 4))
        story.append(Paragraph("OBSERVACIONES", styles['Subtitulo']))
        story.append(Paragraph(data['observaciones'], styles['ValorCampo']))

    # ── Firma del médico ─────────────────────────────────────
    story.append(Spacer(1, 30))
    nombre_doctor = doctor['nombre'] if doctor else 'N/A'
    especialidad_doctor = doctor.get('especialidad', '') if doctor else ''

    firma_linea = Table([['_' * 35]], colWidths=[2.2*inch])
    firma_linea.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))

    firma_nombre = Paragraph(
        f"<b>{nombre_doctor}</b>",
        ParagraphStyle('FirmaNombre', parent=styles['Normal'],
                       fontSize=8, alignment=TA_CENTER, textColor=color_texto_oscuro)
    )
    firma_esp = Paragraph(
        especialidad_doctor,
        ParagraphStyle('FirmaEsp', parent=styles['Normal'],
                       fontSize=7, alignment=TA_CENTER,
                       textColor=colors.HexColor('#666666'))
    )

    firma_table = Table(
        [[firma_linea], [firma_nombre], [firma_esp]],
        colWidths=[2.2*inch]
    )
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    # Centrar la firma en la página
    firma_outer = Table([[firma_table]], colWidths=[doc.width])
    firma_outer.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(firma_outer)

    doc.build(story)
    return buffer.getvalue()
