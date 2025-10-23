from openai import OpenAI
import os
import logging
from dotenv import load_dotenv
import re
from datetime import datetime, timedelta

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def perguntar_ia(mensagem_usuario, instance=None, sender=None):
    try:
        contexto = ""

        prompt = f"""
        Você é um assistente especializado na empresa Luft Solutions.
        Se apresente e seja simpatico com o cliente.
        Use os dados abaixo para responder de forma clara e concisa:

        {contexto}

        Pergunta: {mensagem_usuario}

        Responda de forma direta e profissional, focando nas informações mais relevantes.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.1
        )
        content = response.choices[0].message.content
        return content.strip() if content else "Não foi possível gerar uma resposta."

    except Exception as e:
        logger.error(f"Erro ao consultar IA: {str(e)}")
        return "Desculpe, ocorreu um erro ao processar sua solicitação."