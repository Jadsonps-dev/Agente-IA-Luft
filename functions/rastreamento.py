
"""
Módulo responsável por processar rastreamento de pedidos.
"""
import re
import logging
from config.globals import redis_client
from api import rastrear_pedido

logger = logging.getLogger(__name__)


def eh_cpf(mensagem: str) -> bool:
    """
    Detecta se a mensagem é um CPF (com ou sem pontuação).

    Args:
        mensagem: Texto da mensagem

    Returns:
        True se é um CPF válido
    """
    cpf_limpo = re.sub(r'\D', '', mensagem.strip())

    if len(cpf_limpo) == 11 and cpf_limpo.isdigit():
        logger.info(f"CPF detectado: {cpf_limpo}")
        return True

    return False


def eh_codigo_rastreio(mensagem: str) -> bool:
    """
    Detecta se uma mensagem é um código de rastreio.
    Códigos de rastreio geralmente têm mais de 10 caracteres e podem conter letras.
    NFs geralmente são apenas números com 6-9 dígitos.

    Args:
        mensagem: Mensagem do usuário

    Returns:
        True se parecer um código de rastreio
    """
    codigo = mensagem.strip().upper()
    codigo_limpo = re.sub(r'\D', '', codigo)

    if codigo.isdigit() and len(codigo) < 10:
        return False

    if codigo.isdigit() and len(codigo) >= 10:
        logger.info(f"Código de rastreio Magalog detectado: {codigo}")
        return True

    if 8 <= len(codigo) <= 25:
        tem_letra = any(c.isalpha() for c in codigo)
        tem_numero = any(c.isdigit() for c in codigo)

        if tem_letra and tem_numero:
            logger.info(f"Código de rastreio alfanumérico detectado: {codigo}")
            return True

    return False


def detectar_tipo_rastreamento(transportadora: str) -> str:
    """
    Detecta qual informação solicitar com base na transportadora.

    Args:
        transportadora: Nome da transportadora

    Returns:
        'cpf', 'codigo' ou 'correios' - tipo de dado necessário
    """
    transportadora_lower = transportadora.lower()

    if 'magalog' in transportadora_lower or 'magalu log' in transportadora_lower:
        return 'codigo'
    
    if 'correios' in transportadora_lower or 'empresa brasileira' in transportadora_lower:
        return 'correios'

    if 'dialogo' in transportadora_lower or 'diálogo' in transportadora_lower:
        return 'cpf'
    
    if 'logan' in transportadora_lower:
        return 'cpf'
    
    if 'cooperativa' in transportadora_lower or 'rede sul' in transportadora_lower:
        return 'cpf'

    return 'cpf'


def processar_correios_captcha(sender: str) -> tuple:
    """
    Inicia processo de captcha dos Correios.

    Args:
        sender: Número do remetente

    Returns:
        Tupla (caminho_captcha, mensagem_erro)
    """
    try:
        from api import obter_transportadora
        correios_api = obter_transportadora('correios')
        
        captcha_path = correios_api.baixar_captcha()
        
        if not captcha_path:
            return None, "❌ Erro ao baixar captcha dos Correios. Tente novamente."
        
        # Salva flag indicando que está aguardando captcha
        redis_client.set(f"aguardando_captcha:{sender}", "true", ex=300)
        
        return captcha_path, None
        
    except Exception as e:
        logger.error(f"Erro ao processar captcha: {str(e)}")
        return None, "❌ Erro ao processar captcha. Tente novamente."


def processar_correios_rastreamento(codigo_rastreio: str, captcha_texto: str, sender: str) -> str:
    """
    Processa rastreamento dos Correios com captcha resolvido.

    Args:
        codigo_rastreio: Código de rastreio
        captcha_texto: Texto do captcha
        sender: Número do remetente

    Returns:
        Mensagem formatada
    """
    try:
        from api import obter_transportadora
        correios_api = obter_transportadora('correios')
        
        # Valida código de rastreio
        if not correios_api.validar_codigo_rastreio(codigo_rastreio):
            return "❌ Código de rastreio inválido. Use o formato: AB123456789BR"
        
        # Consulta com captcha
        dados = correios_api.consultar_com_captcha(codigo_rastreio, captcha_texto)
        
        # Verifica se captcha está inválido
        if dados.get('erro') == 'true':
            mensagem_erro = dados.get('mensagem', '')
            if 'captcha' in mensagem_erro.lower():
                logger.warning(f"Captcha inválido para {sender}, solicitando novo")
                return "captcha_invalido"  # Sinal especial para reenviar captcha
            return f"❌ {mensagem_erro}"
        
        # Formata resultado
        resultado = correios_api.formatar_rastreamento(dados)
        
        # Limpa flags
        redis_client.delete(f"aguardando_captcha:{sender}")
        redis_client.delete(f"codigo_rastreio_correios:{sender}")
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro ao processar rastreamento Correios: {str(e)}")
        return "❌ Erro ao processar rastreamento. Tente novamente."


