
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

            # Extrai ID e MD do onclick para buscar detalhes
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

        # Extrai texto completo separado por linhas
        conteudo = soup.get_text(separator="\n", strip=True)
        linhas = [linha.strip() for linha in conteudo.split("\n") if linha.strip()]

        logger.debug(f"📄 Total de linhas extraídas: {len(linhas)}")

        pedido = {
            'numero_nf': '',
            'numero_pedido': '',
            'destinatario': '',
            'eventos': []
        }

        # Extrai informações principais
        for i, linha in enumerate(linhas):
            # Destinatário
            if linha == "Destinatário:" and i + 1 < len(linhas):
                pedido['destinatario'] = linhas[i + 1]
                logger.info(f"   ✅ Destinatário: {pedido['destinatario']}")

            # N Fiscal
            if linha == "N Fiscal:" and i + 1 < len(linhas):
                # A próxima linha pode ter formato "2 2551805"
                nf_linha = linhas[i + 1]
                match = re.search(r'(\d{6,})', nf_linha)
                if match:
                    pedido['numero_nf'] = match.group(1)
                    logger.info(f"   ✅ NF: {pedido['numero_nf']}")

            # N Pedido
            if linha == "N Pedido:" and i + 1 < len(linhas):
                match = re.search(r'(\d{6,})', linhas[i + 1])
                if match:
                    pedido['numero_pedido'] = match.group(1)
                    logger.info(f"   ✅ Pedido: {pedido['numero_pedido']}")

        # Extrai eventos (tabela com data/hora, unidade, situação)
        tabelas = soup.find_all('table')
        for tabela in tabelas:
            linhas_tabela = tabela.find_all('tr')
            
            for linha_tr in linhas_tabela:
                colunas = linha_tr.find_all('td')
                
                # Deve ter pelo menos 3 colunas: data, unidade, situação
                if len(colunas) >= 3:
                    data = colunas[0].get_text(strip=True)
                    unidade = colunas[1].get_text(strip=True)
                    situacao_completa = colunas[2].get_text(separator=" ", strip=True)
                    
                    # Valida se é linha de evento (data com formato dd/mm/yy)
                    if re.search(r'\d{2}/\d{2}/\d{2}', data):
                        pedido['eventos'].append({
                            'data': data,
                            'unidade': unidade,
                            'situacao': situacao_completa
                        })
                        logger.debug(f"   📍 Evento: {data} - {unidade}")

        if pedido['numero_nf'] and pedido['eventos']:
            logger.info(f"✅ Pedido completo - NF: {pedido['numero_nf']}, Eventos: {len(pedido['eventos'])}")
            pedidos.append(pedido)
        else:
            logger.warning(f"⚠️ Dados incompletos - NF: {pedido.get('numero_nf', 'N/A')}, Eventos: {len(pedido.get('eventos', []))}")

        logger.info(f"📋 Total de pedidos extraídos: {len(pedidos)}")
        
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
        
        if pedido.get('destinatario'):
            mensagem += f"👤 *Destinatário:* {pedido['destinatario']}\n"
        
        mensagem += f"🧾 *Nota Fiscal:* {pedido.get('numero_nf', 'N/A')}\n"
        
        if pedido.get('numero_pedido'):
            mensagem += f"🔢 *Pedido:* {pedido['numero_pedido']}\n"

        eventos = pedido.get('eventos', [])

        if not eventos:
            mensagem += "\n⚠️ Nenhum evento de rastreamento encontrado."
            return mensagem

        mensagem += "\n📍 *HISTÓRICO DE RASTREAMENTO:*\n"

        # Mostra todos os eventos em ordem reversa (mais recente primeiro)
        for evento in reversed(eventos):
            data = evento.get('data', '')
            unidade = evento.get('unidade', '')
            situacao = evento.get('situacao', '')
            
            # Extrai título da situação (primeira linha)
            linhas_situacao = situacao.split('\n')
            titulo = linhas_situacao[0] if linhas_situacao else situacao
            
            mensagem += f"\n📝 *{titulo}*\n"
            mensagem += f"   🕒 {data}\n"
            mensagem += f"   📍 {unidade}\n"
            
            # Adiciona detalhes se houver mais linhas
            if len(linhas_situacao) > 1:
                detalhes = '\n'.join(linhas_situacao[1:])
                mensagem += f"   ℹ️ {detalhes}\n"

        return mensagem


# Instância global para uso direto
dialogo = DialogoTransportadora()
