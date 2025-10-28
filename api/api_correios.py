
"""
API de rastreamento para Correios.
Requer resolução de captcha pelo usuário.
"""
import os
import logging
import requests
from api.base_transportadora import BaseTransportadora

logger = logging.getLogger(__name__)


class CorreiosTransportadora(BaseTransportadora):
    """Implementação para Correios com captcha"""

    def __init__(self):
        super().__init__(nome="Correios")
        self.base_url = "https://rastreamento.correios.com.br"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": f"{self.base_url}/"
        })

    def baixar_captcha(self) -> str:
        """
        Baixa o captcha dos Correios e salva como arquivo temporário.

        Returns:
            Caminho do arquivo do captcha salvo
        """
        try:
            # Acessa a página inicial pra iniciar sessão
            self.session.get(f"{self.base_url}/")

            # Baixa o captcha
            captcha_url = f"{self.base_url}/core/securimage/securimage_show.php"
            response = self.session.get(captcha_url)
            response.raise_for_status()

            # Salva captcha temporariamente
            os.makedirs('temp_downloads', exist_ok=True)
            captcha_path = 'temp_downloads/captcha_correios.jpg'

            with open(captcha_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Captcha dos Correios salvo em: {captcha_path}")
            return captcha_path

        except Exception as e:
            logger.error(f"Erro ao baixar captcha: {str(e)}")
            return ""

    def consultar_com_captcha(self, codigo_rastreio: str, captcha_texto: str) -> dict:
        """
        Consulta rastreamento usando código de rastreio e captcha.

        Args:
            codigo_rastreio: Código de rastreio (ex: AB569530491BR)
            captcha_texto: Texto do captcha resolvido pelo usuário

        Returns:
            Dict com dados do rastreamento ou erro
        """
        try:
            logger.info(f"Consultando Correios - Código: {codigo_rastreio}, Captcha: {captcha_texto}")

            rast_url = f"{self.base_url}/app/resultado.php"
            params = {
                "objeto": codigo_rastreio.strip().upper(),
                "captcha": captcha_texto.strip(),
                "mqs": "S"
            }

            response = self.session.get(rast_url, params=params, timeout=30)
            response.raise_for_status()

            # Tenta parsear JSON
            try:
                dados = response.json()
                return dados
            except:
                # Se não for JSON, retorna HTML
                return {"html": response.text}

        except Exception as e:
            logger.error(f"Erro ao consultar Correios: {str(e)}")
            return {"erro": "true", "mensagem": f"Erro na consulta: {str(e)}"}

    def consultar_por_cpf(self, cpf: str) -> dict:
        """
        Correios não usa CPF, mas mantém método por herança.
        """
        return {"erro": "true", "mensagem": "Correios usa código de rastreio, não CPF"}

    def extrair_pedidos(self, dados_resposta: dict) -> list:
        """
        Extrai eventos de rastreamento da resposta dos Correios.

        Args:
            dados_resposta: Dict com resposta da API

        Returns:
            Lista com eventos formatados
        """
        if not dados_resposta or dados_resposta.get('erro') == 'true':
            return []

        eventos = dados_resposta.get('eventos', [])
        return eventos

    def formatar_rastreamento(self, pedido: dict) -> str:
        """
        Formata dados de rastreamento dos Correios mostrando apenas o status atual.

        Args:
            pedido: Dict com dados completos do rastreamento

        Returns:
            Mensagem formatada
        """
        if not pedido or pedido.get('erro') == 'true':
            return f"❌ {pedido.get('mensagem', 'Erro ao consultar rastreamento')}"

        codigo = pedido.get('codObjeto', 'N/A')
        tipo_postal = pedido.get('tipoPostal', {})
        categoria = tipo_postal.get('categoria', 'N/A')
        descricao = tipo_postal.get('descricao', 'N/A')
        dt_prevista = pedido.get('dtPrevista', 'N/A')
        eventos = pedido.get('eventos', [])

        mensagem = f"📦 *RASTREAMENTO - CORREIOS*\n\n"
        mensagem += f"📋 *Código:* {codigo}\n"
        mensagem += f"📮 *Tipo:* {descricao}\n"
        mensagem += f"🏷️ *Categoria:* {categoria}\n"
        mensagem += f"📅 *Previsão de Entrega:* {dt_prevista}\n\n"
        
        # Mostra apenas o último evento (status atual)
        if eventos:
            ultimo_evento = eventos[0]
            descricao_evento = ultimo_evento.get('descricao', 'N/A')
            data_evento = ultimo_evento.get('dtHrCriado', 'N/A')
            
            unidade = ultimo_evento.get('unidade', {})
            local = unidade.get('nome', 'N/A') if unidade else 'N/A'
            
            mensagem += f"📍 *STATUS ATUAL:*\n\n"
            mensagem += f"🔹 {descricao_evento}\n"
            mensagem += f"   📅 {data_evento}\n"
            mensagem += f"   📍 {local}\n"
        else:
            mensagem += "❌ Nenhum evento de rastreamento disponível.\n"

        mensagem += f"📍 *EVENTOS DE RASTREAMENTO:*\n\n"

        for evento in eventos:
            descricao_evento = evento.get('descricao', 'N/A')
            dt_hr = evento.get('dtHrCriado', {})
            data_evento = dt_hr.get('date', 'N/A') if isinstance(dt_hr, dict) else str(dt_hr)
            unidade = evento.get('unidade', {})
            nome_unidade = unidade.get('nome', 'N/A') if isinstance(unidade, dict) else 'N/A'
            tipo_unidade = unidade.get('tipo', '') if isinstance(unidade, dict) else ''

            mensagem += f"🔹 *{descricao_evento}*\n"
            mensagem += f"   📅 {data_evento}\n"
            if nome_unidade != 'N/A':
                mensagem += f"   📍 {nome_unidade} - {tipo_unidade}\n"
            mensagem += "\n"

        return mensagem.strip()

    def validar_codigo_rastreio(self, codigo: str) -> bool:
        """
        Valida formato do código de rastreio dos Correios.
        Formato: 2 letras + 9 números + 2 letras (ex: AB123456789BR)

        Args:
            codigo: Código a validar

        Returns:
            True se válido
        """
        import re
        padrao = r'^[A-Z]{2}\d{9}[A-Z]{2}$'
        return bool(re.match(padrao, codigo.strip().upper()))


# Instância global
correios = CorreiosTransportadora()
