
"""
Módulo responsável por gerenciar contexto de notas fiscais no Redis.
"""
import logging
import time
from config.globals import redis_client
from app.rastreamento import detectar_tipo_rastreamento

logger = logging.getLogger(__name__)


def salvar_contexto_nf(sender: str, numero_nf: str, status: str, transportadora: str = '', codigo_rastreio: str = '', primeiro_nome: str = '', cep: str = ''):
    """
    Salva contexto de NF consultada no Redis.

    Args:
        sender: Número do remetente
        numero_nf: Número da nota fiscal
        status: Status da NF
        transportadora: Nome da transportadora
        codigo_rastreio: Código de rastreio (se disponível)
        primeiro_nome: Primeiro nome do destinatário
        cep: CEP do destinatário
    """
    tipo_rastreamento = detectar_tipo_rastreamento(transportadora)

    contexto = {
        'numero_nf': numero_nf,
        'status': status,
        'transportadora': transportadora,
        'codigo_rastreio': codigo_rastreio,
        'primeiro_nome': primeiro_nome,
        'cep': cep,
        'tipo_rastreamento': tipo_rastreamento,
        'timestamp': time.time()
    }

    redis_client.set(f"contexto_nf:{sender}", contexto, ex=600) 
    logger.info(f"Contexto NF salvo para {sender}: NF={numero_nf}, Status={status}, Transportadora={transportadora}, Tipo={tipo_rastreamento}")


def obter_contexto_nf(sender: str):
    """
    Obtém contexto da última NF consultada.

    Args:
        sender: Número do remetente

    Returns:
        Dict com contexto ou None
    """
    if not sender:
        return None

    contexto_key = f"contexto_nf:{sender}"
    contexto = redis_client.get(contexto_key)

    if contexto:
        logger.info(f"Contexto NF recuperado para {sender}: {contexto}")

    return contexto
