
"""
Módulo de funções auxiliares da IA e processamento de consultas.
"""
from functions.ia_helpers import (
    verificar_interacao_usuario,
    obter_saudacao_inicial,
    limpar_formatacao_markdown,
    adicionar_mensagem_rastreamento,
    construir_contexto_nf
)
from functions.analisador import analisar_pergunta_com_ia, PROMPTS
from functions.consultas import (
    consultar_nota_fiscal,
    consultar_nota_fiscal_e_detectar_transportadora,
    extrair_data_mensagem
)
from functions.contexto import salvar_contexto_nf, obter_contexto_nf
from functions.rastreamento import (
    eh_cpf,
    eh_codigo_rastreio,
    detectar_tipo_rastreamento,
    processar_rastreamento
)

__all__ = [
    'verificar_interacao_usuario',
    'obter_saudacao_inicial',
    'limpar_formatacao_markdown',
    'adicionar_mensagem_rastreamento',
    'construir_contexto_nf',
    'analisar_pergunta_com_ia',
    'PROMPTS',
    'consultar_nota_fiscal',
    'consultar_nota_fiscal_e_detectar_transportadora',
    'extrair_data_mensagem',
    'salvar_contexto_nf',
    'obter_contexto_nf',
    'eh_cpf',
    'eh_codigo_rastreio',
    'detectar_tipo_rastreamento',
    'processar_rastreamento'
]
