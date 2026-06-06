from datetime import datetime, timedelta, timezone
import os
import psutil
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
import bcrypt
import mysql.connector
import secrets
app = FastAPI(title="VPS-POO API", root_path="/api")
JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "poo_user"),
    "password": os.getenv("DB_PASSWORD", "poo_pass"),
    "database": os.getenv("DB_NAME", "vps-poo"),
}
security = HTTPBearer(auto_error=False)

cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if not cors_origins:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RegisterRequest(BaseModel):
    nombre: str
    apellido: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class MoveCard(BaseModel):
    column_id: int
    position: int | None = None

class ProyectoCrearRequest(BaseModel):
    titulo: str
    descripcion: str
    duracion_dias: int
    categoria_id: int
    prioridad_id: int
    cantidad_participantes: int

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def get_user_by_email(email: str):
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM usuarios WHERE email = %s LIMIT 1",
            (email,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(payload: dict):
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode = payload.copy()
    to_encode.update({"exp": exp})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def decode_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
        ) from exc

@app.get("/health")
def health():
    return {
        "status": "ok",
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }

@app.post("/auth/register")
def register(payload: RegisterRequest):
    if get_user_by_email(payload.email):
        raise HTTPException(status_code=400, detail="Email ya está registrado")

    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        hashed = hash_password(payload.password)
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, password, activo)
            VALUES (%s, %s, %s, %s, 1)
        """, (payload.nombre, payload.apellido, payload.email, hashed))
        conn.commit()
    finally:
        conn.close()

    return {"message": "Usuario creado exitosamente"}

@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = get_user_by_email(payload.username)
    if not user or not verify_password(payload.password, user["password"]) or not user["activo"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    token_payload = {
        "sub": user["email"],
        "user_id": user["id"],
        "nombre": user["nombre"],
        "apellido": user["apellido"],
        "email": user["email"],
    }
    access_token = create_access_token(token_payload)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
        "id": user["id"],
        "username": user["email"],
        "nombre": user["nombre"],
        "apellido": user["apellido"],
        "email": user["email"],
        },
    }


@app.get("/auth/me")
def me(request: Request, token_data: str = Depends(security)):
    auth_header = request.headers.get("authorization", "")
    token_header = request.headers.get("x-access-token", "")

    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif token_header.lower().startswith("bearer "):
        token = token_header.split(" ", 1)[1].strip()
    else:
        token = token_header.strip()

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token faltante")

    payload = decode_token(token)
    return {
        "username": payload.get("sub"),
        "nombre": payload.get("nombre"),
        "apellido": payload.get("apellido"),
        "email": payload.get("email"),
    }

@app.get("/categorias")
def obtener_categorias():
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre FROM categorias ORDER BY nombre")
        return cursor.fetchall()
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error al traer categorías: {err.msg}")
    finally:
        conn.close()

@app.get("/prioridades")
def obtener_prioridades():
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nivel FROM prioridades ORDER BY nivel")
        return cursor.fetchall()
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error al traer prioridades: {err.msg}")
    finally:
        conn.close()

@app.post("/proyectos")
def crear_proyecto_manual(payload: ProyectoCrearRequest, request: Request, token_data: str = Depends(security)):
    auth_header = request.headers.get("authorization", "")
    token_header = request.headers.get("x-access-token", "")

    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif token_header.lower().startswith("bearer "):
        token = token_header.split(" ", 1)[1].strip()
    else:
        token = token_header.strip()

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token faltante")

    # Decodificar usando tu función existente
    user_payload = decode_token(token)
    creador_id = user_payload.get("user_id") # Sacamos el ID que metiste en el login

    if not creador_id:
        raise HTTPException(status_code=401, detail="Usuario no identificado en el token")

    # --- GUARDAR EN BASE DE DATOS ---
    codigo_invitacion = secrets.token_hex(3).upper() # Código random tipo F3A82C
    conn = get_db()
    try:
        cursor = conn.cursor()

        # Insertar proyecto
        cursor.execute("""
            INSERT INTO proyectos (titulo, descripcion, duracion_dias, codigo_invitacion, categoria_id, prioridad_id, creador_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            payload.titulo,
            payload.descripcion,
            payload.duracion_dias,
            codigo_invitacion,
            payload.categoria_id,
            payload.prioridad_id,
            creador_id
        ))
        
        proyecto_id = cursor.lastrowid

        # Vincular automáticamente al dueño como admin
        cursor.execute("""
            INSERT INTO proyecto_usuarios (proyecto_id, usuario_id, rol)
            VALUES (%s, %s, 'admin')
        """, (proyecto_id, creador_id))

        conn.commit()

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err.msg}")
    finally:
        conn.close()

    return {
        "status": "success",
        "proyecto_id": proyecto_id,
        "codigo_invitacion": codigo_invitacion,
        "mensaje": "Proyecto guardado exitosamente."
    }

@app.get("/columns")
def get_columns():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM columns ORDER BY id")
    data = cursor.fetchall()

    conn.close()
    return data

@app.get("/cards")
def get_cards():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.id,
            c.title,
            co.column_id,
            co.position
        FROM cards c
        JOIN card_order co ON c.id = co.card_id
        ORDER BY co.column_id, co.position
    """)

    data = cursor.fetchall()
    conn.close()
    return data

@app.post("/cards")
def create_card(card: dict):
    conn = get_db()
    cursor = conn.cursor()

    column_id = card.get("column_id", 1)

    # 🔹 calcular posición en card_order
    cursor.execute("""
        SELECT COALESCE(MAX(position), 0) + 1
        FROM card_order
        WHERE column_id = %s
    """, (column_id,))
    pos = cursor.fetchone()[0]

    # 🔹 crear card (SOLO title)
    cursor.execute("""
        INSERT INTO cards (title)
        VALUES (%s)
    """, (card["title"],))

    card_id = cursor.lastrowid  # 🔥 clave

    # 🔹 insertar en card_order
    cursor.execute("""
        INSERT INTO card_order (card_id, column_id, position)
        VALUES (%s, %s, %s)
    """, (card_id, column_id, pos))

    conn.commit()
    conn.close()

    return {"ok": True}

@app.patch("/cards/{card_id}/move")
def move_card(card_id: int, data: MoveCard):

    conn = get_db()
    cursor = conn.cursor()

    # nueva posición
    cursor.execute("""
        SELECT COALESCE(MAX(position),0)+1
        FROM card_order
        WHERE column_id = %s
    """, (data.column_id,))

    pos = cursor.fetchone()[0]

    # mover tarjeta
    cursor.execute("""
        UPDATE card_order
        SET column_id = %s,
            position = %s
        WHERE card_id = %s
    """, (data.column_id, pos, card_id))

    conn.commit()
    conn.close()

    return {"ok": True}


@app.post("/cards/reorder")
def reorder(data: dict):

    conn = get_db()
    cursor = conn.cursor()

    for i, card_id in enumerate(data["cards"]):
        cursor.execute("""
            UPDATE card_order
            SET position = %s
            WHERE card_id = %s
              AND column_id = %s
        """, (i + 1, card_id, data["column_id"]))

    conn.commit()
    conn.close()

    return {"ok": True}


@app.delete("/cards/{card_id}")
def delete_card(card_id: int):

    conn = get_db()
    cursor = conn.cursor()

    # borrar orden primero
    cursor.execute("""
        DELETE FROM card_order
        WHERE card_id = %s
    """, (card_id,))

    # borrar card
    cursor.execute("""
        DELETE FROM cards
        WHERE id = %s
    """, (card_id,))

    conn.commit()
    conn.close()

    return {"ok": True}