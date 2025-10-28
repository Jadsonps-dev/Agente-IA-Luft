"""
Módulo de APIs de transportadoras.
Gerencia integração com múltiplas transportadoras para rastreamento de pedidos.
"""
from api.base_transportadora import BaseTransportadora
from api.api_dialogo import DialogoTransportadora, dialogo
from api.api_magalog import MagalogTransportadora, magalog
from api.api_logan import LoganTransportadora, logan
from api.api_rede_sul import RedesulTransportadora, redesul

TRANSPORTADORAS = {
    'dialogo': dialogo,
    'magalog': magalog,
    'logan': logan,
    'redesul': redesul,
    'cooperativa': redesul
    # Adicione novas transportadoras aqui:
    # 'jadlog': jadlog,
    # 'correios': correios,
}


def obter_transportadora(nome: str) -> BaseTransportadora:
    """
    Obtém instância de uma transportadora pelo nome.

    Args:
        nome: Nome da transportadora (ex: 'dialogo', 'jadlog')

    Returns:
        Instância da transportadora

    Raises:
        ValueError: Se transportadora não estiver registrada
    """
    nome_lower = nome.lower()
    if nome_lower not in TRANSPORTADORAS:
        disponiveis = ', '.join(TRANSPORTADORAS.keys())
        raise ValueError(f"Transportadora '{nome}' não encontrada. Disponíveis: {disponiveis}")

    return TRANSPORTADORAS[nome_lower]


def rastrear_pedido(cpf: str, numero_fiscal: str, transportadora: str = 'dialogo') -> str:
    """
    Rastreia um pedido específico usando CPF do destinatário.

    Args:
        cpf: CPF do destinatário
        numero_fiscal: Número da nota fiscal
        transportadora: Nome da transportadora (padrão: 'dialogo')

    Returns:
        String formatada com rastreamento ou mensagem de erro
    """
    try:
        transp = obter_transportadora(transportadora)
        pedido = transp.buscar_pedido_especifico(cpf, numero_fiscal)

        if not pedido:
            return f"❌ Pedido {numero_fiscal} não encontrado no rastreamento da {transp.nome}"

        return transp.formatar_rastreamento(pedido)

    except ValueError as e:
        return f"{str(e)}"
    except Exception as e:
        return f"Erro ao rastrear pedido: {str(e)}"


__all__ = [
    'BaseTransportadora',
    'DialogoTransportadora',
    'MagalogTransportadora',
    'LoganTransportadora',
    'RedesulTransportadora',
    'dialogo',
    'magalog',
    'logan',
    'redesul',
    'TRANSPORTADORAS',
    'obter_transportadora',
    'rastrear_pedido'
]