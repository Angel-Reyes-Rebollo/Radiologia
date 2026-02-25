-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 25-02-2026 a las 01:42:31
-- Versión del servidor: 10.4.32-MariaDB-log
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `radiologia_db`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `actividad_admin`
--

CREATE TABLE `actividad_admin` (
  `id` int(11) NOT NULL,
  `usuario_id` varchar(50) DEFAULT NULL,
  `accion` varchar(100) DEFAULT NULL,
  `detalles` text DEFAULT NULL,
  `fecha` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `actividad_admin`
--

INSERT INTO `actividad_admin` (`id`, `usuario_id`, `accion`, `detalles`, `fecha`) VALUES
(1, 'ADMIN', 'CANCELAR_CITA', 'Cita cancelada: FOL-20260218-00002 - Paciente: Gambito', '2026-02-23 13:25:43'),
(2, 'ADMIN', 'CANCELAR_CITA', 'Cita cancelada: FOL-20260218-00001 - Paciente: Husker', '2026-02-23 13:37:58'),
(3, 'ADMIN', 'CANCELAR_CITA', 'Cita cancelada: FOL-20260223-00001 - Paciente: Jesus Ramirez', '2026-02-23 17:22:10'),
(4, 'ADMIN', 'ENTREGAR_RESULTADO', 'Resultado entregado para cita FOL-20260223-00002 - Paciente: Jesus - Puntos asignados: 13 - Tamaño: 21734.1KB', '2026-02-24 14:17:29'),
(5, 'ADMIN', 'PROGRAMAR_ELIMINACION', 'Eliminación programada para cita FOL-20260223-00002 - Paciente: Jesus - Fecha: 2026-02-26', '2026-02-24 16:32:10'),
(6, 'ADMIN', 'ENTREGAR_RESULTADO', 'Resultado entregado para cita FOL-20260223-00003 - Paciente: lucy - Puntos asignados: 14 - Tamaño: 21734.1KB', '2026-02-24 17:41:00'),
(7, 'ADMIN', 'PROGRAMAR_ELIMINACION', 'Eliminación programada para cita FOL-20260223-00003 - Paciente: lucy - Fecha: 2026-03-18', '2026-02-24 17:41:35');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `administradores`
--

CREATE TABLE `administradores` (
  `Aidadmin` varchar(20) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `usuario` varchar(50) NOT NULL,
  `contrasena` varchar(255) NOT NULL,
  `email` varchar(100) NOT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `administradores`
--

INSERT INTO `administradores` (`Aidadmin`, `nombre`, `usuario`, `contrasena`, `email`, `fecha_registro`, `activo`) VALUES
('A001', 'Administrador Principal', 'admin', 'admin123', 'admin@radiologia.com', '2026-02-04 20:11:56', 1);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `citas`
--

CREATE TABLE `citas` (
  `id_cita` int(11) NOT NULL,
  `numero_folio` varchar(20) NOT NULL,
  `paciente` varchar(100) NOT NULL,
  `doctor_id` varchar(20) NOT NULL,
  `fecha` date NOT NULL,
  `hora` time NOT NULL,
  `documento_nombre` varchar(255) DEFAULT NULL,
  `documento_pdf` longblob DEFAULT NULL,
  `documento_tamano` int(11) DEFAULT NULL,
  `documento_tipo` varchar(100) DEFAULT NULL,
  `fecha_cita` date DEFAULT NULL,
  `hora_cita` time DEFAULT NULL,
  `resultado` longblob DEFAULT NULL,
  `resultado_nombre` varchar(255) DEFAULT NULL,
  `resultado_tipo` varchar(100) DEFAULT NULL,
  `resultado_tamano` int(11) DEFAULT NULL,
  `resultado_fecha_carga` timestamp NULL DEFAULT current_timestamp(),
  `fecha_eliminacion` date DEFAULT NULL,
  `total_estudio` decimal(10,2) NOT NULL DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `doctores`
--

CREATE TABLE `doctores` (
  `Diddoctor` varchar(20) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `usuario` varchar(50) NOT NULL,
  `contrasena` varchar(255) NOT NULL,
  `especialidad` varchar(100) DEFAULT NULL,
  `email` varchar(100) NOT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `direccion_consultorio` text DEFAULT NULL,
  `telefono_consultorio` varchar(20) DEFAULT NULL,
  `fecha_registro` timestamp NOT NULL DEFAULT current_timestamp(),
  `puntos` int(11) DEFAULT 0,
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `doctores`
--

INSERT INTO `doctores` (`Diddoctor`, `nombre`, `usuario`, `contrasena`, `especialidad`, `email`, `telefono`, `direccion_consultorio`, `telefono_consultorio`, `fecha_registro`, `puntos`, `activo`) VALUES
('D001', 'Dr. Alejandro Rodríguez', 'dr.rodriguez', 'doctor123', 'Radiología General', 'dr.rodriguez@radiologia.com', '5512345678', 'Av. Insurgentes Sur 1234, Col. Del Valle, Ciudad de México, CP 03100', '5555123456', '2026-02-04 20:11:56', 27, 1),
('D002', 'Dra. María García', 'dr.garcia', 'doc12345', 'Tomografía Computarizada', 'dr.garcia@radiologia.com', '5523456789', 'Torre Médica Reforma, Piso 8, Av. Paseo de la Reforma 250, Col. Juárez, Ciudad de México, CP 06600', '5555234567', '2026-02-04 20:11:56', 0, 1),
('D003', 'Dr. Roberto Martínez', 'dr.martinez', 'doctor123', 'Resonancia Magnética', 'dr.martinez@radiologia.com', '5534567890', 'Centro Médico Santa Fe, Av. Santa Fe 150, Col. Santa Fe, Ciudad de México, CP 05348', '5555345678', '2026-02-04 20:11:56', 0, 1),
('D004', 'Angel Soriano', 'DR_ASoriano', 'Cosmic$21', 'Por definir', 'x@gmail.com', '1234567891', 'Consultorios Médicos Polanco, Av. Presidente Masaryk 311, Col. Polanco, Ciudad de México, CP 11560', '5555456789', '2026-02-04 20:13:35', 0, 1);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `notificaciones`
--

CREATE TABLE `notificaciones` (
  `id_notificacion` int(11) NOT NULL,
  `usuario_id` varchar(20) DEFAULT NULL,
  `tipo_usuario` enum('admin','doctor','paciente') DEFAULT NULL,
  `titulo` varchar(200) NOT NULL,
  `mensaje` text NOT NULL,
  `leida` tinyint(1) DEFAULT 0,
  `fecha_creacion` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `notificaciones`
--

INSERT INTO `notificaciones` (`id_notificacion`, `usuario_id`, `tipo_usuario`, `titulo`, `mensaje`, `leida`, `fecha_creacion`) VALUES
(1, 'D004', 'doctor', 'Bienvenido al sistema', 'Bienvenido Dr. Angel Soriano. Su cuenta ha sido creada exitosamente.', 0, '2026-02-04 20:13:35'),
(2, 'D001', 'doctor', 'Nueva cita agendada', 'Nueva cita agendada para el 2026-02-04 a las 09:00', 0, '2026-02-04 22:22:58'),
(3, 'P001', 'paciente', 'Cita agendada', 'Se ha agendado una cita para el 2026-02-04 a las 09:00', 0, '2026-02-04 22:22:58'),
(4, 'A001', 'admin', 'Cita actualizada', 'Cita 4 actualizada: Paciente Carlos López, Doctor Dr. Alejandro Rodríguez', 0, '2026-02-04 22:23:24'),
(5, 'A001', 'admin', 'Cita actualizada', 'Cita 4 actualizada: Paciente Carlos López, Doctor Dr. Alejandro Rodríguez', 0, '2026-02-04 22:26:22'),
(6, 'P001', 'doctor', 'Estado de paciente actualizado', 'Estado actualizado a: cronico para el paciente Carlos López', 0, '2026-02-05 01:24:08'),
(7, 'D004', 'doctor', 'Recordatorio de cita', 'Tiene una cita programada para mañana a las 10:30', 0, '2026-02-05 09:00:00'),
(8, 'P003', 'paciente', 'Resultados de laboratorio', 'Sus resultados de laboratorio ya están disponibles', 0, '2026-02-05 11:30:22'),
(9, 'D002', 'doctor', 'Paciente urgente', 'El paciente María González requiere atención prioritaria', 0, '2026-02-05 14:15:45'),
(10, 'A002', 'admin', 'Mantenimiento del sistema', 'El sistema estará en mantenimiento el domingo 08:00-12:00', 0, '2026-02-06 08:00:00'),
(11, 'D001', 'doctor', 'Nuevo mensaje', 'Ha recibido un mensaje del paciente Juan Pérez', 1, '2026-02-06 10:45:12'),
(12, 'P002', 'paciente', 'Recordatorio de medicación', 'No olvide tomar su medicación a las 20:00', 0, '2026-02-06 16:30:00'),
(13, 'A001', 'admin', 'Reporte generado', 'El reporte mensual ha sido generado exitosamente', 1, '2026-02-07 09:12:33'),
(14, 'D003', 'doctor', 'Actualización de horario', 'Su horario de atención ha sido actualizado', 0, '2026-02-07 13:20:18'),
(15, 'P005', 'paciente', 'Cita cancelada', 'Su cita del 2026-02-08 ha sido cancelada', 0, '2026-02-07 15:40:00');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `actividad_admin`
--
ALTER TABLE `actividad_admin`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`id_cita`);

--
-- Indices de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  ADD PRIMARY KEY (`id_notificacion`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `actividad_admin`
--
ALTER TABLE `actividad_admin`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT de la tabla `citas`
--
ALTER TABLE `citas`
  MODIFY `id_cita` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;

--
-- AUTO_INCREMENT de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  MODIFY `id_notificacion` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
