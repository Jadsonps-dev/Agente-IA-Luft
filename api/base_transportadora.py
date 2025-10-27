"""
Classe base abstrata para APIs de transportadoras.
Todas as transportadoras devem herdar desta classe.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseTransportadora(ABC):
    """
    Classe abstrata base para integração com APIs de transportadoras.
    
    Cada transportadora deve implementar os métodos abstratos:
    - consultar_por_cpf: Consulta rastreamento usando CPF do destinatário
    - extrair_pedidos: Extrai lista de pedidos da resposta
    - formatar_rastreamento: Formata informações de rastreamento para WhatsApp
    """
    
    def __init__(self, nome: str):
        """
        Inicializa a transportadora.
        
        Args:
            nome: Nome da transportadora (ex: "Dialogo", "Jadlog", etc)
        """
        self.nome = nome
        logger.info(f"🚚 Transportadora {self.nome} inicializada")
    
    @abstractmethod
    def consultar_por_cpf(self, cpf: str) -> Optional[Dict]:
        """
        Consulta rastreamento de pedidos usando CPF do destinatário.
        
        Args:
            cpf: CPF do destinatário (com ou sem pontuação)
            
        Returns:
            Dict com dados brutos da resposta ou None em caso de erro
        """
        pass
    
    @abstractmethod
    def extrair_pedidos(self, dados_resposta: Dict) -> List[Dict]:
        """
        Extrai lista de pedidos da resposta da API.
        
        Args:
            dados_resposta: Dados brutos retornados pela consulta
            
        Returns:
            Lista de dicionários, cada um contendo:
            - numero_fiscal: Número da nota fiscal
            - numero_pedido: Número do pedido
            - destinatario: Nome do destinatário
            - rastreamento: Lista de eventos de rastreamento
        """
        pass
    
    @abstractmethod
    def formatar_rastreamento(self, pedido: Dict) -> str:
        """
        Formata informações de rastreamento para envio no WhatsApp.
        
        Args:
            pedido: Dict com informações do pedido
            
        Returns:
            String formatada com emojis, pronta para enviar no WhatsApp
        """
        pass
    
    def buscar_pedido_especifico(self, cpf: str, numero_fiscal: str) -> Optional[Dict]:
        """
        Busca um pedido específico pelo número da nota fiscal.
        
        Args:
            cpf: CPF do destinatário
            numero_fiscal: Número da nota fiscal a buscar
            
        Returns:
            Dict com informações do pedido ou None se não encontrado
        """
        try:
            logger.info(f"🔍 Buscando NF {numero_fiscal} no {self.nome} com CPF fornecido")
            
            # Consulta API da transportadora
            dados = self.consultar_por_cpf(cpf)
            if not dados:
                logger.warning(f"⚠️ {self.nome}: Nenhum dado retornado para o CPF")
                return None
            
            # Extrai todos os pedidos
            pedidos = self.extrair_pedidos(dados)
            if not pedidos:
                logger.warning(f"⚠️ {self.nome}: Nenhum pedido encontrado")
                return None
            
            # Busca o pedido específico
            numero_fiscal_limpo = numero_fiscal.strip()
            for pedido in pedidos:
                nf_pedido = str(pedido.get('numero_fiscal', '')).strip()
                if nf_pedido == numero_fiscal_limpo:
                    logger.info(f"✅ {self.nome}: Pedido NF {numero_fiscal} encontrado!")
                    return pedido
            
            logger.warning(f"⚠️ {self.nome}: NF {numero_fiscal} não encontrada nos pedidos do CPF")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pedido no {self.nome}: {str(e)}")
            return None
    
    def limpar_cpf(self, cpf: str) -> str:
        """
        Remove pontuação do CPF.
        
        Args:
            cpf: CPF com ou sem pontuação
            
        Returns:
            CPF apenas com números
        """
        import re
        return re.sub(r'\D', '', cpf)
