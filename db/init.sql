DROP TABLE IF EXISTS card_order;
DROP TABLE IF EXISTS cards;
DROP TABLE IF EXISTS columns;
DROP TABLE IF EXISTS tareas;
DROP TABLE IF EXISTS invitaciones;
DROP TABLE IF EXISTS proyecto_usuarios;
DROP TABLE IF EXISTS proyectos;
DROP TABLE IF EXISTS prioridades;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS usuarios;

-- --- 2. TABLAS MAESTRAS INDEPENDIENTES ---
CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE 
); 

CREATE TABLE prioridades(
    id INT AUTO_INCREMENT PRIMARY KEY,
    nivel VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE columns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- --- 3. TABLA PROYECTOS (El Gobernador) ---
CREATE TABLE proyectos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    duracion_dias INT NOT NULL,
    codigo_invitacion VARCHAR(15) NOT NULL UNIQUE,
    categoria_id INT,
    prioridad_id INT,
    creador_id INT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL,
    FOREIGN KEY (prioridad_id) REFERENCES prioridades(id) ON DELETE SET NULL,
    FOREIGN KEY (creador_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- --- 4. TABLA INTERMEDIA: EQUIPO ACTIVO ---
CREATE TABLE proyecto_usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proyecto_id INT NOT NULL,
    usuario_id INT NOT NULL,
    rol ENUM('admin', 'miembro') DEFAULT 'miembro',
    
    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

-- --- 5. TABLA INVITACIONES: EQUIPO EN ESPERA (Sin cuenta aún) ---
CREATE TABLE invitaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    proyecto_id INT NOT NULL,
    token VARCHAR(100) UNIQUE NOT NULL,
    estado ENUM('pendiente', 'aceptada', 'expirada') DEFAULT 'pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE
);

-- --- 6. TABLA TAREAS: GENERADAS POR LA IA POR ROLES ---
CREATE TABLE tareas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    proyecto_id INT NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    descripcion TEXT,
    dias_estimados INT NOT NULL,
    
    -- El rol que inventó la IA (Backend, UX, etc.) para agruparlas en Qt
    rol_sugerido VARCHAR(50) NOT NULL, 

    -- Soporte híbrido para la asignación inteligente
    asignado_usuario_id INT NULL,        -- ID si el usuario ya tiene cuenta activa
    asignado_email VARCHAR(120) NULL,    -- Email de la invitación si aún no se registró
    
    estado ENUM('pendiente', 'en_progreso', 'completada') DEFAULT 'pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE CASCADE,
    FOREIGN KEY (asignado_usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

INSERT INTO usuarios (nombre, apellido, email, password)
VALUES ('Rubi', 'Solis', 'rubisolis215@gmail.com', '1234');

INSERT INTO categorias (nombre) VALUES ('Software'), ('Educación'), ('Salud');
INSERT INTO prioridades (nivel) VALUES ('Baja'), ('Media'), ('Alta');