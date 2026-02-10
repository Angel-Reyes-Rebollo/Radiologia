<?php
// Conectar a la base de datos
$servername = "127.0.0.1";
$username = "root"; // Cambiar si es necesario
$password = ""; // Cambiar si es necesario
$dbname = "radiologia_db";

$conn = new mysqli($servername, $username, $password, $dbname);

// Verificar conexión
if ($conn->connect_error) {
    die("Error de conexión: " . $conn->connect_error);
}

// Configurar codificación
$conn->set_charset("utf8mb4");

// Obtener datos del formulario
$paciente_id = $_POST['paciente_id'] ?? '';
$doctor_id = $_POST['doctor_id'] ?? '';
$tipo_estudio = $_POST['tipo_estudio'] ?? '';
$estudio_especifico = $_POST['estudio_especifico'] ?? '';
$fecha = $_POST['fecha'] ?? '';
$hora = $_POST['hora'] ?? '';
$notas = $_POST['notas'] ?? '';
$instrucciones = $_POST['instrucciones'] ?? '';

// Validar datos (debes agregar más validaciones según tus necesidades)
if (empty($paciente_id) || empty($doctor_id) || empty($tipo_estudio) || empty($fecha) || empty($hora)) {
    die("Error: Faltan datos obligatorios");
}

// Crear nota combinada
$nota_completa = "";
if (!empty($notas)) {
    $nota_completa .= "Motivo: " . $notas;
}
if (!empty($instrucciones)) {
    if (!empty($nota_completa)) $nota_completa .= "\n";
    $nota_completa .= "Instrucciones: " . $instrucciones;
}

// Preparar y ejecutar la consulta
$sql = "INSERT INTO citas (Pidpaciente, Diddoctor, tipo_estudio, estudio_especifico, fecha, hora, estado, notas) 
        VALUES (?, ?, ?, ?, ?, ?, 'pendiente', ?)";

$stmt = $conn->prepare($sql);
$stmt->bind_param("sssssss", $paciente_id, $doctor_id, $tipo_estudio, $estudio_especifico, $fecha, $hora, $nota_completa);

if ($stmt->execute()) {
    $id_cita = $stmt->insert_id;
    
    // Crear notificación para el doctor
    $sql_notif_doctor = "INSERT INTO notificaciones (usuario_id, tipo_usuario, titulo, mensaje) 
                         VALUES (?, 'doctor', 'Nueva cita agendada', ?)";
    $mensaje_doctor = "Nueva cita agendada para el $fecha a las $hora - Paciente ID: $paciente_id";
    $stmt_doc = $conn->prepare($sql_notif_doctor);
    $stmt_doc->bind_param("ss", $doctor_id, $mensaje_doctor);
    $stmt_doc->execute();
    
    // Crear notificación para el paciente
    $sql_notif_paciente = "INSERT INTO notificaciones (usuario_id, tipo_usuario, titulo, mensaje) 
                           VALUES (?, 'paciente', 'Cita agendada', ?)";
    $mensaje_paciente = "Se ha agendado una cita para el $fecha a las $hora - Estudio: $tipo_estudio";
    $stmt_pac = $conn->prepare($sql_notif_paciente);
    $stmt_pac->bind_param("ss", $paciente_id, $mensaje_paciente);
    $stmt_pac->execute();
    
    // Crear notificación para el admin
    $sql_notif_admin = "INSERT INTO notificaciones (usuario_id, tipo_usuario, titulo, mensaje) 
                        VALUES ('A001', 'admin', 'Nueva cita creada', ?)";
    $mensaje_admin = "Nueva cita creada: ID $id_cita - Paciente: $paciente_id - Doctor: $doctor_id";
    $stmt_admin = $conn->prepare($sql_notif_admin);
    $stmt_admin->bind_param("s", $mensaje_admin);
    $stmt_admin->execute();
    
    // Crear estudio automáticamente en la tabla estudios
    $sql_estudio = "INSERT INTO estudios (Pidpaciente, Diddoctor, tipo_estudio, estudio_especifico, fecha_realizacion, estado) 
                    VALUES (?, ?, ?, ?, ?, 'pendiente')";
    $stmt_est = $conn->prepare($sql_estudio);
    $stmt_est->bind_param("sssss", $paciente_id, $doctor_id, $tipo_estudio, $estudio_especifico, $fecha);
    $stmt_est->execute();
    
    // Retornar respuesta en formato JSON
    echo json_encode([
        'success' => true,
        'message' => 'Cita agendada exitosamente',
        'cita_id' => $id_cita,
        'appointment_id' => 'CITA-' . str_pad($id_cita, 6, '0', STR_PAD_LEFT)
    ]);
} else {
    echo json_encode([
        'success' => false,
        'message' => 'Error al guardar la cita: ' . $stmt->error
    ]);
}

// Cerrar conexiones
$stmt->close();
$conn->close();
?>