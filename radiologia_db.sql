-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 12-02-2026 a las 01:00:43
-- Versión del servidor: 10.4.32-MariaDB
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
  `fecha_carga_documento` timestamp NULL DEFAULT NULL,
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
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
  `activo` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `doctores`
--

INSERT INTO `doctores` (`Diddoctor`, `nombre`, `usuario`, `contrasena`, `especialidad`, `email`, `telefono`, `direccion_consultorio`, `telefono_consultorio`, `fecha_registro`, `activo`) VALUES
('D001', 'Dr. Alejandro Rodríguez', 'dr.rodriguez', 'doctor123', 'Radiología General', 'dr.rodriguez@radiologia.com', '5512345678', 'Av. Insurgentes Sur 1234, Col. Del Valle, Ciudad de México, CP 03100', '5555123456', '2026-02-04 20:11:56', 0),
('D002', 'Dra. María García', 'dr.garcia', 'doctor123', 'Tomografía Computarizada', 'dr.garcia@radiologia.com', '5523456789', 'Torre Médica Reforma, Piso 8, Av. Paseo de la Reforma 250, Col. Juárez, Ciudad de México, CP 06600', '5555234567', '2026-02-04 20:11:56', 1),
('D003', 'Dr. Roberto Martínez', 'dr.martinez', 'doctor123', 'Resonancia Magnética', 'dr.martinez@radiologia.com', '5534567890', 'Centro Médico Santa Fe, Av. Santa Fe 150, Col. Santa Fe, Ciudad de México, CP 05348', '5555345678', '2026-02-04 20:11:56', 1),
('D004', 'Angel Soriano', 'DR_ASoriano', 'Cosmic$21', 'Por definir', 'x@gmail.com', '1234567891', 'Consultorios Médicos Polanco, Av. Presidente Masaryk 311, Col. Polanco, Ciudad de México, CP 11560', '5555456789', '2026-02-04 20:13:35', 1);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `estudios`
--

