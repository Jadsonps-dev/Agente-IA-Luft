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

# Carregar documentação da API
with open('docs/api_wms_documentation.json', 'r', encoding='utf-8') as f:
    API_DOCS = json.load(f)

MAPEAMENTO_STATUS = {
    'expedido': 'EXPEDIDO',
    'expedidos': 'EXPEDIDO',
    'importado': 'IMPORTADO',
    'importados': 'IMPORTADO',
    'faturado': 'FATURADO',
    'faturados': 'FATURADO',
    'separacao': 'AG. SEPARAÇÃO',
    'separação': 'AG. SEPARAÇÃO',
    'processado': 'PROCESSADO',
    'processados': 'PROCESSADO',
    'cancelado': 'CANCELADO',
    'cancelados': 'CANCELADO',
    'fluxo': ['IMPORTADO', 'AG. SEPARAÇÃO', 'PROCESSADO', 'FATURADO', 'ENVIADO PARA FATURAMENTO']
}


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
                "description": "Consulta operações no WMS baseado na documentação da API",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo_consulta": {
                            "type": "string",
                            "enum": ["pedidos", "pecas", "nota_fiscal", "nenhuma"],
                            "description": "Tipo de consulta: 'pedidos' para contar NFs únicas, 'pecas' para somar quantidade de produtos, 'nota_fiscal' para buscar uma NF específica"
                        },
                        "periodo": {
                            "type": "string",
                            "enum": ["hoje", "ontem", "semana", "mes", "personalizado"],
                            "description": "Período da consulta"
                        },
                        "status_filtro": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Status para filtrar: EXPEDIDO, IMPORTADO, FATURADO, PROCESSADO, CANCELADO, AG. SEPARAÇÃO, ENVIADO PARA FATURAMENTO"
                        },
                        "numero_nf": {
                            "type": "string",
                            "description": "Número da nota fiscal (apenas para tipo_consulta=nota_fiscal)"
                        }
                    },
                    "required": ["tipo_consulta"]
                }
            }
        }]
        
        prompt = f"""Você é um analisador de consultas para o sistema WMS da Luft Solutions.

DOCUMENTAÇÃO DA API WMS:
{json.dumps(API_DOCS, indent=2, ensure_ascii=False)}

PERGUNTA DO USUÁRIO:
"{mensagem_usuario}"

Analise a pergunta e determine:
1. É uma consulta operacional (pedidos/peças) ou busca de nota fiscal específica?
2. Qual período de tempo? (hoje, ontem, semana, mês)
3. Quais status filtrar? (use os valores exatos da documentação)
4. Se for busca de NF, qual o número?

Use a função consultar_operacoes_wms para retornar as instruções."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice="auto"
        )
        
        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            argumentos = json.loads(tool_call.function.arguments)
            logger.info(f"✅ OpenAI analisou: {argumentos}")
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


def detectar_consulta_operacional(mensagem):
    """
    Detecta se a mensagem é uma consulta sobre operações (expedidos, importados, etc).
    Retorna: (é_consulta_operacional, tipo_consulta, status_filtro)
    """
    mensagem_lower = mensagem.lower()
    
    padroes_operacionais = [
        r'quanto[s]?\s+(?:pedidos?|notas?)',
        r'quantidad[e]?\s+(?:de\s+)?(?:pedidos?|notas?|peças?|pecas?)',
        r'(?:pedidos?|notas?|peças?|pecas?)\s+(?:foi|foram|está|estão|estao|expedido|importado|faturado)',
        r'(?:expedido|importado|faturado|processado|cancelado)[s]?\s+(?:hoje|ontem)',
        r'total\s+(?:de\s+)?(?:pedidos?|notas?|peças?|pecas?)',
        r'(?:resumo|relatório|relatorio)\s+(?:de\s+)?(?:pedidos?|operaç|operac)'
    ]
    
    for padrao in padroes_operacionais:
        if re.search(padrao, mensagem_lower):
            tipo_consulta = 'pecas' if any(word in mensagem_lower for word in ['peça', 'peças', 'peca', 'pecas', 'quantidade de produto', 'total de produto']) else 'pedidos'
            
            status_filtro = None
            for key, value in MAPEAMENTO_STATUS.items():
                if key in mensagem_lower:
                    status_filtro = value
                    break
            
            return True, tipo_consulta, status_filtro
    
    return False, None, None


def extrair_numero_nota_fiscal(mensagem):
    """
    Extrai o número da nota fiscal da mensagem do usuário.
    Procura por padrões como: NF 123456, nota 123456, pedido 123456, etc.
    """
    padroes = [
        r'\b(?:nf|nota|nota fiscal|pedido|nfe)\s*[:.\s-]*(\d+)',
        r'\b(\d{5,})\b'
    ]
    
    for padrao in padroes:
        match = re.search(padrao, mensagem, re.IGNORECASE)
        if match:
            numero = match.group(1)
            logger.info(f"Número de nota fiscal detectado: {numero}")
            return numero
    
    return None


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


def consultar_operacoes(data_inicio, data_fim, status_filtro=None, tipo_consulta='pedidos'):
    """
    Consulta operações via API WMS e retorna estatísticas.
    status_filtro pode ser string única ou lista de strings.
    """
    logger.info(f"Consultando operações de {data_inicio} a {data_fim}, status: {status_filtro}, tipo: {tipo_consulta}")
    
    for id_depositante in ID_DEPOSITANTES:
        estrutura = None
        try:
            sql_query = Queries.query_status_op(id_depositante)
            sql_query = sql_query.replace("&Data_Inicio", f"'{data_inicio}'")
            sql_query = sql_query.replace("&Data_Fim", f"'{data_fim}'")
            
            estrutura = EstruturaSQL(id_depositante, sql_query)
            resposta_api = estrutura.fazer_requisicao_api(data_inicio, data_fim)
            
            if not resposta_api:
                logger.warning(f"Nenhuma resposta da API para operações no depositante {id_depositante}")
                continue
            
            value = resposta_api.get('value', {})
            lines = value.get('lines', [])
            
            if not lines:
                logger.info(f"Nenhum registro encontrado no depositante {id_depositante}")
                continue
            
            pedidos_unicos = set()
            total_pecas = 0
            
            for line in lines:
                columns = line.get('columns', [])
                if len(columns) >= 6:
                    nota_fiscal = columns[0]
                    status_nf = columns[2]
                    qtde_produto = columns[3] if len(columns) > 3 else 0
                    
                    if isinstance(status_filtro, list):
                        status_match = status_nf in status_filtro if status_filtro else True
                    elif status_filtro:
                        status_match = status_nf == status_filtro
                    else:
                        status_match = True
                    
                    if status_match:
                        pedidos_unicos.add(nota_fiscal)
                        try:
                            total_pecas += float(qtde_produto) if qtde_produto else 0
                        except (ValueError, TypeError):
                            pass
            
            if pedidos_unicos or total_pecas > 0:
                resultado = {
                    'encontrado': True,
                    'quantidade_pedidos': len(pedidos_unicos),
                    'quantidade_pecas': int(total_pecas),
                    'status_filtro': status_filtro,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim,
                    'id_depositante': id_depositante
                }
                logger.info(f"✅ Operações encontradas no depositante {id_depositante}: {resultado}")
                return resultado
                
        except Exception as e:
            logger.error(f"Erro ao consultar operações no depositante {id_depositante}: {str(e)}")
            continue
        finally:
            if estrutura is not None:
                estrutura.fechar_sessao()
    
    return {
        'encontrado': True,
        'quantidade_pedidos': 0,
        'quantidade_pecas': 0,
        'status_filtro': status_filtro,
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
            logger.info(f"Consultando nota fiscal {numero_nf} no depositante {id_depositante}")
            
            sql_query = Queries.query_nf(id_depositante, numero_nf)
            estrutura = EstruturaSQL(id_depositante, sql_query)
            
            resposta_api = estrutura.fazer_requisicao_api(data_inicio, data_fim)
            
            if not resposta_api:
                logger.warning(f"Nenhuma resposta da API para NF {numero_nf} no depositante {id_depositante}")
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
                        'transportadora': columns[2] if columns[2] else 'Não informada',
                        'codigo_rastreio': columns[3] if columns[3] else 'Não disponível',
                        'id_depositante': id_depositante
                    }
                    
                    logger.info(f"✅ Dados da NF {numero_nf} encontrados no depositante {id_depositante}")
                    return dados_nf
            
            logger.info(f"NF {numero_nf} não encontrada no depositante {id_depositante}, tentando próximo...")
                
        except Exception as e:
            logger.error(f"Erro ao consultar NF {numero_nf} no depositante {id_depositante}: {str(e)}")
            continue
        finally:
            if estrutura is not None:
                estrutura.fechar_sessao()
    
    logger.warning(f"❌ NF {numero_nf} não encontrada em nenhum dos depositantes")
    return {
        'encontrado': False,
        'numero_nf': numero_nf
    }


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
        
        if analise_ia and analise_ia.get('tipo_consulta') in ['pedidos', 'pecas']:
            logger.info(f"🤖 IA detectou consulta operacional: {analise_ia}")
            
            periodo = analise_ia.get('periodo', 'hoje')
            data_inicio, data_fim = processar_periodo(periodo)
            status_filtro = analise_ia.get('status_filtro')
            tipo_consulta = analise_ia['tipo_consulta']
            
            dados_op = consultar_operacoes(data_inicio, data_fim, status_filtro, tipo_consulta)
            
            if dados_op and dados_op.get('encontrado'):
                status_texto = ', '.join(status_filtro) if isinstance(status_filtro, list) else (status_filtro or "todos")
                
                if tipo_consulta == 'pecas':
                    contexto = f"""
