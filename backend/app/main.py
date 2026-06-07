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
from openai import OpenAI
import json
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
    email: str
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

class UnirseProyectoRequest(BaseModel):
    codigo_invitacion: str

class ActualizarTareaRequest(BaseModel):
    titulo: str
    descripcion: str
    usuario_asignado_id: int | None = None

class TareaFinalRequest(BaseModel):
    nombre: str
    descripcion: str
    dias_estimados: int
    rol_sugerido: str
    usuario_asignado_id: int | None

class ConfirmarProyectoRequest(BaseModel):
    titulo: str
    descripcion: str
    duracion_dias: int
    categoria_id: int
    prioridad_id: int
    cantidad_participantes: int
    tareas: list[TareaFinalRequest]

class ActualizarProyectoCompletoRequest(BaseModel):
    titulo: str
    descripcion: str
    duracion_dias: int
    categoria_id: int
    prioridad_id: int
    tareas: list[TareaFinalRequest]

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
    user = get_user_by_email(payload.email)
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

@app.get("/proyectos")
def listar_mis_proyectos(request: Request, token_data: str = Depends(security)):
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
    user_email = payload.get("email")
    
    conn = get_db() 
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (user_email,))
        usuario = cursor.fetchone()
        
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
        usuario_id = usuario["id"]

        query = """
            SELECT p.id, p.titulo, p.descripcion, p.codigo_invitacion, 
                   p.fecha_creacion, p.categoria_id, p.prioridad_id, 
                   p.duracion_dias, pu.rol
            FROM proyectos p
            INNER JOIN proyecto_usuarios pu ON p.id = pu.proyecto_id
            WHERE pu.usuario_id = %s
            ORDER BY p.fecha_creacion DESC
        """
        cursor.execute(query, (usuario_id,))
        mis_proyectos = cursor.fetchall()

        return mis_proyectos

    except Exception as e:
        print(f"Error al listar proyectos: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
        
    finally:
        cursor.close()
        conn.close()

@app.post("/ia/analizar-proyecto")
async def analizar_proyecto_ia(proyecto: ProyectoCrearRequest, request: Request, token_data: str = Depends(security)):

    auth_header = request.headers.get("authorization", "")
    token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else ""
    
    if not token:
        raise HTTPException(status_code=401, detail="Token faltante")
    
    decode_token(token) 

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta la configuración de OPENAI_API_KEY en el servidor.")
        
    try:
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Sos un experto en gestión de proyectos informáticos. Desglosá el siguiente proyecto en tareas lógicas y alcanzables.

        Proyecto: {proyecto.titulo}
        Descripción: {proyecto.descripcion}
        Duración estimada del proyecto total: {proyecto.duracion_dias} días
        Cantidad de integrantes en el equipo: {proyecto.cantidad_participantes}

        Respondé SOLO con JSON válido (un array de objetos), sin formateo markdown ni bloques de código.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Solo devolvé JSON válido (un array de objetos). Cada objeto representa una tarea y debe contener obligatoriamente las llaves string exactas en minúscula: 'nombre', 'descripcion', 'dias_estimados' y 'rol_sugerido'."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        respuesta_cruda = response.choices[0].message.content.strip()
        
        if respuesta_cruda.startswith("```"):
            lineas = respuesta_cruda.splitlines()
            if lineas[0].startswith("```"):
                lineas.pop(0)
            if lineas and lineas[-1].startswith("```"):
                lineas.pop()
            respuesta_cruda = "\n".join(lineas).strip()

        lista_tareas = json.loads(respuesta_cruda)

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="La IA no mandó un JSON limpio.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar con OpenAI: {str(e)}")

    return {
        "status": "preview",
        "titulo_proyecto": proyecto.titulo,
        "descripcion_proyecto": proyecto.descripcion,
        "duracion_dias": proyecto.duracion_dias,
        "categoria_id": proyecto.categoria_id,
        "prioridad_id": proyecto.prioridad_id,
        "tareas_sugeridas": lista_tareas
    }

