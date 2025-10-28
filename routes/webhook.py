from flask import Blueprint, request, jsonify
from utils.evolutionAPI import EvolutionAPI
from ia import perguntar_ia
import logging
from datetime import datetime
import os
from dotenv import load_dotenv
import time
import threading
from config.globals import redis_client
from services.audio_processor import AudioProcessor 

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)
evolution = EvolutionAPI()


@webhook_bp.route('/webhook', methods=['POST'])
def receber_webhook():
    data = request.json

    logger.info(f"Webhook recebido: {datetime.now().isoformat()}")

    try:
        event = data.get("event", "")
        instance_name = data.get("instance", "")

        api_key = os.getenv("AUTHENTICATION_API_KEY")  
        if not api_key:
            logger.error("API Key da Evolution API não encontrada nas variáveis de ambiente")
            return jsonify({"status": "erro", "message": "API Key ausente"}), 400

        if event != "messages.upsert":
            logger.info(f"Evento ignorado: {event}")
            return jsonify({"status": "ignorado: evento não é messages.upsert"}), 200

        message_data = data.get("data", {})
        key_data = message_data.get("key", {})
        sender = key_data.get("remoteJid", "")
        from_me = key_data.get("fromMe", False)

        if sender and sender.endswith("@g.us"):
            logger.info(f"Ignorado grupo: {sender}")
            return jsonify({"status": "ignorado: grupo"}), 200

        message_content = message_data.get("message", {})
        audio_message = message_content.get('audioMessage')

        mensagem = "" 

        if audio_message:

            mensagem = AudioProcessor.processar_audio_evolution(
                message_data=message_data,
                instance=instance_name,
                instance_key=api_key
            )

            if not mensagem or not mensagem.strip():
                logger.error("Falha ao transcrever áudio")
                return jsonify({"status": "erro", "message": "Não consegui entender o áudio. Tente novamente."}), 500

            import re
            mensagem_limpa = re.sub(r'[-,\s.]+', '', mensagem)

            if re.match(r'^[\d\-,\s.]+$', mensagem.strip()):
                logger.info(f"Áudio de NF detectado - Original: '{mensagem}' | Limpo: '{mensagem_limpa}'")
                mensagem = mensagem_limpa

            logger.info(f"Mensagem processada do áudio: '{mensagem}'")
        else:

            message_content = message_data.get("message", {})
            if "conversation" in message_content:
                mensagem = message_content["conversation"]
            elif "extendedTextMessage" in message_content:
                mensagem = message_content["extendedTextMessage"]["text"]
            elif "imageMessage" in message_content:
                mensagem = message_content["imageMessage"].get("caption", "")
            elif "videoMessage" in message_content:
                mensagem = message_content["videoMessage"].get("caption", "")


        if not mensagem.strip():
            logger.info(f"Ignorada mensagem vazia: {sender}")
            return jsonify({"status": "ignorado: mensagem vazia"}), 200

        sender_number = sender.split("@")[0] if sender and "@" in sender else None

        if not sender_number or not sender_number.isdigit():
            logger.error(f"Número inválido extraído: {sender}")
            return jsonify({"status": "erro", "message": "Número inválido"}), 400

        if not instance_name:
            logger.error("Instância não fornecida")
            return jsonify({"status": "erro", "message": "Instância ausente"}), 400

        if not api_key:
            logger.error("API Key da Evolution não encontrada")
            return jsonify({"status": "erro", "message": "API Key ausente"}), 500

        logger.info(f"Processando mensagem de {sender_number}: {mensagem}")

        timestamp_atual = time.time()
        redis_key = f"last_message:{sender_number}"
        redis_client.set(redis_key, {"timestamp": timestamp_atual, "message": mensagem}, ex=20)

        def processar_com_delay():
            time.sleep(15)

            ultima_mensagem = redis_client.get(redis_key)
            if not ultima_mensagem or ultima_mensagem.get("timestamp") != timestamp_atual:
                logger.info(f"Nova mensagem detectada de {sender_number}, cancelando processamento desta")
                return

            try:
                resposta = perguntar_ia(mensagem, instance_name, sender_number)
                logger.info(f"Resposta da IA: {resposta}")

                response_data = evolution.enviar_mensagem(
                    message=resposta,
                    instance=instance_name,
                    instance_key=api_key,
                    sender_number=sender_number
                )
                logger.info(f"Mensagem enviada com sucesso: {response_data}")

            except Exception as e:
                logger.error(f"Erro ao processar mensagem com IA: {str(e)}")
                evolution.enviar_mensagem(
                    message="Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente mais tarde.",
                    instance=instance_name,
                    instance_key=api_key,
                    sender_number=sender_number
                )

        thread = threading.Thread(target=processar_com_delay, daemon=True)
        thread.start()

        return jsonify({"status": "processado"}), 200

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "erro", "message": str(e)}), 500


@webhook_bp.route('/webhook', methods=['GET'])
def verificar_webhook():
    return jsonify({"status": "ativo", "serviço": "Luft Solutions"}), 200