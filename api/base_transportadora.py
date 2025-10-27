
from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class BaseTransportadora(ABC):
    """
    Classe base abstrata para consulta de rastreamento de transportadoras.
    Todas as transportadoras devem herdar desta classe.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.logger = logger
    
    @abstractmethod
    def consultar_rastreio(self, cnpj_destinatario: str) -> dict:
        """
        Método abstrato que deve ser implementado por cada transportadora.
        
        Args:
            cnpj_destinatario: CNPJ do destinatário para consulta
            
        Returns:
            dict com informações do rastreamento
        """
        pass
    
    @abstractmethod
    def get_nome_transportadora(self) -> str:
        """Retorna o nome da transportadora"""
        pass
    
    def _fazer_requisicao_post(self, url: str, headers: dict, payload: dict, encoding: str = "utf-8") -> requests.Response:
        """Helper para fazer requisições POST"""
        try:
            response = self.session.post(url, headers=headers, data=payload)
            response.encoding = encoding
            return response
        except Exception as e:
            self.logger.error(f"Erro ao fazer requisição POST para {url}: {str(e)}")
            raise
    
    def _fazer_requisicao_get(self, url: str, headers: dict, encoding: str = "utf-8") -> requests.Response:
        """Helper para fazer requisições GET"""
        try:
            response = self.session.get(url, headers=headers)
            response.encoding = encoding
            return response
        except Exception as e:
            self.logger.error(f"Erro ao fazer requisição GET para {url}: {str(e)}")
            raise
    
    def _extrair_texto_soup(self, html: str) -> list:
        """Extrai texto de HTML usando BeautifulSoup"""
        soup = BeautifulSoup(html, "html.parser")
        conteudo = soup.get_text(separator="\n", strip=True)
        linhas = [linha.strip() for linha in conteudo.split("\n") if linha.strip()]
        return linhas
