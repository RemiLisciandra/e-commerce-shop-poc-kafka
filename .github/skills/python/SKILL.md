---
name: python
description: >
  Rules and best practices for designing, building, and structuring a Python backend
  using FastAPI, Pydantic, and SQLAlchemy. Use this skill when creating new API endpoints,
  defining database models, creating Pydantic validation schemas, or structuring the project.
---

# FastAPI & Python — API Best Practices

## 📦 Installation & Setup

```bash
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic
```

Project Structure — Obligatoire
Never put all routes and logic in a single main.py. Follow this strict modular domain-driven structure:

Plaintext
app/
├── main.py          # Point d'entrée (init FastAPI, CORS, middlewares)
├── core/
│   ├── config.py    # Chargement des variables d'environnement (pydantic-settings)
│   └── security.py  # Hashing des mots de passe, JWT
├── api/
│   ├── deps.py      # Dépendances réutilisables (get_db, get_current_user)
│   └── routers/     # Les endpoints (ex: users.py, items.py)
├── models/          # Modèles SQLAlchemy (Database)
├── schemas/         # Modèles Pydantic (Input/Output API)
└── crud/            # Logique d'interaction avec la base de données
🔌 Database Dependency (Injection)
Never instantiate or query the database globally. Always use FastAPI's Depends system to yield a session and close it automatically.

Python
# app/api/deps.py
from typing import Generator
from app.db.session import SessionLocal

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close() # Garanti d'être exécuté, empêche les fuites de connexion
🧬 Modèles ORM vs Schemas (Pydantic)
Strictly separate Database Models (SQLAlchemy) from API Schemas (Pydantic).

Models (models/) represent the database tables.

Schemas (schemas/) validate what comes IN the API and filter what goes OUT.

Le Schema (Validation & Serialization)
Python
# app/schemas/user.py
from pydantic import BaseModel, EmailStr

# Input validation
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Output serialization (Response Model)
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True # Permet de lire depuis l'objet SQLAlchemy
Le Endpoint (Router)
Always define response_model to enforce data filtering (e.g., never leak the password hash).

Python
# app/api/routers/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserResponse
from app.api.deps import get_db
from app.crud import user as crud_user

router = APIRouter()

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    return crud_user.create(db=db, obj_in=user_in)
⚡ Concurrency : def vs async def
FastAPI handles concurrency differently based on how you declare your functions.

If your database driver is synchronous (e.g., standard psycopg2 or pymysql), use def. FastAPI will run it in an external threadpool.

If your database driver is asynchronous (e.g., asyncpg or aiomysql), use async def.

Python
# ✅ Bon pour SQLAlchemy synchrone classique
@router.get("/")
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()

# ❌ TRÈS MAUVAIS — Bloque l'Event Loop entière de FastAPI
@router.get("/")
async def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all() # Requête bloquante dans une fonction async !
🔒 Configuration & Sécurité
Never hardcode secrets. Always use pydantic-settings to load and validate .env files.

Python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "My API"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()
🧪 Testing avec TestClient
Always use FastAPI's TestClient alongside pytest for endpoint testing. Mock the database dependency.

Python
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_db

client = TestClient(app)

def override_get_db():
    # Retourne une session de DB de test
    yield test_db_session

app.dependency_overrides[get_db] = override_get_db

def test_create_user():
    response = client.post("/users/", json={"email": "test@test.com", "password": "pwd"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@test.com"
    assert "password" not in response.json() # Sécurité vérifiée
🛠️ Commandes utiles
Bash
uvicorn app.main:app --reload            # Démarre le serveur en mode dev (hot-reload)
ruff check . --fix                       # Linter : vérifie et corrige les erreurs de syntaxe
ruff format .                            # Formatter : aligne le style du code
alembic revision --autogenerate -m "msg" # Génère une migration de base de données
alembic upgrade head                     # Applique les migrations à la base
pytest                                   # Lance les tests
🚫 Hard Rules
Never write business logic directly inside the router/endpoint (use the crud/ folder).

Never return a SQLAlchemy model without passing it through a Pydantic response_model (prevents data leaks).

Never use global database connections; always use Depends(get_db).

Never put blocking I/O code (like a sync DB query or requests.get) inside an async def endpoint.

Always validate environment variables with pydantic-settings at startup.

Always enforce static typing (Type Hints) for function arguments and return types.