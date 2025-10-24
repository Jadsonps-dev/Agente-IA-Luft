
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
            # Criar diretório temporário se não existir
            os.makedirs('temp_audio', exist_ok=True)
            
            # Gerar nome único para o arquivo
            timestamp = int(time.time() * 1000)
            temp_audio_path = f"temp_audio/audio_{timestamp}.ogg"
            
            # Baixar o áudio usando Evolution API - endpoint correto
            evolution_url = f"http://localhost:8080/message/getBase64FromMediaMessage/{instance}"
            headers = {
                "apikey": instance_key,
                "Content-Type": "application/json"
            }
            
            # Payload com a estrutura completa da mensagem
            payload = {
                "message": message_data
            }
            
            logger.info(f"📥 Baixando áudio via Evolution API")
            logger.info(f"📡 URL: {evolution_url}")
            
            response = requests.post(evolution_url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"📥 Status da resposta: {response.status_code}")
            
            if response.status_code != 200 and response.status_code != 201:
                logger.error(f"❌ Erro na API: {response.status_code} - {response.text}")
                return None
            
            # Extrair base64 da resposta
            response_data = response.json()
            logger.info(f"📥 Campos da resposta: {list(response_data.keys())}")
            
            # O base64 pode vir em diferentes campos
            audio_base64 = (
                response_data.get('base64') or 
                response_data.get('media') or
                response_data.get('base64Media')
            )
            
            if not audio_base64:
                logger.error(f"❌ Base64 não encontrado na resposta. Dados: {response_data}")
                return None
            
            logger.info(f"✅ Base64 obtido: {len(audio_base64)} caracteres")
            
            # Decodificar base64 e salvar arquivo
            audio_data = base64.b64decode(audio_base64)
            with open(temp_audio_path, "wb") as f:
                f.write(audio_data)
            
            file_size = os.path.getsize(temp_audio_path)
            logger.info(f"💾 Áudio salvo: {temp_audio_path} ({file_size} bytes)")
            
            # Verificar se o arquivo tem conteúdo
            if file_size < 100:
                logger.warning(f"⚠️ Arquivo muito pequeno: {file_size} bytes")
                return None
            
            # Transcrever usando Whisper
            logger.info("🎤 Enviando para Whisper API...")
            with open(temp_audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt",
                    response_format="text"
                )
            
            texto_transcrito = transcription if isinstance(transcription, str) else transcription.text
            logger.info(f"✅ Transcrição: '{texto_transcrito}' ({len(texto_transcrito)} caracteres)")
            
            return texto_transcrito.strip() if texto_transcrito else None
            
        except requests.RequestException as e:
            logger.error(f"❌ Erro HTTP ao baixar áudio: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"❌ Resposta: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao processar áudio: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
        finally:
            # Limpar arquivo temporário
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                    logger.info(f"🗑️ Arquivo temporário removido: {temp_audio_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao remover arquivo: {str(e)}")

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
