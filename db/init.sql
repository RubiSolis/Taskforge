CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  apellido VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO usuarios (username, password, nombre, apellido, email)
VALUES ('cponce', '$2b$12$6uZ/ZXGHGnrjUiEFg0d35./CCYRRKWmOd3p31mdtFfwXzTIpPualG', 'Carlos', 'Ponce', 'cponce@example.com');

CREATE TABLE cards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    column_id INT,
    position INT DEFAULT 0
);

CREATE TABLE columns (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
INSERT INTO columns (name) VALUES ('TODO'), ('DOING'), ('DONE');