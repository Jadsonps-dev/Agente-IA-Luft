from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
import re
from datetime import datetime, timedelta
from services.wms import EstruturaSQL
from services.query import Queries

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ID_DEPOSITANTE = 2361178


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


def consultar_nota_fiscal(numero_nf):
    """
    Consulta informações da nota fiscal via API WMS.
    Retorna os dados formatados ou None em caso de erro.
    """
    estrutura = None
    try:
        logger.info(f"Consultando nota fiscal: {numero_nf}")
        
        sql_query = Queries.query_nf(ID_DEPOSITANTE, numero_nf)
        
        estrutura = EstruturaSQL(ID_DEPOSITANTE, sql_query)
        
        data_fim = datetime.now().strftime("%d/%m/%Y")
        data_inicio = (datetime.now() - timedelta(days=90)).strftime("%d/%m/%Y")
        
        resposta_api = estrutura.fazer_requisicao_api(data_inicio, data_fim)
        
        if not resposta_api:
            logger.warning(f"Nenhuma resposta da API para NF {numero_nf}")
            return None
        
        value = resposta_api.get('value', {})
        lines = value.get('lines', [])
        
        if not lines:
            logger.warning(f"Nenhum registro encontrado para NF {numero_nf}")
            return {
                'encontrado': False,
                'numero_nf': numero_nf
            }
        
        primeira_linha = lines[0]
        columns = primeira_linha.get('columns', [])
        
        if len(columns) >= 4:
            dados_nf = {
                'encontrado': True,
                'numero_nf': columns[0],
                'status': columns[1],
                'transportadora': columns[2] if columns[2] else 'Não informada',
                'codigo_rastreio': columns[3] if columns[3] else 'Não disponível'
            }
            
            logger.info(f"Dados da NF encontrados: {dados_nf}")
            return dados_nf
        else:
            logger.warning(f"Formato de resposta inesperado para NF {numero_nf}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao consultar nota fiscal {numero_nf}: {str(e)}")
        return None
    finally:
        if estrutura is not None:
            estrutura.fechar_sessao()


def perguntar_ia(mensagem_usuario, instance=None, sender=None):
    try:
        contexto = ""
        
        numero_nf = extrair_numero_nota_fiscal(mensagem_usuario)
        
        if numero_nf:
            logger.info(f"Processando consulta de nota fiscal: {numero_nf}")
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

        prompt = f"""
Você é um assistente especializado da empresa Luft Solutions.
Você ajuda clientes a rastrear seus pedidos e obter informações sobre notas fiscais.

Se apresente de forma simpática e profissional.

{contexto if contexto else "Você pode ajudar o cliente com informações sobre pedidos e notas fiscais. Para consultar um pedido, peça o número da nota fiscal."}

Pergunta do cliente: {mensagem_usuario}

Responda de forma clara, direta e profissional. Se houver informações de rastreio, destaque-as para o cliente.
Se não encontrar a nota fiscal, sugira que o cliente verifique o número e tente novamente.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )
        content = response.choices[0].message.content
        return content.strip() if content else "Não foi possível gerar uma resposta."

    except Exception as e:
        logger.error(f"Erro ao consultar IA: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."
