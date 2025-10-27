"""
API de rastreamento para Dialogo Logística.
"""
import re
import logging
import requests
from bs4 import BeautifulSoup
from api.base_transportadora import BaseTransportadora

logger = logging.getLogger(__name__)


class DialogoTransportadora(BaseTransportadora):
    """Implementação para Dialogo Logística"""

    def __init__(self):
        super().__init__(
            nome="Dialogo",
            url_base="https://www.dialogotransportes.com.br"
        )

    def consultar_por_cpf(self, cpf: str) -> str:
        """
        Consulta pedidos usando CPF do destinatário.

        Args:
            cpf: CPF do destinatário (com ou sem formatação)

        Returns:
            HTML da página de resultados
        """
        cpf_limpo = re.sub(r'\D', '', cpf)

        url = f"{self.url_base}/rastreamento/"

        payload = {
            'tipo': 'destinatario',
            'valor': cpf_limpo
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text

        except Exception as e:
            logger.error(f"Erro ao consultar Dialogo: {str(e)}")
            return ""

    def extrair_pedidos(self, html: str) -> list:
        """
        Extrai lista de pedidos do HTML retornado.

        Args:
            html: HTML da página de resultados

        Returns:
            Lista de dicionários com dados dos pedidos
        """
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        pedidos = []

        # Busca todas as tabelas de rastreamento
        tabelas = soup.find_all('table')

        for tabela in tabelas:
            linhas = tabela.find_all('tr')

            pedido = {
                'numero_nf': '',
                'numero_coleta': '',
                'destinatario': '',
                'eventos': []
            }

            for linha in linhas:
                texto = linha.get_text(strip=True)

                # Extrai número da nota fiscal
                if 'N Fiscal:' in texto or 'Fiscal:' in texto:
                    match = re.search(r'(\d+)', texto)
                    if match:
                        pedido['numero_nf'] = match.group(1)

                # Extrai destinatário
                if 'Destinatário:' in texto or 'Destinatario:' in texto:
                    partes = texto.split(':', 1)
                    if len(partes) > 1:
                        pedido['destinatario'] = partes[1].strip()

                # Extrai eventos (data, unidade, situação)
                colunas = linha.find_all('td')
                if len(colunas) >= 3:
                    data = colunas[0].get_text(strip=True)
                    unidade = colunas[1].get_text(strip=True)
                    situacao = colunas[2].get_text(strip=True)

                    if data and unidade and situacao:
                        pedido['eventos'].append({
                            'data': data,
                            'unidade': unidade,
                            'situacao': situacao
                        })

            if pedido['numero_nf'] and pedido['eventos']:
                pedidos.append(pedido)

        return pedidos

    def buscar_pedido_especifico(self, cpf: str, numero_nf: str) -> dict:
        """
        Busca um pedido específico pelo CPF e número da NF.

        Args:
            cpf: CPF do destinatário
            numero_nf: Número da nota fiscal

        Returns:
            Dicionário com dados do pedido ou None se não encontrado
        """
        html = self.consultar_por_cpf(cpf)
        pedidos = self.extrair_pedidos(html)

        numero_nf_limpo = re.sub(r'\D', '', str(numero_nf))

        for pedido in pedidos:
            pedido_nf_limpo = re.sub(r'\D', '', str(pedido.get('numero_nf', '')))
            if pedido_nf_limpo == numero_nf_limpo:
                return pedido

        return None

    def formatar_rastreamento(self, pedido: dict) -> str:
        """
        Formata os dados do pedido em mensagem para o usuário.

        Args:
            pedido: Dicionário com dados do pedido

        Returns:
            Mensagem formatada
        """
        if not pedido:
            return "❌ Pedido não encontrado"

        mensagem = f"📦 **Rastreamento - {self.nome}**\n\n"
        mensagem += f"🧾 **Nota Fiscal:** {pedido.get('numero_nf', 'N/A')}\n"

        if pedido.get('destinatario'):
            mensagem += f"👤 **Destinatário:** {pedido['destinatario']}\n"

        mensagem += "\n📍 **Histórico de Movimentação:**\n\n"

        eventos = pedido.get('eventos', [])

        # Mostra último evento em destaque
        if eventos:
            ultimo = eventos[-1]
            mensagem += f"🔹 **SITUAÇÃO ATUAL**\n"
            mensagem += f"   {ultimo.get('data', '')} - {ultimo.get('unidade', '')}\n"
            mensagem += f"   {ultimo.get('situacao', '')}\n\n"

        # Mostra histórico completo
        if len(eventos) > 1:
            mensagem += "📋 **Histórico completo:**\n"
            for evento in reversed(eventos[:-1]):
                mensagem += f"\n• {evento.get('data', '')} - {evento.get('unidade', '')}\n"
                mensagem += f"  {evento.get('situacao', '')}\n"

        return mensagem


# Instância global para uso direto
dialogo = DialogoTransportadora()