@app.post("/proyectos/confirmar")
async def confirmar_y_guardar_proyecto(payload: ConfirmarProyectoRequest, request: Request, token_data: str = Depends(security)):

    auth_header = request.headers.get("authorization", "")
    token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else ""

    if not token:
        raise HTTPException(status_code=401, detail="Token faltante")

    user_payload = decode_token(token)
    creador_id = user_payload.get("user_id")        

    if not creador_id:
        raise HTTPException(status_code=401, detail="Usuario no identificado en el token")

    codigo_invitacion = secrets.token_hex(3).upper()
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)

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

        cursor.execute("""
            INSERT INTO proyecto_usuarios (proyecto_id, usuario_id, rol)
            VALUES (%s, %s, 'admin')
        """, (proyecto_id, creador_id))

        for tarea in payload.tareas:
            cursor.execute("""
                INSERT INTO tareas (proyecto_id, titulo, descripcion, dias_estimados, rol_sugerido, asignado_usuario_id, estado)
                VALUES (%s, %s, %s, %s, %s, NULL, 'pendiente')
            """, (
                proyecto_id,
                tarea.nombre,
                tarea.descripcion,
                tarea.dias_estimados,
                tarea.rol_sugerido
            ))

        conn.commit()

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos al guardar: {err.msg}")
    finally:
        conn.close()

    return {
        "status": "success",
        "proyecto_id": proyecto_id,
        "codigo_invitacion": codigo_invitacion,
        "mensaje": "Proyecto y tareas editadas guardados correctamente."
    }

@app.get("/proyectos/{proyecto_id}/tareas")
def obtener_tareas_e_integrantes(proyecto_id: int, request: Request, token_data: str = Depends(security)):
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
        raise HTTPException(status_code=401, detail="Token faltante")

    decode_token(token)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        query_tareas = """
            SELECT id, titulo, descripcion, dias_estimados, rol_sugerido, estado, asignado_usuario_id 
            FROM tareas 
            WHERE proyecto_id = %s
        """
        cursor.execute(query_tareas, (proyecto_id,))
        tareas = cursor.fetchall()

        query_integrantes = """
            SELECT u.id, u.nombre, u.apellido, u.email, pu.rol
            FROM usuarios u
            INNER JOIN proyecto_usuarios pu ON u.id = pu.usuario_id
            WHERE pu.proyecto_id = %s
        """
        cursor.execute(query_integrantes, (proyecto_id,))
        integrantes = cursor.fetchall()

        return {
            "proyecto_id": proyecto_id,
            "tareas": tareas,
            "integrantes": integrantes
        }
    except Exception as e:
        print(f"Error al recuperar info del proyecto {proyecto_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al consultar la base de datos")
    finally:
        cursor.close()
        conn.close()

@app.post("/proyectos/unirse")
def unirse_a_proyecto(payload: UnirseProyectoRequest, request: Request, token_data: str = Depends(security)):
    # 🔑 VALIDACIÓN DE TOKEN
    auth_header = request.headers.get("authorization", "")
    token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Token faltante")

    user_payload = decode_token(token)
    usuario_id = user_payload.get("user_id")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Buscar si el proyecto existe con ese código
        cursor.execute("SELECT id FROM proyectos WHERE codigo_invitacion = %s LIMIT 1", (payload.codigo_invitacion,))
        proyecto = cursor.fetchone()
        if not proyecto:
            raise HTTPException(status_code=404, detail="Código de invitación inválido o no existe.")
        
        proyecto_id = proyecto["id"]

        cursor.execute("""
            SELECT id FROM proyecto_usuarios 
            WHERE proyecto_id = %s AND usuario_id = %s LIMIT 1
        """, (proyecto_id, usuario_id))
        
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Ya formas parte de este proyecto.")

        cursor.execute("""
            INSERT INTO proyecto_usuarios (proyecto_id, usuario_id, rol)
            VALUES (%s, %s, 'miembro')
        """, (proyecto_id, usuario_id))
        conn.commit()

        return {"status": "success", "message": "Te uniste al proyecto correctamente."}

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {err.msg}")
    finally:
        cursor.close()
        conn.close()

