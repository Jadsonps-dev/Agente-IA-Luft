"""
Módulo principal de IA - Assistente de atendimento ao cliente.
"""
from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
import time
from datetime import datetime
from config.globals import redis_client
from app.analisador import analisar_pergunta_com_ia, PROMPTS
from app.consultas import consultar_nota_fiscal_e_detectar_transportadora
from app.rastreamento import eh_cpf, eh_codigo_rastreio, processar_rastreamento
from app.contexto import obter_contexto_nf

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
        ja_interagiu = False
        if sender:
            historico_key = f"historico:{sender}"
            historico = redis_client.get(historico_key)
            if historico:
                ja_interagiu = True
            redis_client.set(historico_key, {"interagiu": True}, ex=3600)

        # Analisa a pergunta com IA
        analise_ia = analisar_pergunta_com_ia(mensagem_usuario)

        # Processa consulta de NF
        if analise_ia and analise_ia.get('tipo_consulta') == 'nota_fiscal':
            numero_nf = analise_ia.get('numero_nf')
            if numero_nf:
                logger.info(f"IA detectou busca de NF: {numero_nf}")
                dados_nf = consultar_nota_fiscal_e_detectar_transportadora(numero_nf, sender)

                if dados_nf and dados_nf.get('encontrado'):
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
                        from app.rastreamento import detectar_tipo_rastreamento
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
                elif dados_nf and not dados_nf.get('encontrado'):
                    contexto = f"""
                        A nota fiscal {numero_nf} não foi encontrada no sistema.
                        Pode ser que o número esteja incorreto ou o pedido ainda não foi processado.
                    """
                else:
                    contexto = """
                        Houve um problema ao consultar o sistema. Por favor, tente novamente em alguns instantes.
                    """

        # Saudação inicial
        if not ja_interagiu and not contexto:
            hora_atual = datetime.now().hour
            saudacao = "Boa tarde" if 12 <= hora_atual < 18 else "Bom dia" if hora_atual < 12 else "Boa noite"
            return PROMPTS['prompts']['saudacao_inicial']['template'].format(saudacao=saudacao)

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
            content = content.replace("**", "").replace("*", "").replace("__", "")
            content = content.strip()

            # Adiciona mensagem de rastreamento se necessário
            if "AÇÃO OBRIGATÓRIA" in contexto and "📍 Deseja rastrear" not in content:
                if sender and analise_ia and analise_ia.get('tipo_consulta') == 'nota_fiscal':
                    ctx_temp = obter_contexto_nf(sender)
                    if ctx_temp:
                        tipo_rastreamento = ctx_temp.get('tipo_rastreamento', 'cpf')
                        codigo_rastreio = ctx_temp.get('codigo_rastreio', '')
                        transportadora_ctx = ctx_temp.get('transportadora', '').lower()

                        if tipo_rastreamento == 'codigo' and codigo_rastreio:
                            content += f"\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o código de rastreio: {codigo_rastreio}"
                        elif 'logan' in transportadora_ctx:
                            content += "\n\n📍 Deseja rastrear seu pedido em tempo real?\n\n✉️ Envie o *CPF do destinatário* para acompanhar a entrega."
                        else:
                            content += "\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."
                    else:
                        content += "\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."

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