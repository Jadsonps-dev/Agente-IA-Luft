from config import DB_CONFIG
from EstruturaSQL import EstruturaSQL
from Database import DataBaseOP
from Query import Queries
from Tables import TableDefinitions, InsertQueries
from Processadores import ProcessadorAcompanhamentoNF

class AcompanhamentoNF(EstruturaSQL):
    def __init__(self):
        self.ID_DEPOSITANTE = 2361178
        self.DATA_INICIO = (datetime.today() - timedelta(days=45)).strftime("%d/%m/%Y")
        self.DATA_FIM = datetime.today().strftime("%d/%m/%Y")

        query = Queries.query_nf(
            id_depositante=self.ID_DEPOSITANTE,
            nota_fiscal='2449256'   
        )

        super().__init__(self.ID_DEPOSITANTE, query)

    def executar(self):
        print("\nIMPORTAÇÃO DE ACOMPANHAMENTO DE SAÍDA")

        db = DataBaseOP(DB_CONFIG)
        sql_tabela = TableDefinitions.get_acompanhamento_nf()
        sql_insert = InsertQueries.insert_acompanhamento_nf()

        sucesso = self.executar_importacao_completa(
            db=db,
            sql_insert=sql_insert,
            sql_criacao_tabela=sql_tabela,
            data_inicio=self.DATA_INICIO,
            data_fim=self.DATA_FIM,
            nome_importacao="ACOMPANHAMENTO DE SAÍDA",
            processador_customizado=ProcessadorAcompanhamentoNF.processar
        )

        self.fechar_sessao()

        if sucesso:
            print("\nAcompanhamento de saída importado com sucesso!")
        else:
            print("\nFalha na importação do acompanhamento de saída")

        return sucesso

if __name__ == "__main__":
    ac_nf = AcompanhamentoNF()
    ac_nf.executar()
