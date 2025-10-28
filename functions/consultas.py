
"""
Módulo responsável por consultas ao WMS.
"""
import re
import logging
from datetime import datetime, timedelta
from services.wms import EstruturaSQL
from services.query import Queries

logger = logging.getLogger(__name__)

ID_DEPOSITANTES = [2361178, 538607]


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
                        'destinatario': columns[4] if len(columns) > 4 else '',
                        'cpf_destinatario': columns[5] if len(columns) > 5 else '',
                        'cep_destinatario': columns[6] if len(columns) > 6 else '',
                        'primeiro_nome': columns[7] if len(columns) > 7 else '',
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


def consultar_nota_fiscal_e_detectar_transportadora(numero_nf, sender):
    """
    Consulta informações da nota fiscal e detecta a transportadora para solicitar
    a informação correta (CPF ou código de rastreio) se o status for EXPEDIDO.
    """
    from functions.contexto import salvar_contexto_nf
    from functions.rastreamento import detectar_tipo_rastreamento
    
    dados_nf = consultar_nota_fiscal(numero_nf)

    if not dados_nf or not dados_nf.get('encontrado'):
        return dados_nf

    status_atual = dados_nf['status']
    transportadora = dados_nf.get('transportadora', '')
    codigo_rastreio = dados_nf.get('codigo_rastreio', '')
    primeiro_nome = dados_nf.get('primeiro_nome', '')
    cep = dados_nf.get('cep_destinatario', '')

    if status_atual == "EXPEDIDO":
        transportadora_lower = transportadora.lower()
        if 'magalog' in transportadora_lower:
            salvar_contexto_nf(sender, dados_nf['numero_nf'], status_atual, transportadora, codigo_rastreio, primeiro_nome, cep)
            prompt_para_ia = f"O pedido {dados_nf['numero_nf']} está EXPEDIDO via {transportadora}. O código de rastreio é {codigo_rastreio}. Solicite o código de rastreio se o cliente quiser rastrear."
        else:
            salvar_contexto_nf(sender, dados_nf['numero_nf'], status_atual, transportadora, codigo_rastreio, primeiro_nome, cep)
            prompt_para_ia = f"O pedido {dados_nf['numero_nf']} está EXPEDIDO via {transportadora}. Solicite o CPF do destinatário para rastrear a entrega."

        return {**dados_nf, 'prompt_adicional': prompt_para_ia}
    else:
        return dados_nf
