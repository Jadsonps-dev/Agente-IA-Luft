
import base64
import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AudioProcessor:
    """Processador de mensagens de áudio do WhatsApp"""

    @staticmethod
    def processar_audio(audio_base64):
        """
        Processa áudio base64 e retorna a transcrição usando Whisper
        
        Args:
            audio_base64: String base64 do áudio
            
        Returns:
            str: Texto transcrito ou None em caso de erro
        """
        temp_audio_path = None
        
        try:
            # Criar diretório temporário se não existir
            os.makedirs('temp_audio', exist_ok=True)
            
            # Gerar nome único para o arquivo
            import time
            timestamp = int(time.time() * 1000)
            temp_audio_path = f"temp_audio/audio_{timestamp}.ogg"
            
            # Decodificar base64 e salvar arquivo
            audio_data = base64.b64decode(audio_base64)
            with open(temp_audio_path, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"Áudio salvo temporariamente em: {temp_audio_path}")
            
            # Transcrever usando Whisper
            with open(temp_audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
            
            texto_transcrito = transcription.text
            logger.info(f"📝 Transcrição concluída: {texto_transcrito}")
            
            return texto_transcrito
            
        except Exception as e:
            logger.error(f"Erro ao processar áudio: {str(e)}")
            return None
            
        finally:
            # Limpar arquivo temporário
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                    logger.info(f"Arquivo temporário removido: {temp_audio_path}")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo temporário: {str(e)}")
