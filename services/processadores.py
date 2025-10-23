"""
Classes de processamento específicas para cada tipo de importação
Cada classe sabe como processar os dados vindos da API para sua respectiva tabela
"""

import time
from datetime import datetime
from services.converters import Converters


class ProcessadorAcompanhamentoNF:
    """Processador de dados de acompanhamento de saída"""

    @staticmethod
    def processar(resposta_api):
        """Processa a resposta da API ou banco de dados para acompanhamento de saída"""
        start_time = time.time()

        try:
            value = resposta_api.get('value', {})
            lines = value.get('lines', [])

            print(f"Total de registros de acompanhamento de saída retornados: {len(lines)}")

            dados_formatados = []
            append_dado = dados_formatados.append

            for line in lines:
                columns = line.get('columns', [])
                if len(columns) >= 4:
                    nota_fiscal = columns[0]
                    status_nf = columns[1]
                    transportadora = columns[2]
                    codigo_rastreio = columns[3] or None  # pode vir vazio

                    append_dado((
                        nota_fiscal,
                        status_nf,
                        transportadora,
                        codigo_rastreio
                    ))

            end_time = time.time()
            print(f"Tempo de processamento dos dados de saída: {end_time - start_time:.2f} segundos")

            return dados_formatados

        except Exception as e:
            print(f"Erro ao processar resposta da API de acompanhamento de saída: {e}")
            import traceback
            traceback.print_exc()
            return []