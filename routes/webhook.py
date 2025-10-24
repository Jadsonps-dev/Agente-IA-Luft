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

        # ✅ Usar a API Key diretamente do ambiente (não vem no webhook)
        api_key = os.getenv("AUTHENTICATION_API_KEY")  # Alterado para usar a variável correta
        if not api_key:
            logger.error("❌ API Key da Evolution API não encontrada nas variáveis de ambiente")
            return jsonify({"status": "erro", "message": "API Key ausente"}), 400

        if event != "messages.upsert":
            logger.info(f"Evento ignorado: {event}")
            return jsonify({"status": "ignorado: evento não é messages.upsert"}), 200

        message_data = data.get("data", {})
        key_data = message_data.get("key", {})
        sender = key_data.get("remoteJid", "")
        from_me = key_data.get("fromMe", False)

        logger.info(f"DEBUG - fromMe: {from_me}, sender: {sender}, instance: {instance_name}")

        if sender and sender.endswith("@g.us"):
            logger.info(f"Ignorado grupo: {sender}")
            return jsonify({"status": "ignorado: grupo"}), 200

        # Verificar se é mensagem de áudio
        message_content = message_data.get("message", {})
        audio_message = message_content.get('audioMessage')

        mensagem = "" # Inicializa a variável mensagem

        if audio_message:
            # Processar mensagem de áudio
            logger.info("🎤 Mensagem de áudio detectada")
            
            # Log para debug
            logger.info(f"DEBUG - Estrutura da mensagem: {list(message_data.keys())}")
            logger.info(f"DEBUG - audioMessage keys: {list(audio_message.keys())}")
            
            # Verificar se tem base64 no audioMessage
            audio_base64 = None
            
            # O base64 pode vir em diferentes campos dependendo da versão da Evolution
            if 'base64' in audio_message:
                audio_base64 = audio_message['base64']
                logger.info("✅ Base64 encontrado em audioMessage.base64")
            elif 'audio' in message_content:
                audio_base64 = message_content['audio'].get('base64')
                logger.info("✅ Base64 encontrado em message.audio.base64")
            
            if not audio_base64:
                logger.error(f"❌ Base64 não encontrado. Campos disponíveis: {list(audio_message.keys())}")
                logger.error(f"DEBUG - audioMessage completo: {audio_message}")
                return jsonify({"status": "erro", "message": "Áudio sem base64"}), 400

            # Transcrever áudio usando o base64 direto
            mensagem = AudioProcessor.processar_audio(audio_base64)

            if not mensagem or not mensagem.strip():
                logger.error("Falha ao transcrever áudio ou áudio vazio")
                return jsonify({"status": "erro", "message": "Não consegui entender o áudio. Tente novamente."}), 500

            logger.info(f"📝 Áudio transcrito: {mensagem}")
        else:
            # Processar mensagem de texto normal
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

        # Depois de extrair os dados
        sender_number = sender.split("@")[0] if sender and "@" in sender else None

        # 🔴 Validação antes de prosseguir
        if not sender_number or not sender_number.isdigit():
            logger.error(f"❌ Número inválido extraído: {sender}")
            return jsonify({"status": "erro", "message": "Número inválido"}), 400

        if not instance_name:
            logger.error("❌ Instância não fornecida")
            return jsonify({"status": "erro", "message": "Instância ausente"}), 400

        if not api_key:
            logger.error("❌ API Key da Evolution não encontrada")
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
                    message="⚠️ Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente mais tarde.",
                    instance=instance_name,
                    instance_key=api_key,
                    sender_number=sender_number
                )

        thread = threading.Thread(target=processar_com_delay, daemon=True)
        thread.start()

        return jsonify({"status": "processado"}), 200

    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {str(e)}")
        return jsonify({"status": "erro", "message": str(e)}), 500


@webhook_bp.route('/webhook', methods=['GET'])
def verificar_webhook():
    return jsonify({"status": "ativo", "serviço": "Luft Solutions"}), 200