RESUMO DE OPERAÇÕES - PEÇAS:
Período: {data_inicio} até {data_fim}
Status: {status_texto}
Total de peças: {dados_op['quantidade_pecas']:,}
                    """
                else:
                    contexto = f"""
RESUMO DE OPERAÇÕES - PEDIDOS:
Período: {data_inicio} até {data_fim}
Status: {status_texto}
Total de pedidos: {dados_op['quantidade_pedidos']}
                    """
        
        elif analise_ia and analise_ia.get('tipo_consulta') == 'nota_fiscal':
            numero_nf = analise_ia.get('numero_nf')
            if numero_nf:
                logger.info(f"🤖 IA detectou busca de NF: {numero_nf}")
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
            saudacao = "Boa tarde" if 12 <= datetime.now().hour < 18 else "Bom dia" if datetime.now().hour < 12 else "Boa noite"
            return f"{saudacao}! 😊\n\nSou assistente da Luft Solutions. Como posso ajudar você hoje? Se precisar de informações sobre seus pedidos, por favor, me forneça a nota fiscal ou número do pedido. 📦"

        prompt = f"""
Você é um assistente da empresa Luft Solutions que ajuda clientes com informações sobre pedidos e notas fiscais.

REGRAS OBRIGATÓRIAS:
- NUNCA use asteriscos (*) em nenhuma parte da resposta
- NUNCA use markdown (**, __, etc)
- Use apenas texto simples com emojis
- Use emojis para destacar informações (📦 para pedidos, ✅ para rastreio, 🚚 para transportadora)
- Use quebras de linha para organizar
- Seja breve e direto
- NÃO se apresente novamente

{contexto if contexto else "Responda de forma objetiva à pergunta do cliente."}

Pergunta do cliente: {mensagem_usuario}

LEMBRE-SE: NÃO use asteriscos ou markdown. Apenas texto simples com emojis.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )
        content = response.choices[0].message.content
        
        if content:
            content = content.replace("**", "").replace("*", "").replace("__", "")
            return content.strip()
        return "Não foi possível gerar uma resposta."

    except Exception as e:
        logger.error(f"Erro ao consultar IA: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."
