
"""
Módulo principal de IA - Assistente de atendimento ao cliente.
Agente inteligente para WhatsApp.
"""
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv

from functions.analisador import analisar_pergunta_com_ia, PROMPTS
from functions.consultas import consultar_nota_fiscal_e_detectar_transportadora
from functions.rastreamento import eh_cpf, eh_codigo_rastreio, processar_rastreamento
from functions.contexto import obter_contexto_nf
from functions.ia_helpers import (
    verificar_interacao_usuario,
    obter_saudacao_inicial,
    limpar_formatacao_markdown,
    adicionar_mensagem_rastreamento,
    construir_contexto_nf
)

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def perguntar_ia(mensagem_usuario, instance=None, sender=None):
    """
    Função principal que processa perguntas do usuário com IA.

    Args:
        mensagem_usuario: Mensagem enviada pelo usuário
        instance: Instância do WhatsApp
        sender: Número do remetente

    Returns:
        Resposta formatada para o usuário
    """
    try:
        # Detecta CPF
        if eh_cpf(mensagem_usuario):
            logger.info("CPF detectado - processando rastreamento")
            return processar_rastreamento(mensagem_usuario, sender, tipo='cpf')

        # Detecta código de rastreio
        if eh_codigo_rastreio(mensagem_usuario):
            logger.info("Código de rastreio detectado - processando rastreamento")
            return processar_rastreamento(mensagem_usuario, sender, tipo='codigo')

        contexto = ""

        # Verifica se já interagiu
        ja_interagiu = verificar_interacao_usuario(sender)

        # Analisa a pergunta com IA
        analise_ia = analisar_pergunta_com_ia(mensagem_usuario)

        # Processa consulta de NF
        if analise_ia and analise_ia.get('tipo_consulta') == 'nota_fiscal':
            numero_nf = analise_ia.get('numero_nf')
            if numero_nf:
                logger.info(f"IA detectou busca de NF: {numero_nf}")
                dados_nf = consultar_nota_fiscal_e_detectar_transportadora(numero_nf, sender)
                contexto = construir_contexto_nf(dados_nf)

        # Saudação inicial
        if not ja_interagiu and not contexto:
            return obter_saudacao_inicial()

        # Gera resposta com IA
        prompt_template = PROMPTS['prompts']['assistente_resposta']['template']
        prompt = prompt_template.format(
            contexto=contexto if contexto else "Responda de forma objetiva à pergunta do cliente.",
            pergunta_cliente=mensagem_usuario
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )

        content = response.choices[0].message.content

        if content:
            content = limpar_formatacao_markdown(content)
            content = adicionar_mensagem_rastreamento(content, contexto, sender)
            return content

        return "Não foi possível gerar uma resposta."

    except Exception as e:
        logger.error(f"Erro ao consultar IA: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."


def consultar_nota_fiscal_wms(numero_nf: str, empresa: str = None, id_depositante: str = None, sender: str = None):
    """
    Wrapper para consultar_nota_fiscal que inclui o sender para salvar contexto.
    """
    dados_nf = consultar_nota_fiscal_e_detectar_transportadora(numero_nf, sender)
    return dados_nf
