from services.database import get_db_connection
from utils.evolutionAPI import EvolutionAPI
from config.globals import SessionLocal
from psycopg2 import sql
from ia import perguntar_ia
from redisdbt import RedisClient
from sqlalchemy import text
import json
import time
import re
import traceback
from config.globals import SessionLocal, evolution, redis_client

evolution = EvolutionAPI()
redis_client = RedisClient()

def desativar_via_redis(instance_name):
    redis_client.set(f"webhook_desativado:{instance_name}", "1")
    print(f"🔴 Instância {instance_name} DESATIVADA via comando.")
    return {"message": f"🔴 Webhook da instância {instance_name} desativado via Redis."}

def ativar_via_redis(instance_name):
    redis_client.delete(f"webhook_desativado:{instance_name}")
    print(f"🟢 Instância {instance_name} ATIVADA via comando.")
    return {"message": f"🟢 Webhook da instância {instance_name} reativado via Redis."}

def padronizar_numero(numero):
    numero_limpo = re.sub(r'\D', '', numero)
    if not numero_limpo.startswith('55'):
        numero_limpo = '55' + numero_limpo
    return numero_limpo