from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
import re
import json
from datetime import datetime, timedelta
import time
from services.wms import EstruturaSQL
from services.query import Queries
from config.globals import redis_client
from api import rastrear_pedido

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ID_DEPOSITANTES = [2361178, 538607]

with open('docs/wms_documentation.json', 'r', encoding='utf-8') as f:
    API_DOCS = json.load(f)

with open('docs/prompts_sistema.json', 'r', encoding='utf-8') as f:
    PROMPTS = json.load(f)

with open('docs/query_consulta_nf_learning.json', 'r', encoding='utf-8') as f:
    LEARNING_NF = json.load(f)

# LEARNING_OP removido - apenas consulta de NF


def analisar_pergunta_com_ia(mensagem_usuario):
    """
    Usa OpenAI para analisar a pergunta do usuário e determinar como fazer a consulta.
    Retorna instruções estruturadas baseadas na documentação da API.
    """
    try:
        tools = [{
            "type": "function",
            "function": {
                "name": "consultar_nota_fiscal_wms",
                "description":
                "Busca informações de uma nota fiscal específica no WMS da Luft Solutions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo_consulta": {
                            "type":
                            "string",
                            "enum": ["nota_fiscal"],
                            "description":
                            "Tipo de consulta - sempre 'nota_fiscal'"
                        },
                        "numero_nf": {
                            "type":
                            "string",
                            "description":
                            "Número da nota fiscal fornecido pelo usuário"
                        },
                        "empresa": {
                            "type":
                            "string",
                            "enum": ["Insider", "Alpargatas", "todas"],
                            "description":
                            "Nome da empresa mencionada: Insider, Alpargatas ou todas"
                        },
                        "id_depositante": {
                            "type":
                            "string",
                            "enum": ["2361178", "538607"],
                            "description":
                            "ID do depositante: 2361178=Insider | 538607=Alpargatas"
                        }
                    },
                    "required": ["tipo_consulta", "numero_nf"]
                }
            }
        }]

        documentacao_completa = {
            "api_wms": API_DOCS,
            "aprendizado_query_nf": LEARNING_NF
        }

        prompt_template = PROMPTS['prompts']['analisador_consultas']['template']
        prompt = prompt_template.format(
            documentacao_api=json.dumps(documentacao_completa, indent=2, ensure_ascii=False),
            pergunta_usuario=mensagem_usuario
        )

        response = client.chat.completions.create(model="gpt-4o-mini",
                                                  messages=[{
                                                      "role": "user",
                                                      "content": prompt
                                                  }],
                                                  tools=tools,
                                                  tool_choice="auto")

        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            argumentos = json.loads(tool_call.function.arguments)
            logger.info(f"OpenAI analisou: {argumentos}")
            return argumentos

        return None

    except Exception as e:
        logger.error(f"Erro ao analisar pergunta com IA: {str(e)}")
        return None


def extrair_data_mensagem(mensagem):
    """
    Extrai a data da mensagem do usuário e retorna data_inicio e data_fim.
    """
    hoje = datetime.now()
    mensagem_lower = mensagem.lower()

    if 'hoje' in mensagem_lower:
        data_inicio = hoje.strftime("%d/%m/%Y")
        data_fim = hoje.strftime("%d/%m/%Y")
    elif 'ontem' in mensagem_lower:
        ontem = hoje - timedelta(days=1)
        data_inicio = ontem.strftime("%d/%m/%Y")
        data_fim = ontem.strftime("%d/%m/%Y")
    elif 'semana' in mensagem_lower or 'últimos 7 dias' in mensagem_lower:
        data_inicio = (hoje - timedelta(days=7)).strftime("%d/%m/%Y")
        data_fim = hoje.strftime("%d/%m/%Y")
    elif 'mês' in mensagem_lower or 'mes' in mensagem_lower or 'últimos 30 dias' in mensagem_lower:
        data_inicio = (hoje - timedelta(days=30)).strftime("%d/%m/%Y")
        data_fim = hoje.strftime("%d/%m/%Y")
    else:
        padrao_data = r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})'
        match = re.search(padrao_data, mensagem)
        if match:
            dia, mes, ano = match.groups()
            if len(ano) == 2:
                ano = f"20{ano}"
            data_inicio = f"{dia.zfill(2)}/{mes.zfill(2)}/{ano}"
            data_fim = data_inicio
        else:
            data_inicio = hoje.strftime("%d/%m/%Y")
            data_fim = hoje.strftime("%d/%m/%Y")

    return data_inicio, data_fim

