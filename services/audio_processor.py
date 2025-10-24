
import base64
import os
import logging
import requests
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class AudioProcessor:
    """Processador de mensagens de áudio do WhatsApp"""

    @staticmethod
    def processar_audio_evolution(message_id, instance, instance_key):
        """
        Baixa áudio usando a Evolution API e retorna a transcrição usando Whisper
        
        Args:
            message_id: ID da mensagem do WhatsApp
            instance: Nome da instância
            instance_key: API key da Evolution
            
        Returns:
            str: Texto transcrito ou None em caso de erro
        """
        temp_audio_path = None
        
        try:
            # Criar diretório temporário se não existir
            os.makedirs('temp_audio', exist_ok=True)
            
            # Gerar nome único para o arquivo
            timestamp = int(time.time() * 1000)
            temp_audio_path = f"temp_audio/audio_{timestamp}.ogg"
            
            # Baixar o áudio usando Evolution API
            evolution_url = f"http://localhost:8080/message/downloadMedia/{instance}"
            headers = {"apikey": instance_key}
            payload = {"messageId": message_id}
            
            logger.info(f"📥 Baixando áudio via Evolution API - Message ID: {message_id}")
            response = requests.post(evolution_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extrair base64 da resposta
            response_data = response.json()
            audio_base64 = response_data.get('base64')
            
            if not audio_base64:
                logger.error("Evolution API não retornou base64")
                return None
            
            # Decodificar base64 e salvar arquivo
            audio_data = base64.b64decode(audio_base64)
            with open(temp_audio_path, "wb") as f:
                f.write(audio_data)
            
            file_size = os.path.getsize(temp_audio_path)
            logger.info(f"Áudio salvo temporariamente: {temp_audio_path} ({file_size} bytes)")
            
            # Verificar se o arquivo tem conteúdo
            if file_size < 100:
                logger.warning(f"Arquivo de áudio muito pequeno: {file_size} bytes")
                return None
            
            # Transcrever usando Whisper
            with open(temp_audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",
                    response_format="text"
                )
            
            texto_transcrito = transcription if isinstance(transcription, str) else transcription.text
            logger.info(f"📝 Transcrição concluída: '{texto_transcrito}' ({len(texto_transcrito)} caracteres)")
            
            return texto_transcrito.strip() if texto_transcrito else None
            
        except requests.RequestException as e:
            logger.error(f"Erro ao baixar áudio via Evolution: {str(e)}")
            return None
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

    @staticmethod
    def processar_audio(audio_base64):
        """
        Processa áudio base64 e retorna a transcrição usando Whisper
        (Mantido para compatibilidade)
        
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
            timestamp = int(time.time() * 1000)
            temp_audio_path = f"temp_audio/audio_{timestamp}.ogg"
            
            # Decodificar base64 e salvar arquivo
            audio_data = base64.b64decode(audio_base64)
            with open(temp_audio_path, "wb") as f:
                f.write(audio_data)
            
            file_size = os.path.getsize(temp_audio_path)
            logger.info(f"Áudio salvo temporariamente: {temp_audio_path} ({file_size} bytes)")
            
            # Transcrever usando Whisper
            with open(temp_audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",
                    response_format="text"
                )
            
            texto_transcrito = transcription if isinstance(transcription, str) else transcription.text
            logger.info(f"📝 Transcrição concluída: '{texto_transcrito}'")
            
            return texto_transcrito.strip() if texto_transcrito else None
            
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
