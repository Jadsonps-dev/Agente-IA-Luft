
"""
API de rastreamento para Logan Express.
"""
import re
import logging
import requests
from api.base_transportadora import BaseTransportadora

logger = logging.getLogger(__name__)


class LoganTransportadora(BaseTransportadora):
    """Implementação para Logan Express"""

    def __init__(self):
        super().__init__(nome="Logan")
        self.url_base = "https://endpoint.simexpress.com.br/logan/consumidor/index.php"

    def consultar_por_cpf(self, cpf: str, primeiro_nome: str = "", cep: str = "") -> str:
        """
        Consulta rastreamento usando CPF, primeiro nome e CEP do destinatário.

        Args:
            cpf: CPF do destinatário (com ou sem pontuação)
            primeiro_nome: Primeiro nome do destinatário
            cep: CEP do destinatário

        Returns:
            HTML com dados do rastreamento ou string vazia em caso de erro
        """
        cpf_limpo = re.sub(r'\D', '', cpf)
        cep_limpo = re.sub(r'\D', '', cep)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
                      "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://endpoint.simexpress.com.br",
            "Referer": "https://endpoint.simexpress.com.br/logan/consumidor/index.php",
            "Connection": "keep-alive",
        }

        payload = {
            "documento": cpf_limpo,
            "primeironome": primeiro_nome.lower(),
            "cep": cep_limpo,
            "login": ""
        }

        try:
            logger.info(f"Consultando Logan com CPF: {cpf_limpo}, Nome: {primeiro_nome}, CEP: {cep_limpo}")

            response = requests.post(self.url_base, data=payload, headers=headers, timeout=30)
            response.encoding = "utf-8"

            logger.info(f"Status code Logan: {response.status_code}")
            return response.text

        except Exception as e:
            logger.error(f"Erro ao consultar Logan: {str(e)}")
            return ""

    def extrair_pedidos(self, dados_resposta: str) -> list:
        """
        Extrai pedidos do HTML retornado pela Logan.

        Args:
            dados_resposta: HTML da resposta

        Returns:
            Lista de pedidos encontrados
        """
        if not dados_resposta:
            return []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(dados_resposta, 'html.parser')

            pedidos = []
            
            logger.info(f"Extraindo pedidos da Logan do HTML")
            
            # Busca a tabela com id='grid'
            tabela = soup.find('table', {'id': 'grid'})
            
            if not tabela:
                logger.warning("Logan: Tabela de pedidos não encontrada no HTML")
                return []
            
            # Pega todas as linhas da tabela (exceto o cabeçalho)
            linhas = tabela.find_all('tr', class_='linha')
            
            logger.info(f"Logan: Encontradas {len(linhas)} linhas de pedidos")
            
            for linha in linhas:
                colunas = linha.find_all('td', class_='linhacelula')
                
                if len(colunas) >= 6:
                    tomador = colunas[0].get_text(strip=True)
                    numero_fiscal = colunas[1].get_text(strip=True)
                    coletado_em = colunas[2].get_text(strip=True)
                    previsao_entrega = colunas[3].get_text(strip=True)
                    
                    # Extrai status e link do rastreamento
                    status_link = colunas[4].find('a')
                    status = status_link.get_text(strip=True) if status_link else colunas[4].get_text(strip=True)
                    link_rastreamento = status_link.get('href') if status_link else ''
                    
                    pedido_transportadora = colunas[5].get_text(strip=True)
                    
                    pedido = {
                        'numero_fiscal': numero_fiscal,
                        'tomador': tomador,
                        'data_coleta': coletado_em,
                        'previsao_entrega': previsao_entrega,
                        'status': status,
                        'link_rastreamento': link_rastreamento,
                        'pedido_transportadora': pedido_transportadora
                    }
                    
                    pedidos.append(pedido)
                    logger.info(f"Logan: Pedido extraído - NF: {numero_fiscal}, Status: {status}")
            
            return pedidos

        except Exception as e:
            logger.error(f"Erro ao extrair pedidos Logan: {str(e)}")
            return []

    def formatar_rastreamento(self, pedido: dict) -> str:
        """
        Formata os dados do pedido em mensagem para o usuário.

        Args:
            pedido: Dicionário com dados do pedido

        Returns:
            Mensagem formatada
        """
        if not pedido:
            return "Pedido não encontrado"

        mensagem = f"📦 *RASTREAMENTO - LOGAN EXPRESS*\n\n"

        if pedido.get('numero_fiscal'):
            mensagem += f"📋 *NF:* {pedido['numero_fiscal']}\n"

        if pedido.get('tomador'):
            mensagem += f"🏢 *Tomador:* {pedido['tomador']}\n"

        if pedido.get('pedido_transportadora'):
            mensagem += f"🔢 *Pedido Transportadora:* {pedido['pedido_transportadora']}\n\n"

        if pedido.get('data_coleta'):
            mensagem += f"📅 *Coletado em:* {pedido['data_coleta']}\n"

        if pedido.get('previsao_entrega'):
            mensagem += f"⏰ *Previsão de Entrega:* {pedido['previsao_entrega']}\n\n"

        if pedido.get('status'):
            mensagem += f"📝 *Status:* {pedido['status']}"

        return mensagem

    def buscar_pedido_com_dados_completos(self, cpf: str, primeiro_nome: str, cep: str, codigo_rastreio: str = "") -> dict:
        """
        Busca pedido usando CPF, primeiro nome, CEP e código de rastreio.

        Args:
            cpf: CPF do destinatário
            primeiro_nome: Primeiro nome do destinatário
            cep: CEP do destinatário
            codigo_rastreio: Código de rastreio do WMS (opcional)

        Returns:
            Dict com dados do pedido ou None
        """
        try:
            logger.info(f"Buscando pedido Logan - Código rastreio WMS: {codigo_rastreio}")

            dados = self.consultar_por_cpf(cpf, primeiro_nome, cep)
            pedidos = self.extrair_pedidos(dados)

            if not pedidos:
                logger.warning("Logan: Nenhum pedido encontrado")
                return None

            # Converte codigo_rastreio para string e remove espaços
            codigo_rastreio_str = str(codigo_rastreio).strip() if codigo_rastreio else ""

            if codigo_rastreio_str:
                # Remove caracteres não numéricos para comparação
                codigo_limpo = re.sub(r'\D', '', codigo_rastreio_str)
                
                for pedido in pedidos:
                    # Na Logan, o código de rastreio vem no campo 'numero_fiscal'
                    pedido_codigo = str(pedido.get('numero_fiscal', '')).strip()
                    pedido_codigo_limpo = re.sub(r'\D', '', pedido_codigo)
                    
                    if pedido_codigo_limpo == codigo_limpo:
                        logger.info(f"Logan: Pedido encontrado! Código: {codigo_rastreio} = NF Logan: {pedido_codigo}, Status: {pedido.get('status')}")
                        return pedido

                logger.warning(f"Logan: Código {codigo_rastreio} não encontrado entre os {len(pedidos)} pedidos retornados")
                return None

            # Se não especificou código, retorna o primeiro
            logger.info(f"Logan: Retornando primeiro pedido (total: {len(pedidos)})")
            return pedidos[0] if pedidos else None

        except Exception as e:
            logger.error(f"Erro ao buscar pedido Logan: {str(e)}")
            return None


logan = LoganTransportadora()
