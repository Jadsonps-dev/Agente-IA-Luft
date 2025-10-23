"""
Definições de tabelas e queries SQL
Centraliza todas as estruturas de tabelas e comandos INSERT do projeto
"""

class TableDefinitions:
    """Classe com definições de criação de tabelas"""
    
    @staticmethod
    def get_acompanhamento_nf():
        """Retorna SQL de criação da tabela acompanhamento_nf"""
        return """
        CREATE TABLE IF NOT EXISTS acompanhamento_nf (
            nota_fiscal VARCHAR PRIMARY KEY,
            status_nota_fiscal VARCHAR,
            transportadora VARCHAR,
            codigo_rastreio VARCHAR,
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

class InsertQueries:
    """Classe com queries de INSERT"""
    
    @staticmethod
    def insert_acompanhamento_nf():
        return """
        INSERT INTO acompanhamento_nf (
            nota_fiscal,
            status_nota_fiscal,
            transportadora,
            codigo_rastreio
        ) VALUES (%s, %s, %s, %s)
        ON CONFLICT (nota_fiscal) DO UPDATE SET
            status_nota_fiscal = EXCLUDED.status_nota_fiscal,
            transportadora = EXCLUDED.transportadora,
            codigo_rastreio = EXCLUDED.codigo_rastreio,
            data_importacao = CURRENT_TIMESTAMP
        """