
"""
API de rastreamento para Magalog.
"""
import re
import logging
from playwright.sync_api import sync_playwright
from api.base_transportadora import BaseTransportadora

logger = logging.getLogger(__name__)


class MagalogTransportadora(BaseTransportadora):
    """Implementação para Magalog"""

    def __init__(self):
        super().__init__(nome="Magalog")
        self.url_base = "https://cademinhaentrega.com.br/magalog"

    def consultar_por_codigo(self, codigo_rastreio: str) -> str:
        """
        Consulta rastreamento usando código de rastreio.
        
        Args:
            codigo_rastreio: Código de rastreio do pedido
            
        Returns:
            HTML com dados do rastreamento ou string vazia em caso de erro
        """
        try:
            logger.info(f"🔍 Consultando Magalog com código: {codigo_rastreio}")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto(self.url_base, wait_until="networkidle")

                campo = page.wait_for_selector('input[type="text"]', timeout=10000)
                campo.click()
                campo.fill(codigo_rastreio)
                campo.press("Enter")

                xpath_botao = '/html/body/app-root/ion-app/ion-router-outlet/app-tracking/ion-content/ion-row/ion-col[2]/ion-card/ion-accordion-group/ion-accordion/ion-item/ion-col[1]/ion-text/h1'
                page.wait_for_selector(f'xpath={xpath_botao}', timeout=20000)
                page.click(f'xpath={xpath_botao}')

                page.wait_for_selector("ion-list.md.list-md.hydrated", timeout=20000)

                itens = page.locator("ion-list.md.list-md.hydrated ion-item")

                eventos_html = []
                for i in range(itens.count()):
                    eventos_html.append(itens.nth(i).inner_text())

                browser.close()
                
                logger.info("✅ Dados da Magalog obtidos com sucesso")
                return "\n".join(eventos_html)

        except Exception as e:
            logger.error(f"❌ Erro ao consultar Magalog: {str(e)}")
            return ""

    def consultar_por_cpf(self, cpf: str) -> str:
        """
        Magalog não usa CPF, usa código de rastreio.
        Este método existe para manter compatibilidade com a interface.
        """
        logger.warning("⚠️ Magalog usa código de rastreio, não CPF")
        return ""

    def extrair_pedidos(self, dados_resposta: str) -> list:
        """
        Extrai eventos de rastreamento do HTML retornado.
        
        Args:
            dados_resposta: String com eventos de rastreamento
            
        Returns:
            Lista com um único pedido contendo os eventos
        """
        if not dados_resposta:
            return []

        try:
            eventos = []
            linhas = dados_resposta.split('\n')
            
            evento_atual = {}
            for linha in linhas:
                linha = linha.strip()
                if not linha:
                    continue
                
                # Tenta identificar padrões de data/hora
                if re.match(r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}', linha):
                    # Se já temos um evento em andamento, salva ele
                    if evento_atual:
                        eventos.append(evento_atual)
                    
                    evento_atual = {
                        'data': linha,
                        'descricao': ''
                    }
                elif evento_atual:
                    # Adiciona à descrição do evento atual
                    if evento_atual['descricao']:
                        evento_atual['descricao'] += ' ' + linha
                    else:
                        evento_atual['descricao'] = linha
            
            # Adiciona o último evento
            if evento_atual:
                eventos.append(evento_atual)

            pedido = {
                'numero_fiscal': '',
                'numero_pedido': '',
                'codigo_rastreio': '',
                'destinatario': '',
                'eventos': eventos
            }

            logger.info(f"📦 Total de eventos extraídos: {len(eventos)}")
            return [pedido] if eventos else []

        except Exception as e:
            logger.error(f"❌ Erro ao extrair pedidos: {str(e)}")
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
            return "❌ Pedido não encontrado"

        mensagem = f"📦 *RASTREAMENTO - MAGALOG*\n\n"
        
        if pedido.get('codigo_rastreio'):
            mensagem += f"🔢 *Código:* {pedido['codigo_rastreio']}\n"

        eventos = pedido.get('eventos', [])

        if not eventos:
            mensagem += "\n⚠️ Nenhum evento de rastreamento encontrado."
            return mensagem

        mensagem += "\n📍 *HISTÓRICO DE RASTREAMENTO:*\n"

        # Mostra todos os eventos (do mais recente ao mais antigo)
        for evento in eventos:
            data = evento.get('data', 'N/A')
            descricao = evento.get('descricao', 'N/A')
            
            mensagem += f"\n📝 *{descricao}*\n"
            mensagem += f"🕒 {data}\n"

        return mensagem

    def buscar_pedido_por_codigo(self, codigo_rastreio: str) -> dict:
        """
        Busca um pedido específico pelo código de rastreio.
        
        Args:
            codigo_rastreio: Código de rastreio do pedido
            
        Returns:
            Dicionário com dados do pedido ou None se não encontrado
        """
        try:
            logger.info(f"🔍 Buscando código {codigo_rastreio} na Magalog")
            
            dados = self.consultar_por_codigo(codigo_rastreio)
            pedidos = self.extrair_pedidos(dados)
            
            if pedidos:
                pedido = pedidos[0]
                pedido['codigo_rastreio'] = codigo_rastreio
                logger.info(f"✅ Pedido {codigo_rastreio} encontrado!")
                return pedido
            
            logger.warning(f"⚠️ Código {codigo_rastreio} não encontrado")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pedido: {str(e)}")
            return None
    
    def buscar_pedido_especifico(self, cpf: str, numero_fiscal: str) -> dict:
        """
        Magalog não usa CPF, mas mantém método para compatibilidade.
        """
        logger.warning("⚠️ Magalog usa código de rastreio, não CPF")
        return None


# Instância global
magalog = MagalogTransportadora()
