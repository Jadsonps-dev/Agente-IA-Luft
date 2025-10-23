import requests
import time
from config.globals import *


class EstruturaSQL:
    def __init__(self, id_depositante, sql_query):
        """
        Inicializa a estrutura SQL genérica
        
        Args:
            id_depositante: ID do depositante
            sql_query: Query SQL que será executada na API
        """
        self.id_depositante = id_depositante
        self.sql_query = sql_query
        self.session = requests.Session()
        self.headers = API_CONFIG['headers'].copy()
        
        print("EstruturaSQL inicializada com query personalizada")

    def fazer_login(self):
        """Faz login na API e retorna session com token"""
        print("Fazendo login na API...")
        try:
            response = self.session.post(
                API_CONFIG['LOGIN_URL'], 
                json=API_CONFIG['login_data'], 
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Erro no login: {response.status_code} - {response.text}")
            
            token = response.json().get('value', {}).get('bearer')
            if not token:
                raise Exception("Token de autenticação não encontrado na resposta!")
            
            self.headers['Authorization'] = f'Bearer {token}'
            print("Login realizado com sucesso!")
            return True
            
        except Exception as e:
            print(f"Erro no login: {e}")
            return False

    def get_grid_data(self, data_inicio, data_fim):
        """Retorna a estrutura grid_data com as datas preenchidas"""
        return {
            "armazem": API_CONFIG['login_data']["armazem"],
            "config": {
                "@class": "SqlQueryResultTableConfig",
                "sqlQueryLoadMode": "DEFAULT",
                "queryType": "ROWID",
                "showAll": False,
                "advancedSearch": [],
                "customWhere": None,
                "dynamicParameters": {
                    "DataInicio": data_inicio,
                    "DataFim": data_fim
                },
                "filterConfigs": [],
                "onlyGenerateSql": False,
                "orderBy": None,
                "parameters": {
                    "DataInicio": data_inicio,
                    "DataFim": data_fim
                },
                "scalarTypes": {},
                "showFilter": [],
                "showQueryCount": True,
                "skip": 0,
                "sqlQueryLoadMode": "DEFAULT",
                "take": 10000000   
            },
            "usuario": {
                "id": 2520,
                "nomeUsuario": "EDGAR.MARQUES",
                "senha": "5BI/ESLUrIAVQsQJqp0UXrTbjUg=",
                "ativo": True
            },
            "sql": self.sql_query   
        }

    def fazer_requisicao_api(self, data_inicio, data_fim):
        """
        Faz a requisição completa para a API Grid
        
        Args:
            data_inicio: Data inicial no formato dd/mm/yyyy
            data_fim: Data final no formato dd/mm/yyyy
            
        Returns:
            dict: Resposta da API ou None em caso de erro
        """
        try:
            
            if not self.fazer_login():
                return None
            
            print(f"Período da consulta: {data_inicio} a {data_fim}")
            
            grid_data = self.get_grid_data(data_inicio, data_fim)
            
            print("Fazendo requisição para GridService...")
            start_time = time.time()
            
            response = self.session.post(
                API_CONFIG['GRID_URL'], 
                json=grid_data, 
                headers=self.headers,
                timeout=60
            )
            
            end_time = time.time()
            print(f"Tempo da requisição: {end_time - start_time:.2f} segundos")
            
            if response.status_code == 200:
                print("Requisição API realizada com sucesso!")
                return response.json()
            else:
                print(f"Erro na requisição: {response.status_code}")
                print(f"Resposta: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("Timeout na requisição API")
            return None
        except requests.exceptions.ConnectionError:
            print("Erro de conexão com a API")
            return None
        except Exception as e:
            print(f"Erro inesperado: {e}")
            return None

    def processar_resposta_api(self, resposta_api, processador_customizado=None):
        """
        Processa a resposta da API usando um processador customizado ou genérico
        
        Args:
            resposta_api: Resposta JSON da API
            processador_customizado: Função customizada para processar os dados (opcional)
        
        Returns:
            list: Dados formatados para inserção no banco
        """
        if not resposta_api:
            print("Nenhuma resposta da API para processar")
            return []
        
        if processador_customizado:
            return processador_customizado(resposta_api)
        else:
            print("AVISO: Usando processador genérico. Recomenda-se usar um processador customizado.")
            value = resposta_api.get('value', {})
            lines = value.get('lines', [])
            dados_formatados = []
            
            print(f"Total de registros retornados: {len(lines)}")
            
            for i, line in enumerate(lines):
                columns = line.get('columns', [])
                if columns:
                    dados_formatados.append(tuple(columns))
                
                if (i + 1) % 1000 == 0:
                    print(f"Processados {i + 1}/{len(lines)} registros")
            
            print(f"Dados processados: {len(dados_formatados)} registros válidos")
            return dados_formatados


    def executar_importacao_completa(self, db, sql_insert, sql_criacao_tabela, data_inicio, data_fim, nome_importacao="Importação", processador_customizado=None):
        """
        Executa o processo completo de importação
        
        Args:
            db: Instância do DataBaseOP
            sql_insert: SQL para inserção dos dados
            sql_criacao_tabela: SQL para criação da tabela
            num_colunas_esperadas: Número de colunas esperadas na resposta
            data_inicio: Data inicial no formato dd/mm/yyyy
            data_fim: Data final no formato dd/mm/yyyy
            nome_importacao: Nome descritivo da importação
            
        Returns:
            bool: True se sucesso, False se erro
        """
        start_time = time.time()
        
        try:
            print(f"\n{'='*60}")
            print(f"INICIANDO {nome_importacao.upper()}")
            print(f"Período: {data_inicio} a {data_fim}")
            print(f"Depositante: {self.id_depositante}")
            
            conn = db.conectar()
            if not conn:
                print("Falha na conexão com o banco")
                return False
            
            print("Criando/verificando tabela...")
            db.criar_tabela(sql_criacao_tabela)
            
            resposta_api = self.fazer_requisicao_api(data_inicio, data_fim)
            
            if resposta_api:
                
                dados = self.processar_resposta_api(resposta_api, processador_customizado)
                
                if dados:
                    
                    print("Inserindo dados no banco...")
                    db.inserir_dados_batch(sql_insert, dados, batch_size=30000)
                    print(f"{nome_importacao.upper()} - CONCLUÍDA!")
                else:
                    print("Nenhum dado válido para importar")
            else:
                print("Falha na obtenção dos dados da API")
                return False
                
        except Exception as e:
            print(f"ERRO: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            db.fechar_conexao()
            tempo_total = time.time() - start_time
            print(f"Tempo total: {tempo_total:.2f}s")
        
        return True

    def fechar_sessao(self):
        """Fecha a sessão HTTP"""
        if self.session:
            self.session.close()
            print("Sessão HTTP fechada")