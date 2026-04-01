from datetime import datetime, timedelta, timezone
import os

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
import bcrypt
import mysql.connector
from pydantic import BaseModel

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


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def get_user_by_username(username: str):
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, username, nombre, apellido, password, email, activo FROM usuarios WHERE username = %s LIMIT 1",
            (username,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


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
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user["password"]) or not user["activo"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    token_payload = {
        "sub": user["username"],
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
            "username": user["username"],
            "nombre": user["nombre"],
            "apellido": user["apellido"],
            "email": user["email"],
        },
    }


@app.get("/auth/me")
def me(request: Request):
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
