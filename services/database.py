import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
import time
import warnings

warnings.filterwarnings("ignore")

class DataBaseOP:
    """Classe para operações de banco de dados PostgreSQL"""

    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None

    def conectar(self):
        """Conecta ao banco de dados PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
            print("Conexão com o banco estabelecida.")
            return self.conn
        except Exception as e:
            print(f"Erro ao conectar ao banco: {e}")
            return None

    def fechar_conexao(self):
        """Fecha a conexão com o banco"""
        if self.conn:
            self.conn.close()
            print("Conexão encerrada.")

    def criar_tabela(self, tabela_sql):
        """Cria a tabela caso não exista"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(tabela_sql)
            self.conn.commit()
            print("Tabela criada/verificada com sucesso!")
        except Exception as e:
            print(f"Erro ao criar tabela: {e}")
            self.conn.rollback()

    def inserir_dados_batch(self, insert_sql, dados, batch_size=1000):
        """Insere dados em lotes (super otimizado)"""
        try:
            cursor = self.conn.cursor()
            start_time = time.time()
            total = len(dados)

            for i in range(0, total, batch_size):
                batch = dados[i:i + batch_size]
                execute_batch(cursor, insert_sql, batch, page_size=batch_size)
                print(f"Inseridos {i+len(batch)} / {total} registros")

            self.conn.commit()
            print(f"Inserção concluída! Tempo total: {time.time()-start_time:.2f}s")
            cursor.close()
        except Exception as e:
            print(f"Erro ao inserir: {e}")
            self.conn.rollback()