@app.put("/tareas/{tarea_id}")
def actualizar_tarea(tarea_id: int, payload: ActualizarTareaRequest, request: Request, token_data: str = Depends(security)):

    auth_header = request.headers.get("authorization", "")
    token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Token faltante")

    user_payload = decode_token(token)
    usuario_id = user_payload.get("user_id")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
    
        cursor.execute("SELECT proyecto_id FROM tareas WHERE id = %s LIMIT 1", (tarea_id,))
        tarea = cursor.fetchone()
        if not tarea:
            raise HTTPException(status_code=404, detail="La tarea no existe.")
        
        proyecto_id = tarea["proyecto_id"]

      
        cursor.execute("""
            SELECT rol FROM proyecto_usuarios 
            WHERE proyecto_id = %s AND usuario_id = %s LIMIT 1
        """, (proyecto_id, usuario_id))
        rol_usuario = cursor.fetchone()

        if not rol_usuario or rol_usuario["rol"] != "admin":
            raise HTTPException(status_code=403, detail="Permiso denegado. Solo el administrador puede modificar tareas.")


        cursor.execute("""
            UPDATE tareas 
            SET titulo = %s, descripcion = %s, asignado_usuario_id = %s
            WHERE id = %s
        """, (payload.titulo, payload.descripcion, payload.usuario_asignado_id, tarea_id))
        conn.commit()

        return {"status": "success", "message": "Tarea actualizada de forma exitosa."}

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos al actualizar: {err.msg}")
    finally:
        cursor.close()
        conn.close()

@app.put("/proyectos/{proyecto_id}/actualizar")
def actualizar_proyecto_y_tareas(proyecto_id: int, payload: ActualizarProyectoCompletoRequest, request: Request, token_data: str = Depends(security)):

    auth_header = request.headers.get("authorization", "")
    token = auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else ""
    if not token:
        raise HTTPException(status_code=401, detail="Token faltante")

    user_payload = decode_token(token)
    usuario_id = user_payload.get("user_id")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
    
        cursor.execute("""
            SELECT rol FROM proyecto_usuarios 
            WHERE proyecto_id = %s AND usuario_id = %s LIMIT 1
        """, (proyecto_id, usuario_id))
        rol_usuario = cursor.fetchone()

        if not rol_usuario or rol_usuario["rol"] != "admin":
            raise HTTPException(status_code=403, detail="Permiso denegado. Solo el administrador puede modificar el proyecto.")

        cursor.execute("""
            UPDATE proyectos 
            SET titulo = %s, descripcion = %s, duracion_dias = %s, categoria_id = %s, prioridad_id = %s
            WHERE id = %s
        """, (payload.titulo, payload.descripcion, payload.duracion_dias, payload.categoria_id, payload.prioridad_id, proyecto_id))

        cursor.execute("DELETE FROM tareas WHERE proyecto_id = %s", (proyecto_id,))

        for tarea in payload.tareas:
            cursor.execute("""
                INSERT INTO tareas (proyecto_id, titulo, descripcion, dias_estimados, rol_sugerido, asignado_usuario_id, estado)
                VALUES (%s, %s, %s, %s, %s, %s, 'pendiente') 
            """, (
                proyecto_id,
                tarea.nombre,
                tarea.descripcion,
                tarea.dias_estimados,
                tarea.rol_sugerido,
                tarea.usuario_asignado_id  
            ))

        conn.commit()
        return {"status": "success", "message": "Proyecto y tareas actualizados correctamente de forma masiva."}

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {err.msg}")
    finally:
        cursor.close()
        conn.close()
