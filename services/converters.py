"""
Classe de conversão de dados da API
Todas as funções de conversão ficam centralizadas aqui
"""

from datetime import datetime


class Converters:
    """Classe com métodos de conversão de dados"""
    
    @staticmethod
    def inteiro(valor):
        """Converte valor para inteiro"""
        if valor in (None, ""): 
            return None
        try: 
            return int(float(valor))
        except: 
            return None

    @staticmethod
    def numero(valor):
        """Converte valor para número decimal"""
        if valor in (None, ""): 
            return None
        try: 
            return float(valor)
        except: 
            return None

    @staticmethod
    def texto(valor):
        """Converte valor para texto"""
        return str(valor) if valor not in (None, "") else None

    @staticmethod
    def data(timestamp_ms):
        """Converte timestamp em milissegundos para datetime"""
        if timestamp_ms in (None, "", " "):
            return None
        
        try:
            if isinstance(timestamp_ms, str):
                timestamp_ms = float(timestamp_ms.strip())
            
            if timestamp_ms > 0:
                return datetime.fromtimestamp(timestamp_ms / 1000)
            else:
                return None
        except:
            return None
    
    @staticmethod
    def timestamp(timestamp_ms):
        """Alias para conversão de timestamp"""
        return Converters.data(timestamp_ms)