def consultar_nota_fiscal(numero_nf):
    """
    Consulta informações da nota fiscal via API WMS em múltiplos depositantes.
    Tenta primeiro no depositante 2361178, se não encontrar, tenta no 538607.
    Retorna os dados formatados ou None em caso de erro.
    """
    # Limpar o número da NF removendo traços, espaços e outros caracteres especiais
    numero_nf = re.sub(r'[^0-9]', '', str(numero_nf))

    if not numero_nf:
        logger.warning("Número da NF vazio após limpeza")
        return {'encontrado': False, 'numero_nf': 'inválido'}

    data_fim = datetime.now().strftime("%d/%m/%Y")
    data_inicio = (datetime.now() - timedelta(days=90)).strftime("%d/%m/%Y")

    for id_depositante in ID_DEPOSITANTES:
        estrutura = None
        try:
            logger.info(
                f"Consultando nota fiscal {numero_nf} no depositante {id_depositante}"
            )

            sql_query = Queries.query_status_nf(id_depositante, numero_nf)
            estrutura = EstruturaSQL(id_depositante, sql_query)

            resposta_api = estrutura.fazer_requisicao_api(
                data_inicio, data_fim)

            if not resposta_api:
                logger.warning(
                    f"Nenhuma resposta da API para NF {numero_nf} no depositante {id_depositante}"
                )
                continue

            value = resposta_api.get('value', {})
            lines = value.get('lines', [])

            if lines and len(lines) > 0:
                primeira_linha = lines[0]
                columns = primeira_linha.get('columns', [])

                if len(columns) >= 4:
                    dados_nf = {
                        'encontrado': True,
                        'numero_nf': columns[0],
                        'status': columns[1],
                        'transportadora':
                        columns[2] if columns[2] else 'Não informada',
                        'codigo_rastreio':
                        columns[3] if columns[3] else 'Não disponível',
                        'id_depositante': id_depositante
                    }

                    logger.info(
                        f"Dados da NF {numero_nf} encontrados no depositante {id_depositante}"
                    )
                    return dados_nf

            logger.info(
                f"NF {numero_nf} não encontrada no depositante {id_depositante}, tentando próximo..."
            )

        except Exception as e:
            logger.error(
                f"Erro ao consultar NF {numero_nf} no depositante {id_depositante}: {str(e)}"
            )
            continue
        finally:
            if estrutura is not None:
                estrutura.fechar_sessao()

    logger.warning(
        f"NF {numero_nf} não encontrada em nenhum dos depositantes")
    return {'encontrado': False, 'numero_nf': numero_nf}


def eh_cpf(mensagem: str) -> bool:
    """
    Detecta se a mensagem é um CPF (com ou sem pontuação).

    Args:
        mensagem: Texto da mensagem

    Returns:
        True se é um CPF válido
    """
    # Remove pontuação
    cpf_limpo = re.sub(r'\D', '', mensagem.strip())

    # CPF deve ter 11 dígitos
    if len(cpf_limpo) == 11 and cpf_limpo.isdigit():
        logger.info(f"✅ CPF detectado: {cpf_limpo}")
        return True

    return False


def eh_codigo_rastreio(mensagem: str) -> bool:
    """
    Detecta se uma mensagem é um código de rastreio.
    Geralmente são códigos alfanuméricos (letras + números).

    Args:
        mensagem: Mensagem do usuário

    Returns:
        True se parecer um código de rastreio
    """
    # Remove espaços e pontuação
    codigo = mensagem.strip().upper()

    # Código de rastreio geralmente tem letras e números, entre 10-20 caracteres
    # Exemplos: "BR123456789BR", "AA123456789BR", etc
    if 8 <= len(codigo) <= 25:
        tem_letra = any(c.isalpha() for c in codigo)
        tem_numero = any(c.isdigit() for c in codigo)

        if tem_letra and tem_numero:
            logger.info(f"✅ Código de rastreio detectado: {codigo}")
            return True

    return False


def salvar_contexto_nf(sender: str, numero_nf: str, status: str, transportadora: str = '', codigo_rastreio: str = ''):
    """
    Salva contexto de NF consultada no Redis.

    Args:
        sender: Número do remetente
        numero_nf: Número da nota fiscal
        status: Status da NF
        transportadora: Nome da transportadora
        codigo_rastreio: Código de rastreio (se disponível)
    """
    contexto = {
        'numero_nf': numero_nf,
        'status': status,
        'transportadora': transportadora,
        'codigo_rastreio': codigo_rastreio,
        'timestamp': time.time()
    }

    redis_client.set(f"contexto_nf:{sender}", contexto, ex=600)  # Expira em 10 minutos
    logger.info(f"💾 Contexto NF salvo para {sender}: NF={numero_nf}, Status={status}, Transportadora={transportadora}, Código={codigo_rastreio}")


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
        logger.info(f"📖 Contexto NF recuperado para {sender}: {contexto}")

    return contexto


