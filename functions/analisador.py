
"""
Módulo responsável por análise de perguntas com IA.
"""
import json
import logging
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

with open('docs/wms_documentation.json', 'r', encoding='utf-8') as f:
    API_DOCS = json.load(f)

with open('docs/prompts_sistema.json', 'r', encoding='utf-8') as f:
    PROMPTS = json.load(f)

with open('docs/query_consulta_nf_learning.json', 'r', encoding='utf-8') as f:
    LEARNING_NF = json.load(f)


def analisar_pergunta_com_ia(mensagem_usuario):
    """
    Usa OpenAI para analisar a pergunta do usuário e determinar como fazer a consulta.
    Retorna instruções estruturadas baseadas na documentação da API.
    """
    try:
        from tools.agent_tools import get_all_tools
        tools = get_all_tools()

        documentacao_completa = {
            "api_wms": API_DOCS,
            "aprendizado_query_nf": LEARNING_NF
        }

        prompt_template = PROMPTS['prompts']['analisador_consultas']['template']
        prompt = prompt_template.format(
            documentacao_api=json.dumps(documentacao_completa, indent=2, ensure_ascii=False),
            pergunta_usuario=mensagem_usuario
        )

        response = client.chat.completions.create(model="gpt-4o-mini",
                                                  messages=[{
                                                      "role": "user",
                                                      "content": prompt
                                                  }],
                                                  tools=tools,
                                                  tool_choice="auto")

        if response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            argumentos = json.loads(tool_call.function.arguments)
            logger.info(f"OpenAI analisou: {argumentos}")
            return argumentos

        return None

    except Exception as e:
        logger.error(f"Erro ao analisar pergunta com IA: {str(e)}")
        return None
