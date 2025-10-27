from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
import re
import json
from datetime import datetime, timedelta
from services.wms import EstruturaSQL
from services.query import Queries
from config.globals import redis_client

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ID_DEPOSITANTES = [2361178, 538607]

with open('docs/api_wms_documentation.json', 'r', encoding='utf-8') as f:
    API_DOCS = json.load(f)

with open('docs/prompts_sistema.json', 'r', encoding='utf-8') as f:
    PROMPTS = json.load(f)

with open('docs/query_nf_learning.json', 'r', encoding='utf-8') as f:
    LEARNING_NF = json.load(f)

with open('docs/query_consulta_op_learning.json', 'r', encoding='utf-8') as f:
    LEARNING_OP = json.load(f)


def analisar_pergunta_com_ia(mensagem_usuario):
    """
    Usa OpenAI para analisar a pergunta do usuário e determinar como fazer a consulta.
    Retorna instruções estruturadas baseadas na documentação da API.
    """
    try:
        tools = [{
            "type": "function",
            "function": {
                "name": "consultar_operacoes_wms",
                "description":
                "Consulta operações no WMS baseado na documentação completa da API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo_consulta": {
                            "type":
                            "string",
                            "enum":
                            ["pedidos", "pecas", "nota_fiscal", "nenhuma"],
                            "description":
                            "Tipo: 'pedidos' = contar NOTA_FISCAL únicos | 'pecas' = somar QTDE | 'nota_fiscal' = buscar NF específica"
                        },
                        "periodo": {
                            "type":
                            "string",
                            "enum": [
                                "hoje", "ontem", "semana", "mes",
                                "personalizado"
                            ],
                            "description":
                            "Período da consulta"
                        },
                        "status_filtro": {
                            "type":
                            "array",
                            "items": {
                                "type": "string"
                            },
                            "description":
                            "Lista de status para filtrar. Valores possíveis: EXPEDIDO, IMPORTADO, FATURADO, PROCESSADO, CANCELADO, AG. SEPARAÇÃO, ENVIADO PARA FATURAMENTO"
                        },
                        "coluna_data": {
                            "type":
                            "string",
                            "enum": ["PESADO_EM", "IMPORTADO_EM"],
                            "description":
                            "IMPORTANTE: Use PESADO_EM para status EXPEDIDO. Use IMPORTADO_EM para todos os outros status (IMPORTADO, FATURADO, CANCELADO, etc)"
                        },
                        "tipo_cliente": {
                            "type":
                            "string",
                            "enum": ["B2B", "B2C", "TODOS"],
                            "description":
                            "Filtro de tipo de cliente: B2B, B2C ou TODOS"
                        },
                        "empresa": {
                            "type":
                            "string",
                            "enum": ["Insider", "Alpargatas", "todas"],
                            "description":
                            "Nome da empresa mencionada pelo usuário: Insider, Alpargatas ou todas se não especificou"
                        },
                        "id_depositante": {
                            "type":
                            "string",
                            "enum": ["2361178", "538607"],
                            "description":
                            "ID do depositante: 2361178=Insider | 538607=Alpargatas. Se usuário mencionar Insider use 2361178, se mencionar Alpargatas use 538607"
                        },
                        "numero_nf": {
                            "type":
                            "string",
                            "description":
                            "Número da nota fiscal (apenas para tipo_consulta=nota_fiscal)"
                        }
                    },
                    "required": ["tipo_consulta"]
                }
            }
        }]

        documentacao_completa = {
            "api_wms": API_DOCS,
            "aprendizado_query_nf": LEARNING_NF,
            "aprendizado_query_consulta_op": LEARNING_OP,
            "instrucoes_aprendizado": PROMPTS['instrucoes_aprendizado']
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

def processar_periodo(periodo):
    """
    Converte o período em datas DD/MM/YYYY.
    """
    hoje = datetime.now()

    if periodo == "hoje":
        data_inicio = data_fim = hoje.strftime("%d/%m/%Y")
    elif periodo == "ontem":
        ontem = hoje - timedelta(days=1)
        data_inicio = data_fim = ontem.strftime("%d/%m/%Y")
    elif periodo == "semana":
        data_inicio = (hoje - timedelta(days=7)).strftime("%d/%m/%Y")
        data_fim = hoje.strftime("%d/%m/%Y")
    elif periodo == "mes":
        data_inicio = (hoje - timedelta(days=30)).strftime("%d/%m/%Y")
        data_fim = hoje.strftime("%d/%m/%Y")
    else:
        data_inicio = data_fim = hoje.strftime("%d/%m/%Y")

    return data_inicio, data_fim

def consultar_operacoes(data_inicio,
                        data_fim,
                        status_filtro=None,
                        tipo_consulta='pedidos',
                        coluna_data='IMPORTADO_EM',
                        tipo_cliente='TODOS'):
    """
    Consulta operações via API WMS com suporte a filtros avançados.

    Args:
        data_inicio: Data inicial (DD/MM/YYYY)
        data_fim: Data final (DD/MM/YYYY)
        status_filtro: String ou lista de status para filtrar
        tipo_consulta: 'pedidos' (conta NFs) ou 'pecas' (soma quantidade)
        coluna_data: 'PESADO_EM' (para expedidos) ou 'IMPORTADO_EM' (para outros)
        tipo_cliente: 'B2B', 'B2C' ou 'TODOS'
    """
    logger.info(f"Consultando operações de {data_inicio} a {data_fim}")
    logger.info(
        f"  Status: {status_filtro} | Tipo: {tipo_consulta} | Coluna Data: {coluna_data} | Cliente: {tipo_cliente}"
    )

    for id_depositante in ID_DEPOSITANTES:
        estrutura = None
        try:
            sql_query = Queries.query_analise_op(id_depositante)
            sql_query = sql_query.replace("&Data_Inicio", f"'{data_inicio}'")
            sql_query = sql_query.replace("&Data_Fim", f"'{data_fim}'")

            estrutura = EstruturaSQL(id_depositante, sql_query)
            resposta_api = estrutura.fazer_requisicao_api(
                data_inicio, data_fim)

            if not resposta_api:
                logger.warning(
                    f"Nenhuma resposta da API para operações no depositante {id_depositante}"
                )
                continue

            value = resposta_api.get('value', {})
            lines = value.get('lines', [])

            if not lines:
                logger.info(
                    f"Nenhum registro encontrado no depositante {id_depositante}"
                )
                continue

            pedidos_unicos = set()
            total_pecas = 0

            for line in lines:
                columns = line.get('columns', [])
                if len(columns) >= 7:
                    nota_fiscal = columns[0]
                    classificacao = columns[1] if len(columns) > 1 else ''
                    status_nf = columns[2]
                    importado_em = columns[3]
                    pesado_em = columns[4]
                    qtde = columns[5] if len(columns) > 5 else 0

                    filtro_status_ok = True
                    if isinstance(status_filtro, list):
                        filtro_status_ok = status_nf in status_filtro if status_filtro else True
                    elif status_filtro:
                        filtro_status_ok = status_nf == status_filtro

                    filtro_cliente_ok = True
                    if tipo_cliente == 'B2C':
                        filtro_cliente_ok = classificacao.startswith(
                            'INSIDER_B2C') if classificacao else False
                    elif tipo_cliente == 'B2B':
                        filtro_cliente_ok = classificacao.startswith(
                            'INSIDER_B2B') if classificacao else False

                    if filtro_status_ok and filtro_cliente_ok:
                        pedidos_unicos.add(nota_fiscal)
                        try:
                            total_pecas += float(qtde) if qtde else 0
                        except (ValueError, TypeError):
                            pass

            if pedidos_unicos or total_pecas > 0:
                resultado = {
                    'encontrado': True,
                    'quantidade_pedidos': len(pedidos_unicos),
                    'quantidade_pecas': int(total_pecas),
                    'status_filtro': status_filtro,
                    'tipo_cliente': tipo_cliente,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim,
                    'id_depositante': id_depositante
                }
                logger.info(
                    f"Operações encontradas no depositante {id_depositante}: {resultado}"
                )
                return resultado

        except Exception as e:
            logger.error(
                f"Erro ao consultar operações no depositante {id_depositante}: {str(e)}"
            )
            continue
        finally:
            if estrutura is not None:
                estrutura.fechar_sessao()

    return {
        'encontrado': True,
        'quantidade_pedidos': 0,
        'quantidade_pecas': 0,
        'status_filtro': status_filtro,
        'tipo_cliente': tipo_cliente,
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }


def consultar_nota_fiscal(numero_nf):
    """
    Consulta informações da nota fiscal via API WMS em múltiplos depositantes.
    Tenta primeiro no depositante 2361178, se não encontrar, tenta no 538607.
    Retorna os dados formatados ou None em caso de erro.
    """
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


def perguntar_ia(mensagem_usuario, instance=None, sender=None):
    try:
        contexto = ""

        ja_interagiu = False
        if sender:
            historico_key = f"historico:{sender}"
            historico = redis_client.get(historico_key)
            if historico:
                ja_interagiu = True
            redis_client.set(historico_key, {"interagiu": True}, ex=3600)

        analise_ia = analisar_pergunta_com_ia(mensagem_usuario)

        if analise_ia and analise_ia.get('tipo_consulta') in [
                'pedidos', 'pecas'
        ]:
            logger.info(f"IA detectou consulta operacional: {analise_ia}")

            periodo = analise_ia.get('periodo', 'hoje')
            data_inicio, data_fim = processar_periodo(periodo)
            status_filtro = analise_ia.get('status_filtro')
            tipo_consulta = analise_ia['tipo_consulta']
            coluna_data = analise_ia.get('coluna_data', 'IMPORTADO_EM')
            tipo_cliente = analise_ia.get('tipo_cliente', 'TODOS')

            dados_op = consultar_operacoes(data_inicio, data_fim,
                                           status_filtro, tipo_consulta,
                                           coluna_data, tipo_cliente)

            if dados_op and dados_op.get('encontrado'):
                status_texto = ', '.join(status_filtro) if isinstance(
                    status_filtro, list) else (status_filtro or "todos")
                cliente_texto = f" ({tipo_cliente})" if tipo_cliente != 'TODOS' else ""

                if tipo_consulta == 'pecas':
                    contexto = f"""
                        RESUMO DE OPERAÇÕES - PEÇAS{cliente_texto}:
                        Período: {data_inicio} até {data_fim}
                        Status: {status_texto}
                        Coluna de Data: {coluna_data}
                        Total de peças: {dados_op['quantidade_pecas']:,}
                    """
                else:
                    contexto = f"""
                        RESUMO DE OPERAÇÕES - PEDIDOS{cliente_texto}:
                        Período: {data_inicio} até {data_fim}
                        Status: {status_texto}
                        Coluna de Data: {coluna_data}
                        Total de pedidos: {dados_op['quantidade_pedidos']}
                    """

        elif analise_ia and analise_ia.get('tipo_consulta') == 'nota_fiscal':
            numero_nf = analise_ia.get('numero_nf')
            if numero_nf:
                logger.info(f"IA detectou busca de NF: {numero_nf}")
                dados_nf = consultar_nota_fiscal(numero_nf)

                if dados_nf and dados_nf.get('encontrado'):
                    contexto = f"""
                        INFORMAÇÕES DA NOTA FISCAL {dados_nf['numero_nf']}:
                        - Status: {dados_nf['status']}
                        - Transportadora: {dados_nf['transportadora']}
                        - Código de Rastreio: {dados_nf['codigo_rastreio']}
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
            return content.strip()
        return "Não foi possível gerar uma resposta."

    except Exception as e:
        logger.error(f"Erro ao consultar IA: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."