def processar_rastreamento(mensagem: str, sender: str, tipo: str) -> str:
    """
    Processa o rastreamento com base no tipo (CPF ou código de rastreio).

    Args:
        mensagem: Mensagem do usuário contendo CPF ou código.
        sender: Número do remetente.
        tipo: 'cpf' ou 'codigo'.

    Returns:
        Mensagem formatada com rastreamento ou erro.
    """
    try:
        contexto = obter_contexto_nf(sender)

        if not contexto:
            if tipo == 'cpf':
                return "❌ Para rastrear seu pedido, primeiro consulte o número da nota fiscal e depois envie seu CPF."
            else:
                return "❌ Para rastrear seu pedido, primeiro consulte o número da nota fiscal e depois envie o código de rastreio."

        numero_nf = contexto.get('numero_nf')
        status = contexto.get('status', '')
        transportadora_nome = contexto.get('transportadora', '')
        codigo_rastreio_contexto = contexto.get('codigo_rastreio', '')

        if status != 'EXPEDIDO':
            return f"❌ O pedido {numero_nf} não está com status EXPEDIDO. Status atual: {status}"

        resultado = ""
        transportadora_key = ''

        if tipo == 'cpf':
            if not transportadora_nome:
                return "❌ Não foi possível determinar a transportadora para rastreamento."

            transportadora_lower = transportadora_nome.lower()
            if 'dialogo' in transportadora_lower or 'diálogo' in transportadora_lower:
                transportadora_key = 'dialogo'
            else:
                # Outras transportadoras que pedem CPF
                transportadora_key = 'dialogo' # Padrão se não for Magalog
            logger.info(f"🔍 Rastreando NF {numero_nf} com CPF fornecido via {transportadora_key}")
            resultado = rastrear_pedido(mensagem, numero_nf, transportadora=transportadora_key)

        elif tipo == 'codigo':
            if not codigo_rastreio_contexto:
                return "❌ Não há código de rastreio associado a este pedido no momento."

            transportadora_lower = transportadora_nome.lower()
            if 'magalog' in transportadora_lower:
                transportadora_key = 'magalog'
                logger.info(f"🔍 Rastreando NF {numero_nf} com código de rastreio {codigo_rastreio_contexto} via {transportadora_key}")
                resultado = rastrear_pedido(codigo_rastreio_contexto, numero_nf, transportadora=transportadora_key)
            else:
                # Se não for Magalog, mas o usuário enviou código, pode ser um erro ou outra transportadora não suportada.
                # Por enquanto, tratamos como erro ou informamos que não é o esperado.
                return f"❌ O código de rastreio fornecido não é esperado para a transportadora {transportadora_nome}. Por favor, envie o CPF do destinatário."

        # Limpa contexto após usar
        redis_client.delete(f"contexto_nf:{sender}")

        return resultado

    except Exception as e:
        logger.error(f"❌ Erro ao processar rastreamento: {str(e)}")
        return "❌ Erro ao buscar rastreamento. Tente novamente em alguns instantes."


