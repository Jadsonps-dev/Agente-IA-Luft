
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
        super().__init__(nome="Dialogo")
        self.url_inicial = "https://ssw.inf.br/2/ssw_resultSSW_dest"
        self.url_detalhado_base = "https://ssw.inf.br/2/ssw_SSWDetalhado"

    def consultar_por_cpf(self, cpf: str) -> str:
        """
        Consulta pedidos usando CPF do destinatário.

        Args:
            cpf: CPF do destinatário (com ou sem formatação)

        Returns:
            HTML da página de resultados
        """
        cpf_limpo = re.sub(r'\D', '', cpf)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://dialogologistica.com.br",
            "Referer": "https://dialogologistica.com.br/",
        }

        payload = {
            "urlori": "https://dialogologistica.com.br/rastreie-seu-pedido",
            "sigla_emp": "DLG",
            "cnpjdest": cpf_limpo
        }

        try:
            logger.info(f"🔍 Consultando Dialogo com CPF: {cpf_limpo}")
            
            response = requests.post(self.url_inicial, headers=headers, data=payload, timeout=30)
            response.encoding = "iso-8859-1"

            # Extrai ID e MD do onclick
            soup = BeautifulSoup(response.text, "html.parser")
            onclick_regex = re.compile(r"opx\('/2/ssw_SSWDetalhado\?id=([^&]+)&md=([^']+)'\)")
            match = onclick_regex.search(response.text)

            if not match:
                logger.warning("⚠️ Nenhum link de detalhes encontrado na resposta")
                return ""

            id_param, md_param = match.groups()
            url_detalhado = f"{self.url_detalhado_base}?id={id_param}&md={md_param}"

            logger.info(f"📄 Buscando detalhes em: {url_detalhado}")

            headers_detalhado = {
                "User-Agent": "Mozilla/5.0",
                "Referer": self.url_inicial,
            }

            resp_detalhado = requests.get(url_detalhado, headers=headers_detalhado, timeout=30)
            resp_detalhado.encoding = "iso-8859-1"

            logger.info("✅ Dados da Dialogo obtidos com sucesso")
            return resp_detalhado.text

        except Exception as e:
            logger.error(f"❌ Erro ao consultar Dialogo: {str(e)}")
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

        # DEBUG: Log do HTML recebido
        logger.debug(f"📄 HTML recebido (primeiros 500 chars): {html[:500]}")
        
        # Busca todas as tabelas de rastreamento
        tabelas = soup.find_all('table')
        logger.info(f"🔍 Total de tabelas encontradas: {len(tabelas)}")

        for idx, tabela in enumerate(tabelas):
            logger.debug(f"📊 Processando tabela {idx + 1}/{len(tabelas)}")
            linhas = tabela.find_all('tr')

            pedido = {
                'numero_nf': '',
                'numero_pedido': '',
                'destinatario': '',
                'eventos': []
            }

            for linha in linhas:
                texto = linha.get_text(strip=True)
                
                # DEBUG: Mostra o texto de cada linha
                if texto and len(texto) > 5:
                    logger.debug(f"   📝 Linha: {texto[:100]}")

                # Extrai número da nota fiscal - busca sequência de 6+ dígitos
                if 'N Fiscal:' in texto or 'Fiscal:' in texto or 'NF:' in texto or 'Nota' in texto:
                    logger.debug(f"   🧾 Linha com NF detectada: {texto}")
                    # Busca por sequência de 6 ou mais dígitos consecutivos
                    match = re.search(r'(\d{6,})', texto)
                    if match:
                        pedido['numero_nf'] = match.group(1)
                        logger.info(f"   ✅ NF extraída: {pedido['numero_nf']}")

                # Extrai número do pedido - busca sequência de 6+ dígitos
                if 'N Pedido:' in texto or 'Pedido:' in texto or 'Ped:' in texto or 'Nº Pedido' in texto:
                    logger.debug(f"   📦 Linha com Pedido detectada: {texto}")
                    # Busca por sequência de 6 ou mais dígitos consecutivos
                    match = re.search(r'(\d{6,})', texto)
                    if match:
                        pedido['numero_pedido'] = match.group(1)
                        logger.info(f"   ✅ Pedido extraído: {pedido['numero_pedido']}")

                # Extrai destinatário
                if 'Destinatário:' in texto or 'Destinatario:' in texto or 'Dest:' in texto:
                    logger.debug(f"   👤 Linha com Destinatário detectada: {texto}")
                    partes = texto.split(':', 1)
                    if len(partes) > 1:
                        pedido['destinatario'] = partes[1].strip()
                        logger.info(f"   ✅ Destinatário extraído: {pedido['destinatario']}")

                # Extrai eventos (data, unidade, situação)
                colunas = linha.find_all('td')
                if len(colunas) >= 3:
                    data = colunas[0].get_text(strip=True)
                    unidade = colunas[1].get_text(strip=True)
                    situacao = colunas[2].get_text(strip=True)

                    # Valida se é realmente um evento (data deve ter formato de data)
                    if data and unidade and situacao and re.search(r'\d{2}/\d{2}', data):
                        pedido['eventos'].append({
                            'data': data,
                            'unidade': unidade,
                            'situacao': situacao
                        })

            if pedido['numero_nf'] and pedido['eventos']:
                logger.info(f"✅ Pedido extraído - NF: {pedido['numero_nf']}, Pedido: {pedido['numero_pedido']}")
                pedidos.append(pedido)
            else:
                logger.warning(f"⚠️ Pedido ignorado - NF: {pedido.get('numero_nf', 'N/A')}, Eventos: {len(pedido.get('eventos', []))}")

        logger.info(f"📋 Total de pedidos extraídos: {len(pedidos)}")
        if pedidos:
            for p in pedidos:
                logger.info(f"   - NF: {p.get('numero_nf')}, Pedido: {p.get('numero_pedido')}")
        
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
                logger.info(f"✅ Pedido NF {numero_nf} encontrado!")
                return pedido

        logger.warning(f"⚠️ NF {numero_nf} não encontrada nos pedidos retornados")
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

        mensagem = f"📦 *RASTREAMENTO - DIALOGO LOGÍSTICA*\n\n"
        mensagem += f"🧾 *Nota Fiscal:* {pedido.get('numero_nf', 'N/A')}\n"
        
        if pedido.get('numero_pedido'):
            mensagem += f"🔢 *Pedido:* {pedido['numero_pedido']}\n"

        if pedido.get('destinatario'):
            mensagem += f"👤 *Destinatário:* {pedido['destinatario']}\n"

        mensagem += "\n📍 *Histórico de Movimentação:*\n\n"

        eventos = pedido.get('eventos', [])

        # Mostra último evento em destaque
        if eventos:
            ultimo = eventos[-1]
            mensagem += f"🔹 *SITUAÇÃO ATUAL*\n"
            mensagem += f"   {ultimo.get('data', '')} - {ultimo.get('unidade', '')}\n"
            mensagem += f"   {ultimo.get('situacao', '')}\n\n"

        # Mostra histórico completo
        if len(eventos) > 1:
            mensagem += "📋 *Histórico completo:*\n"
            for evento in reversed(eventos[:-1]):
                mensagem += f"\n• {evento.get('data', '')} - {evento.get('unidade', '')}\n"
                mensagem += f"  {evento.get('situacao', '')}\n"

        return mensagem


# Instância global para uso direto
dialogo = DialogoTransportadora()
