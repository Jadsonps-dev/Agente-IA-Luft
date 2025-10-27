"""
API de integração com Dialogo Logística.
Consulta rastreamento de pedidos usando CPF do destinatário.
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Optional
import logging
from api.base_transportadora import BaseTransportadora

logger = logging.getLogger(__name__)


class DialogoTransportadora(BaseTransportadora):
    """
    Integração com API de rastreamento da Dialogo Logística.
    """
    
    def __init__(self):
        super().__init__("Dialogo")
        self.url_inicial = "https://ssw.inf.br/2/ssw_resultSSW_dest"
        self.sigla_emp = "DLG"
    
    def consultar_por_cpf(self, cpf: str) -> Optional[Dict]:
        """
        Consulta rastreamento usando CPF do destinatário.
        
        Args:
            cpf: CPF do destinatário (com ou sem pontuação)
            
        Returns:
            Dict contendo HTML da página de resultados e detalhes
        """
        try:
            cpf_limpo = self.limpar_cpf(cpf)
            logger.info(f"🔍 Consultando Dialogo com CPF: {cpf_limpo}")
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://dialogologistica.com.br",
                "Referer": "https://dialogologistica.com.br/",
            }
            
            payload = {
                "urlori": "https://dialogologistica.com.br/rastreie-seu-pedido",
                "sigla_emp": self.sigla_emp,
                "cnpjdest": cpf_limpo
            }
            
            # Primeira requisição - lista de pedidos
            response = requests.post(self.url_inicial, headers=headers, data=payload, timeout=30)
            response.encoding = "iso-8859-1"
            
            # Extrai ID para página de detalhes
            onclick_regex = re.compile(r"opx\('/2/ssw_SSWDetalhado\?id=([^&]+)&md=([^']+)'\)")
            match = onclick_regex.search(response.text)
            
            if not match:
                logger.warning("⚠️ Nenhum pedido encontrado para este CPF")
                return None
            
            id_param, md_param = match.groups()
            url_detalhado = f"https://ssw.inf.br/2/ssw_SSWDetalhado?id={id_param}&md={md_param}"
            
            # Segunda requisição - detalhes do rastreamento
            headers_detalhado = {
                "User-Agent": "Mozilla/5.0",
                "Referer": self.url_inicial,
            }
            
            resp_detalhado = requests.get(url_detalhado, headers=headers_detalhado, timeout=30)
            resp_detalhado.encoding = "iso-8859-1"
            
            logger.info("✅ Dados da Dialogo obtidos com sucesso")
            return {
                'html_resultados': response.text,
                'html_detalhado': resp_detalhado.text
            }
            
        except requests.Timeout:
            logger.error("❌ Timeout ao consultar Dialogo")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao consultar Dialogo: {str(e)}")
            return None
    
    def extrair_pedidos(self, dados_resposta: Dict) -> List[Dict]:
        """
        Extrai informações de pedidos do HTML retornado.
        
        Args:
            dados_resposta: Dict com 'html_resultados' e 'html_detalhado'
            
        Returns:
            Lista com informações dos pedidos
        """
        try:
            html_detalhado = dados_resposta.get('html_detalhado', '')
            if not html_detalhado:
                return []
            
            soup = BeautifulSoup(html_detalhado, "html.parser")
            
            # Extrai informações do cabeçalho
            destinatario = ""
            numero_fiscal = ""
            numero_pedido = ""
            
            # Procura por "Destinatário:", "N Fiscal:", "N Pedido:"
            texto = soup.get_text()
            
            # Destinatário
            match_dest = re.search(r'Destinatário:\s*(.+?)(?:\n|N\s)', texto)
            if match_dest:
                destinatario = match_dest.group(1).strip()
            
            # N Fiscal
            match_nf = re.search(r'N\s+Fiscal:\s*(\d+(?:\s+\d+)*)', texto)
            if match_nf:
                numero_fiscal = match_nf.group(1).strip().replace(' ', '')
            
            # N Pedido
            match_pedido = re.search(r'N\s+Pedido:\s*(\d+)', texto)
            if match_pedido:
                numero_pedido = match_pedido.group(1).strip()
            
            # Extrai eventos de rastreamento da tabela
            eventos = []
            
            # Procura pela tabela de eventos
            linhas_tabela = soup.find_all('tr')
            for tr in linhas_tabela:
                colunas = tr.find_all('td')
                if len(colunas) >= 3:
                    # Data/Hora, Unidade, Situação
                    data_hora = colunas[0].get_text(separator=' ', strip=True)
                    unidade = colunas[1].get_text(separator=' ', strip=True)
                    situacao = colunas[2].get_text(separator=' ', strip=True)
                    
                    if data_hora and situacao:
                        eventos.append({
                            'data_hora': data_hora,
                            'unidade': unidade,
                            'situacao': situacao
                        })
            
            if not numero_fiscal:
                logger.warning("⚠️ Número fiscal não encontrado no HTML")
                return []
            
            pedido = {
                'numero_fiscal': numero_fiscal,
                'numero_pedido': numero_pedido,
                'destinatario': destinatario,
                'rastreamento': eventos
            }
            
            logger.info(f"✅ Pedido extraído - NF: {numero_fiscal}, Pedido: {numero_pedido}")
            return [pedido]
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair pedidos: {str(e)}")
            return []
    
    def formatar_rastreamento(self, pedido: Dict) -> str:
        """
        Formata rastreamento para envio no WhatsApp.
        
        Args:
            pedido: Dict com informações do pedido
            
        Returns:
            String formatada com emojis para WhatsApp
        """
        try:
            nf = pedido.get('numero_fiscal', 'N/A')
            num_pedido = pedido.get('numero_pedido', 'N/A')
            destinatario = pedido.get('destinatario', 'N/A')
            eventos = pedido.get('rastreamento', [])
            
            # Cabeçalho
            msg = f"📦 *RASTREAMENTO - DIALOGO LOGÍSTICA*\n\n"
            msg += f"👤 Destinatário: {destinatario}\n"
            msg += f"📄 Nota Fiscal: {nf}\n"
            msg += f"🔢 Pedido: {num_pedido}\n\n"
            
            if not eventos:
                msg += "⚠️ Nenhum evento de rastreamento disponível"
                return msg
            
            msg += "📍 *HISTÓRICO DE RASTREAMENTO:*\n\n"
            
            # Mapeia situações para emojis
            emoji_map = {
                'DOCUMENTO DE TRANSPORTE EMITIDO': '📝',
                'SAIDA DE UNIDADE': '🚚',
                'CHEGADA EM UNIDADE': '📍',
                'SAIDA PARA ENTREGA': '🚛',
                'PRIMEIRA TENTATIVA DE ENTREGA': '🔔',
                'MERCADORIA ENTREGUE': '✅',
                'ENTREGUE': '✅'
            }
            
            for evento in eventos:
                data_hora = evento.get('data_hora', '')
                unidade = evento.get('unidade', '')
                situacao_texto = evento.get('situacao', '')
                
                # Extrai título da situação (primeira linha em caps)
                linhas_situacao = situacao_texto.split('\n')
                titulo_situacao = linhas_situacao[0] if linhas_situacao else situacao_texto
                
                # Seleciona emoji
                emoji = '📌'
                for palavra_chave, emoji_escolhido in emoji_map.items():
                    if palavra_chave in titulo_situacao.upper():
                        emoji = emoji_escolhido
                        break
                
                msg += f"{emoji} *{titulo_situacao}*\n"
                msg += f"   🕒 {data_hora}\n"
                if unidade:
                    msg += f"   📍 {unidade}\n"
                
                # Adiciona detalhes (linhas após o título)
                if len(linhas_situacao) > 1:
                    detalhes = '\n'.join(linhas_situacao[1:]).strip()
                    if detalhes:
                        # Limita tamanho dos detalhes
                        if len(detalhes) > 200:
                            detalhes = detalhes[:200] + '...'
                        msg += f"   ℹ️ {detalhes}\n"
                
                msg += "\n"
            
            return msg
            
        except Exception as e:
            logger.error(f"❌ Erro ao formatar rastreamento: {str(e)}")
            return "❌ Erro ao formatar informações de rastreamento"


# Instância global para usar no agente
dialogo = DialogoTransportadora()