CREATE TABLE `estudios` (
  `id_estudio` int(11) NOT NULL,
  `Pidpaciente` varchar(20) DEFAULT NULL,
  `Diddoctor` varchar(20) DEFAULT NULL,
  `tipo_estudio` varchar(100) NOT NULL,
  `estudio_especifico` varchar(100) DEFAULT NULL,
  `fecha_realizacion` date NOT NULL,
  `resultado` text DEFAULT NULL,
  `archivo_url` varchar(255) DEFAULT NULL,
  `estado` enum('pendiente','completado','revision') DEFAULT 'pendiente',
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `estudios`
--

INSERT INTO `estudios` (`id_estudio`, `Pidpaciente`, `Diddoctor`, `tipo_estudio`, `estudio_especifico`, `fecha_realizacion`, `resultado`, `archivo_url`, `estado`, `fecha_creacion`) VALUES
(1, 'P001', 'D001', 'Radiografía de Tórax', 'Radiografía de Tórax', '2023-11-15', 'Resultados normales, sin hallazgos patológicos.', NULL, 'completado', '2026-02-04 20:11:56'),
(2, 'P002', 'D002', 'Resonancia Magnética Cerebral', 'Resonancia Magnética Cerebral', '2023-11-10', 'Estudio dentro de parámetros normales.', NULL, 'completado', '2026-02-04 20:11:56'),
(3, 'P003', 'D001', 'Ecografía Abdominal', 'Ecografía Abdominal', '2023-10-25', 'Leve hepatomegalia, se recomienda seguimiento.', NULL, 'completado', '2026-02-04 20:11:56'),
(4, 'P001', 'D001', 'Resonancia Magnética', 'RMN de Columna Lumbar', '2024-03-15', NULL, NULL, 'pendiente', '2026-02-04 21:38:18'),
(5, 'P001', 'D001', 'Tomografía', 'TC de Cráneo Contrastada', '2024-03-20', NULL, NULL, 'pendiente', '2026-02-04 21:38:37'),
(6, 'P001', 'D001', 'Ecografía', 'Eco Abdominal Doppler', '2024-03-18', NULL, NULL, 'pendiente', '2026-02-04 21:38:37'),
(7, 'P001', 'D001', 'Rayos X', 'RX de Rodilla AP/Lateral', '2024-03-22', NULL, NULL, 'pendiente', '2026-02-04 21:38:37'),
(8, 'P002', 'D002', 'Resonancia Magnética', 'RMN Cerebral con Contraste', '2024-03-25', NULL, NULL, 'pendiente', '2026-02-04 21:38:37'),
(9, 'P003', 'D003', 'Tomografía', 'TC Torácica', '2024-03-19', NULL, NULL, 'pendiente', '2026-02-04 21:38:37'),
(10, 'P001', 'D001', 'Rayos X', NULL, '2026-02-04', NULL, NULL, 'pendiente', '2026-02-04 22:22:58'),
(11, 'P001', 'D001', 'Rayos X', NULL, '2026-02-04', NULL, NULL, 'pendiente', '2026-02-05 01:26:35'),
(12, 'P001', 'D001', 'Tomografía', NULL, '2026-02-04', NULL, NULL, 'pendiente', '2026-02-05 01:27:13'),
(13, 'P004', 'D001', 'Resonancia Magnética', 'Resonancia Magnética', '2026-02-09', NULL, NULL, 'pendiente', '2026-02-08 15:10:55'),
(14, 'P001', 'D001', 'Resonancia Magnética', 'Resonancia Magnética', '2026-02-12', NULL, NULL, 'pendiente', '2026-02-09 15:49:47'),
(15, 'P001', 'D001', 'Tomografía', 'Ejemplo 1', '2026-02-23', NULL, NULL, 'pendiente', '2026-02-09 16:10:23'),
(16, 'P004', 'D001', 'Resonancia Magnética', 'Resonancia Magnética', '2026-02-10', NULL, NULL, 'pendiente', '2026-02-10 20:18:22');

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
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp()
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
(6, 'P001', 'doctor', 'Estado de paciente actualizado', 'Estado actualizado a: cronico para el paciente Carlos López', 0, '2026-02-05 01:25:49'),
(7, 'P001', 'doctor', 'Estado de paciente actualizado', 'Estado actualizado a: seguimiento para el paciente Carlos López', 0, '2026-02-05 01:25:50'),
(8, 'P001', 'doctor', 'Estado de paciente actualizado', 'Estado actualizado a: recuperado para el paciente Carlos López', 0, '2026-02-05 01:25:51'),
(9, 'P001', 'doctor', 'Estado de paciente actualizado', 'Estado actualizado a: cronico para el paciente Carlos López', 0, '2026-02-05 01:25:53'),
(10, 'P001', 'doctor', 'Estado de paciente actualizado', 'Estado actualizado a: agudo para el paciente Carlos López', 0, '2026-02-05 01:26:01'),
(11, 'D001', 'doctor', 'Nueva cita agendada', 'Nueva cita agendada para el 2026-02-04 a las 09:00', 0, '2026-02-05 01:26:35'),
(12, 'P001', 'paciente', 'Cita agendada', 'Se ha agendado una cita para el 2026-02-04 a las 09:00', 0, '2026-02-05 01:26:35'),
(13, 'D001', 'doctor', 'Nueva cita agendada', 'Nueva cita agendada para el 2026-02-04 a las 20:00', 0, '2026-02-05 01:27:13'),
(14, 'P001', 'paciente', 'Cita agendada', 'Se ha agendado una cita para el 2026-02-04 a las 20:00', 0, '2026-02-05 01:27:13'),
(15, 'A001', 'admin', 'Cita actualizada', 'Cita 6 actualizada: Paciente Carlos López, Doctor Dr. Alejandro Rodríguez', 0, '2026-02-05 20:04:15'),
(16, 'A001', 'admin', 'Cita actualizada', 'Cita 6 actualizada: Paciente Carlos López, Doctor Dr. Alejandro Rodríguez', 0, '2026-02-05 20:05:23'),
(17, 'A001', 'admin', 'Cita actualizada', 'Cita 6 actualizada: Paciente Carlos López, Doctor Dr. Alejandro Rodríguez', 0, '2026-02-05 23:09:15'),
(18, 'P004', 'paciente', 'Bienvenido al sistema', 'Bienvenido Cosmic Rebollo. Su cuenta ha sido creada exitosamente.', 0, '2026-02-06 19:13:04'),
(19, 'D001', 'doctor', 'Nuevo paciente asignado', 'Se le ha asignado un nuevo paciente: Cosmic Rebollo', 0, '2026-02-06 19:13:04'),
(20, 'P004', 'doctor', 'Estado de paciente actualizado', 'Estado actualizado a: cronico para el paciente Cosmic Rebollo', 0, '2026-02-06 19:13:37');

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vista_dashboard_doctor`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `vista_dashboard_doctor` (
);

-- --------------------------------------------------------

--
-- Estructura para la vista `vista_dashboard_doctor`
--
DROP TABLE IF EXISTS `vista_dashboard_doctor`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vista_dashboard_doctor`  AS SELECT `d`.`Diddoctor` AS `Diddoctor`, `d`.`nombre` AS `doctor_nombre`, count(distinct `c`.`id_cita`) AS `citas_hoy`, count(distinct `p`.`Pidpaciente`) AS `total_pacientes`, count(distinct `e`.`id_estudio`) AS `estudios_pendientes` FROM (((`doctores` `d` left join `citas` `c` on(`d`.`Diddoctor` = `c`.`Diddoctor` and `c`.`fecha` = curdate())) left join `pacientes` `p` on(`d`.`Diddoctor` = `p`.`doctor_asignado`)) left join `estudios` `e` on(`d`.`Diddoctor` = `e`.`Diddoctor` and `e`.`estado` = 'pendiente')) GROUP BY `d`.`Diddoctor`, `d`.`nombre` ;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `administradores`
--
ALTER TABLE `administradores`
  ADD PRIMARY KEY (`Aidadmin`),
  ADD UNIQUE KEY `usuario` (`usuario`),
  ADD UNIQUE KEY `email` (`email`),
  ADD KEY `idx_administradores_usuario` (`usuario`);

--
-- Indices de la tabla `citas`
--
ALTER TABLE `citas`
  ADD PRIMARY KEY (`id_cita`),
  ADD UNIQUE KEY `idx_folio_unico` (`numero_folio`),
  ADD KEY `idx_citas_doctor` (`doctor_id`);

--
-- Indices de la tabla `doctores`
--
ALTER TABLE `doctores`
  ADD PRIMARY KEY (`Diddoctor`),
  ADD UNIQUE KEY `usuario` (`usuario`),
  ADD UNIQUE KEY `email` (`email`),
  ADD KEY `idx_doctores_usuario` (`usuario`);

--
-- Indices de la tabla `estudios`
--
ALTER TABLE `estudios`
  ADD PRIMARY KEY (`id_estudio`),
  ADD KEY `Diddoctor` (`Diddoctor`),
  ADD KEY `idx_estudios_paciente` (`Pidpaciente`);

--
-- Indices de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  ADD PRIMARY KEY (`id_notificacion`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `citas`
--
ALTER TABLE `citas`
  MODIFY `id_cita` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `estudios`
--
ALTER TABLE `estudios`
  MODIFY `id_estudio` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT de la tabla `notificaciones`
--
ALTER TABLE `notificaciones`
  MODIFY `id_notificacion` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `citas`
--
ALTER TABLE `citas`
  ADD CONSTRAINT `fk_citas_doctor` FOREIGN KEY (`doctor_id`) REFERENCES `doctores` (`Diddoctor`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