def perguntar_ia(mensagem_usuario, instance=None, sender=None):
    try:
        # PRIORIDADE 1: Detectar CPF ou Código de Rastreio ANTES de qualquer outra análise
        if eh_cpf(mensagem_usuario):
            logger.info("🎯 CPF detectado - processando rastreamento")
            return processar_rastreamento(mensagem_usuario, sender, tipo='cpf')

        if eh_codigo_rastreio(mensagem_usuario):
            logger.info("🎯 Código de rastreio detectado - processando rastreamento")
            return processar_rastreamento(mensagem_usuario, sender, tipo='codigo')

        contexto = ""

        ja_interagiu = False
        if sender:
            historico_key = f"historico:{sender}"
            historico = redis_client.get(historico_key)
            if historico:
                ja_interagiu = True
            redis_client.set(historico_key, {"interagiu": True}, ex=3600)

        analise_ia = analisar_pergunta_com_ia(mensagem_usuario)

        if analise_ia and analise_ia.get('tipo_consulta') == 'nota_fiscal':
            numero_nf = analise_ia.get('numero_nf')
            if numero_nf:
                logger.info(f"IA detectou busca de NF: {numero_nf}")
                dados_nf = consultar_nota_fiscal(numero_nf)

                if dados_nf and dados_nf.get('encontrado'):
                    status_nf = dados_nf['status']
                    transportadora_nf = dados_nf.get('transportadora', '')
                    codigo_rastreio_nf = dados_nf.get('codigo_rastreio', '')

                    # Salva contexto se status = EXPEDIDO
                    if status_nf == 'EXPEDIDO' and sender:
                        salvar_contexto_nf(sender, dados_nf['numero_nf'], status_nf, transportadora_nf, codigo_rastreio_nf)

                    # Monta contexto base
                    contexto = f"""
                        INFORMAÇÕES DA NOTA FISCAL {dados_nf['numero_nf']}:
                        - Status: {status_nf}
                        - Transportadora: {transportadora_nf}
                        - Código de Rastreio: {codigo_rastreio_nf}
                    """

                    # Se EXPEDIDO, adiciona instrução OBRIGATÓRIA para oferecer rastreamento
                    if status_nf == 'EXPEDIDO':
                        contexto += """

                        ⚠️ AÇÃO OBRIGATÓRIA - O pedido está EXPEDIDO:
                        Você DEVE incluir na sua resposta a seguinte mensagem EXATAMENTE como está escrito:

                        "📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."

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

        if not ja_interagiu and not contexto:
            hora_atual = datetime.now().hour
            saudacao = "Boa tarde" if 12 <= hora_atual < 18 else "Bom dia" if hora_atual < 12 else "Boa noite"
            return PROMPTS['prompts']['saudacao_inicial']['template'].format(saudacao=saudacao)

        prompt_template = PROMPTS['prompts']['assistente_resposta']['template']
        prompt = prompt_template.format(
            contexto=contexto if contexto else "Responda de forma objetiva à pergunta do cliente.",
            pergunta_cliente=mensagem_usuario
        )

        response = client.chat.completions.create(model="gpt-4o-mini",
                                                  messages=[{
                                                      "role": "user",
                                                      "content": prompt
                                                  }],
                                                  max_tokens=500,
                                                  temperature=0.1)
        content = response.choices[0].message.content

        if content:
            content = content.replace("**", "").replace("*",
                                                        "").replace("__", "")
            content = content.strip()

            # Se foi uma consulta de NF EXPEDIDO, garantir que a mensagem de rastreamento está incluída
            if "AÇÃO OBRIGATÓRIA" in contexto and "📍 Deseja rastrear" not in content:
                content += "\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."

            return content
        return "Não foi possível gerar uma resposta."

    except Exception as e:
        logger.error(f"Erro ao consultar IA: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."

# Função para consulta de NF e extração de dados, com atualização para detectar transportadora
def consultar_nota_fiscal_e_detectar_transportadora(numero_nf, sender):
    """
    Consulta informações da nota fiscal e detecta a transportadora para solicitar
    a informação correta (CPF ou código de rastreio) se o status for EXPEDIDO.
    """
    dados_nf = consultar_nota_fiscal(numero_nf)

    if not dados_nf or not dados_nf.get('encontrado'):
        return dados_nf

    status_atual = dados_nf['status']
    transportadora = dados_nf.get('transportadora', '')
    codigo_rastreio = dados_nf.get('codigo_rastreio', '')

    # Se estiver EXPEDIDO, salva contexto e oferece rastreamento
    if status_atual == "EXPEDIDO":
        transportadora_lower = transportadora.lower()
        if 'magalog' in transportadora_lower:
            salvar_contexto_nf(sender, dados_nf['numero_nf'], status_atual, transportadora, codigo_rastreio)
            # Instrui IA a oferecer rastreamento com código
            prompt_para_ia = f"O pedido {dados_nf['numero_nf']} está EXPEDIDO via {transportadora}. O código de rastreio é {codigo_rastreio}. Solicite o código de rastreio se o cliente quiser rastrear."
        else:
            # Dialogo e outras transportadoras usam CPF
            salvar_contexto_nf(sender, dados_nf['numero_nf'], status_atual, transportadora, codigo_rastreio)
            # Instrui IA a oferecer rastreamento com CPF
            prompt_para_ia = f"O pedido {dados_nf['numero_nf']} está EXPEDIDO via {transportadora}. Solicite o CPF do destinatário para rastrear a entrega."

        # Retorna dados da NF e a instrução adicional para a IA
        return {**dados_nf, 'prompt_adicional': prompt_para_ia}
    else:
        # Se não estiver EXPEDIDO, apenas retorna os dados da NF
        return dados_nf

# Função para consultar NF que será chamada pela IA
def consultar_nota_fiscal_wms(numero_nf: str, empresa: str = None, id_depositante: str = None, sender: str = None):
    """
    Wrapper para consultar_nota_fiscal que inclui o sender para salvar contexto.
    """
    # Ignora empresa e id_depositante por enquanto, pois a lógica atual já busca em todos
    dados_nf = consultar_nota_fiscal_e_detectar_transportadora(numero_nf, sender)
    return dados_nf