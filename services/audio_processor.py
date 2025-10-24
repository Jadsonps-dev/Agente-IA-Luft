import base64
import os
import logging
import requests
from openai import OpenAI
from dotenv import load_dotenv
import time
from urllib.parse import quote

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AudioProcessor:
    """Processador de mensagens de áudio do WhatsApp"""

    @staticmethod
    def processar_audio_evolution(message_data, instance, instance_key):
        """
        Baixa áudio usando a Evolution API e retorna a transcrição usando Whisper

        Args:
            message_data: Dados completos da mensagem do webhook
            instance: Nome da instância
            instance_key: API key da Evolution

        Returns:
            str: Texto transcrito ou None em caso de erro
        """
        temp_audio_path = None

        try:
            os.makedirs('temp_audio', exist_ok=True)

            timestamp = int(time.time() * 1000)
            temp_audio_path = f"temp_audio/audio_{timestamp}.ogg"

            message_obj = message_data.get('message', {})

            if not message_obj:
                logger.error("❌ 'message' não encontrado na mensagem")
                return None

            audio_base64 = message_obj.get('base64')

            if not audio_base64:
                logger.error("❌ Base64 do áudio não encontrado")
                return None

            # Decodificar e salvar áudio
            audio_data = base64.b64decode(audio_base64)
            with open(temp_audio_path, "wb") as f:
                f.write(audio_data)

            file_size = os.path.getsize(temp_audio_path)

            if file_size < 100:
                logger.warning(f"⚠️ Arquivo muito pequeno: {file_size} bytes")
                return None

            # Transcrever com Whisper
            with open(temp_audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",
                    response_format="text"
                )

            texto_transcrito = transcription if isinstance(transcription, str) else transcription.text
            logger.info(f"📝 Áudio transcrito: '{texto_transcrito}'")

            return texto_transcrito.strip() if texto_transcrito else None

        except requests.RequestException as e:
            logger.error(f"❌ Erro HTTP ao processar áudio: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"❌ Resposta: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao processar áudio: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                    logger.info(f"🗑️ Arquivo temporário removido: {temp_audio_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao remover arquivo: {str(e)}")