def processar_rastreamento(mensagem: str, sender: str, tipo: str) -> str:
    """
    Processa o rastreamento com base no tipo (CPF, código de rastreio ou Correios).

    Args:
        mensagem: Mensagem do usuário contendo CPF, código ou captcha.
        sender: Número do remetente.
        tipo: 'cpf', 'codigo' ou 'correios'.

    Returns:
        Mensagem formatada com rastreamento ou erro.
    """
    try:
        from functions.contexto import obter_contexto_nf
        contexto = obter_contexto_nf(sender)

        if not contexto:
            if tipo == 'cpf':
                return "❌ Para rastrear seu pedido, primeiro consulte o número da nota fiscal e depois envie seu CPF."
            elif tipo == 'correios':
                return "❌ Para rastrear pelos Correios, primeiro consulte o número da nota fiscal."
            else:
                return "❌ Para rastrear seu pedido, primeiro consulte o número da nota fiscal e depois envie o código de rastreio."

        numero_nf = contexto.get('numero_nf')
        status = contexto.get('status', '')
        transportadora_nome = contexto.get('transportadora', '')
        codigo_rastreio_contexto = contexto.get('codigo_rastreio', '')
        tipo_esperado = contexto.get('tipo_rastreamento', 'cpf')

        if status != 'EXPEDIDO':
            return f"❌ O pedido {numero_nf} não está com status EXPEDIDO. Status atual: {status}"

        # Para Correios, sempre aceita código de rastreio
        if tipo_esperado == 'correios':
            if tipo != 'codigo':
                return f"❌ Para rastrear pelos Correios, envie o código de rastreio (ex: AB123456789BR)."
        elif tipo_esperado == 'codigo' and tipo != 'codigo':
            return f"❌ A transportadora {transportadora_nome} requer o código de rastreio, não CPF."
        elif tipo_esperado == 'cpf' and tipo != 'cpf':
            return f"❌ A transportadora {transportadora_nome} requer o CPF do destinatário, não código de rastreio."

        transportadora_lower = transportadora_nome.lower()
        
        if 'magalog' in transportadora_lower or 'magalu log' in transportadora_lower:
            transportadora_key = 'magalog'
            dado_rastreio = mensagem.strip()
            logger.info(f"Rastreando Magalog - Código: {dado_rastreio}")

            from api import obter_transportadora
            magalog_api = obter_transportadora('magalog')
            pedido = magalog_api.buscar_pedido_por_codigo(dado_rastreio)

            if pedido:
                resultado = magalog_api.formatar_rastreamento(pedido)
            else:
                resultado = f"❌ Não foi possível rastrear o código {dado_rastreio} na Magalog. Verifique se o código está correto."

        elif 'logan' in transportadora_lower:
            transportadora_key = 'logan'
            dado_rastreio = mensagem
            primeiro_nome = contexto.get('primeiro_nome', '')
            cep = contexto.get('cep', '')
            codigo_rastreio_wms = contexto.get('codigo_rastreio', '')
            
            logger.info(f"Rastreando via Logan - Código WMS: {codigo_rastreio_wms}, CPF, Nome: {primeiro_nome}, CEP: {cep}")
            
            from api import obter_transportadora
            logan_api = obter_transportadora('logan')
            pedido = logan_api.buscar_pedido_com_dados_completos(dado_rastreio, primeiro_nome, cep, codigo_rastreio_wms)
            
            if pedido:
                resultado = logan_api.formatar_rastreamento(pedido)
            else:
                resultado = f"❌ Não foi possível rastrear o código {codigo_rastreio_wms} na Logan. Verifique os dados informados."
        
        elif 'cooperativa' in transportadora_lower or 'rede sul' in transportadora_lower:
            transportadora_key = 'redesul'
            dado_rastreio = mensagem
            logger.info(f"Rastreando NF {numero_nf} via Rede Sul com CPF")
            
            from api import obter_transportadora
            redesul_api = obter_transportadora('redesul')
            pedido = redesul_api.buscar_pedido_especifico(dado_rastreio, numero_nf)
            
            if pedido:
                resultado = redesul_api.formatar_rastreamento(pedido)
            else:
                resultado = f"❌ Não foi possível rastrear o pedido {numero_nf} na Rede Sul. Verifique os dados informados."
        
        elif 'correios' in transportadora_lower or 'empresa brasileira' in transportadora_lower:
            # Correios requer captcha
            codigo_rastreio_correios = contexto.get('codigo_rastreio', '')
            
            # Verifica se já tem código de rastreio salvo
            codigo_salvo = redis_client.get(f"codigo_rastreio_correios:{sender}")
            
            if codigo_salvo:
                # Cliente enviou o captcha
                captcha_texto = mensagem.strip()
                resultado = processar_correios_rastreamento(codigo_salvo, captcha_texto, sender)
                
                if resultado == "captcha_invalido":
                    # Captcha errado, envia novo
                    return "correios_novo_captcha"
            else:
                # Cliente enviou código de rastreio, precisa do captcha
                redis_client.set(f"codigo_rastreio_correios:{sender}", mensagem.strip(), ex=300)
                return "correios_solicitar_captcha"
        
        elif 'dialogo' in transportadora_lower or 'diálogo' in transportadora_lower:
            transportadora_key = 'dialogo'
            dado_rastreio = mensagem
            logger.info(f"Rastreando NF {numero_nf} via {transportadora_key} com CPF")
            resultado = rastrear_pedido(dado_rastreio, numero_nf, transportadora=transportadora_key)
        else:
            transportadora_key = 'dialogo'
            dado_rastreio = mensagem
            logger.info(f"🔍 Rastreando NF {numero_nf} via {transportadora_key} com {tipo}")
            resultado = rastrear_pedido(dado_rastreio, numero_nf, transportadora=transportadora_key)

        redis_client.delete(f"contexto_nf:{sender}")

        return resultado

    except Exception as e:
        logger.error(f"Erro ao processar rastreamento: {str(e)}")
        return "❌ Erro ao buscar rastreamento. Tente novamente em alguns instantes."
