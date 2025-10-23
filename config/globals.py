import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from redisdbt import RedisClient
from utils.evolutionAPI import EvolutionAPI


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

evolution = EvolutionAPI()
redis_client = RedisClient()

database_url = os.getenv("DATABASE_URL")

if database_url and database_url.startswith("DATABASE_URL="):
    database_url = database_url.split("=", 1)[1]

DATABASE_URL = (
    database_url
    or "postgresql+psycopg2://luftsolutions:luft@2025@172.34.6.218:5333/luft"
)

DB_CONFIG = {
    'host': '172.34.6.218',
    'database': 'luft',
    'user': 'luftsolutions',
    'password': 'luft@2025',
    'port': 5333
}

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


API_BASE_URL = 'http://200.143.168.151:8880/siltwms/webresources'

API_CONFIG = {
    'BASE_URL': API_BASE_URL,
    'LOGIN_URL': f'{API_BASE_URL}/SessionService/login',
    'GRID_URL': f'{API_BASE_URL}/GridService/getDinamicGridSql',
    'headers': {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko)'
        ),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
    'login_data': {
        "nomeUsuario": "EDGAR.MARQUES",
        "password": "101876",
        "armazem": {
            "id": 7,
            "descricao": "LUFT SOLUTIONS - AG2 - CAJAMAR - 16"
        }
    }
}