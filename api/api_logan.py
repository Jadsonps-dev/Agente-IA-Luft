
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
            # A estrutura exata dependerá do HTML retornado pela Logan
            # Este é um exemplo que deve ser ajustado conforme necessário
            
            logger.info(f"Extraindo pedidos da Logan")
            
            # Aqui você precisará implementar a lógica específica 
            # para extrair os dados do HTML da Logan
            # Por enquanto, retornando estrutura básica
            
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

        if pedido.get('destinatario'):
            mensagem += f"👤 *Destinatário:* {pedido['destinatario']}\n"

        mensagem += "\n📍 *HISTÓRICO DE RASTREAMENTO:*\n"

        eventos = pedido.get('eventos', [])
        if not eventos:
            mensagem += "\n⚠️ Nenhum evento de rastreamento encontrado."
            return mensagem

        for evento in eventos:
            data = evento.get('data', 'N/A')
            status = evento.get('status', 'N/A')
            
            mensagem += f"\n📝 *{status}*\n"
            mensagem += f"🕒 {data}\n"

        return mensagem

    def buscar_pedido_com_dados_completos(self, cpf: str, primeiro_nome: str, cep: str, numero_fiscal: str = "") -> dict:
        """
        Busca pedido usando CPF, primeiro nome e CEP.

        Args:
            cpf: CPF do destinatário
            primeiro_nome: Primeiro nome do destinatário
            cep: CEP do destinatário
            numero_fiscal: Número da nota fiscal (opcional)

        Returns:
            Dict com dados do pedido ou None
        """
        try:
            logger.info(f"Buscando pedido Logan com dados completos")

            dados = self.consultar_por_cpf(cpf, primeiro_nome, cep)
            pedidos = self.extrair_pedidos(dados)

            if not pedidos:
                logger.warning("Logan: Nenhum pedido encontrado")
                return None

            if numero_fiscal:
                for pedido in pedidos:
                    if str(pedido.get('numero_fiscal', '')).strip() == numero_fiscal.strip():
                        logger.info(f"Logan: Pedido NF {numero_fiscal} encontrado!")
                        return pedido

            # Se não especificou NF ou não encontrou, retorna o primeiro
            return pedidos[0] if pedidos else None

        except Exception as e:
            logger.error(f"Erro ao buscar pedido Logan: {str(e)}")
            return None


logan = LoganTransportadora()
