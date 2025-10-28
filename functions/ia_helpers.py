"""
Funções auxiliares para processamento de IA.
Separadas do módulo principal para melhor organização.
"""
import logging
from datetime import datetime
from config.globals import redis_client

logger = logging.getLogger(__name__)


def verificar_interacao_usuario(sender: str) -> bool:
    """
    Verifica se o usuário já interagiu anteriormente.

    Args:
        sender: Número do remetente

    Returns:
        True se já interagiu, False caso contrário
    """
    if not sender:
        return False

    historico_key = f"historico:{sender}"
    historico = redis_client.get(historico_key)

    if historico:
        return True

    redis_client.set(historico_key, {"interagiu": True}, ex=3600)
    return False


def obter_saudacao_inicial() -> str:
    """
    Retorna saudação inicial baseada no horário.

    Returns:
        String com saudação formatada
    """
    from functions.analisador import PROMPTS

    hora_atual = datetime.now().hour
    saudacao = "Boa tarde" if 12 <= hora_atual < 18 else "Bom dia" if hora_atual < 12 else "Boa noite"

    return PROMPTS['prompts']['saudacao_inicial']['template'].format(saudacao=saudacao)


def limpar_formatacao_markdown(texto: str) -> str:
    """
    Remove formatação markdown do texto.

    Args:
        texto: Texto com formatação markdown

    Returns:
        Texto limpo sem formatação
    """
    if not texto:
        return texto

    texto = texto.replace("**", "").replace("*", "").replace("__", "")
    return texto.strip()


def adicionar_mensagem_rastreamento(content: str, contexto: str, sender: str) -> str:
    """
    Adiciona mensagem solicitando CPF ou código de rastreio quando NF é EXPEDIDO.

    Args:
        content: Conteúdo da resposta
        contexto: Contexto da consulta
        sender: Número do remetente

    Returns:
        Conteúdo com mensagem adicional se necessário
    """
    # Evita adicionar mensagem se já existe no conteúdo
    if "📍 Deseja rastrear" in content:
        return content
    
    if "EXPEDIDO" in contexto and sender:
        from functions.contexto import obter_contexto_nf
        ctx = obter_contexto_nf(sender)

        if ctx:
            tipo_rastreamento = ctx.get('tipo_rastreamento', 'cpf')
            codigo_rastreio = ctx.get('codigo_rastreio', '')

            if tipo_rastreamento == 'correios':
                content += f"\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o código de rastreio."
            elif tipo_rastreamento == 'codigo' and codigo_rastreio:
                content += f"\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o código de rastreio."
            else:
                content += f"\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."

    return content


def construir_contexto_nf(dados_nf: dict) -> str:
    """
    Constrói string de contexto a partir dos dados da NF.

    Args:
        dados_nf: Dicionário com dados da nota fiscal

    Returns:
        String formatada com contexto
    """
    if not dados_nf or not dados_nf.get('encontrado'):
        if dados_nf:
            numero_nf = dados_nf.get('numero_nf', 'informado')
            return f"""
                A nota fiscal {numero_nf} não foi encontrada no sistema.
                Pode ser que o número esteja incorreto ou o pedido ainda não foi processado.
            """
        return """
            Houve um problema ao consultar o sistema. Por favor, tente novamente em alguns instantes.
        """

    status_nf = dados_nf['status']
    transportadora_nf = dados_nf.get('transportadora', '')
    codigo_rastreio_nf = dados_nf.get('codigo_rastreio', '')

    contexto = f"""
        INFORMAÇÕES DA NOTA FISCAL {dados_nf['numero_nf']}:
        - Status: {status_nf}
        - Transportadora: {transportadora_nf}
        - Código de Rastreio: {codigo_rastreio_nf}
    """

    if status_nf == 'EXPEDIDO':
        from functions.rastreamento import detectar_tipo_rastreamento
        tipo_rastreamento = detectar_tipo_rastreamento(transportadora_nf)
        transportadora_lower = transportadora_nf.lower()

        if tipo_rastreamento == 'codigo':
            if codigo_rastreio_nf and codigo_rastreio_nf != 'Não disponível':
                mensagem_rastreamento = f"📍 Deseja rastrear seu pedido em tempo real? Basta enviar o código de rastreio abaixo:\n\n🔢 Código: {codigo_rastreio_nf}"
            else:
                mensagem_rastreamento = "📍 Para rastrear seu pedido, envie o código de rastreio fornecido pela transportadora."
        elif 'logan' in transportadora_lower:
            mensagem_rastreamento = "📍 Deseja rastrear seu pedido em tempo real?\n\n✉️ Envie o *CPF do destinatário* para acompanhar a entrega."
        else:
            mensagem_rastreamento = "📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."

        contexto += f"""

        ⚠️ AÇÃO OBRIGATÓRIA - O pedido está EXPEDIDO:
        Você DEVE incluir na sua resposta a seguinte mensagem EXATAMENTE como está escrito:

        "{mensagem_rastreamento}"

        Esta mensagem deve aparecer AO FINAL da sua resposta, após as informações da nota fiscal.
        NÃO OMITA esta mensagem. É OBRIGATÓRIO incluí-la.
        """

    return contexto