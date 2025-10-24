
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
            # Criar diretório temporário se não existir
            os.makedirs('temp_audio', exist_ok=True)
            
            # Gerar nome único para o arquivo
            timestamp = int(time.time() * 1000)
            temp_audio_path = f"temp_audio/audio_{timestamp}.ogg"
            
            # Primeiro, vamos logar a estrutura completa da mensagem para debug
            logger.info(f"📦 ESTRUTURA COMPLETA DA MENSAGEM:")
            logger.info(f"📦 message_data keys: {list(message_data.keys())}")
            logger.info(f"📦 message_data completo: {message_data}")
            
            # Extrair informações do áudio
            audio_message = message_data.get('message', {}).get('audioMessage', {})
            logger.info(f"🎵 audioMessage: {audio_message}")
            
            # A Evolution API geralmente usa o endpoint /chat/fetchMedia ou similar
            # Vamos tentar diferentes abordagens
            
            from urllib.parse import quote
            instance_encoded = quote(instance)
            
            # Opção 1: Tentar baixar mídia diretamente via Evolution API
            # O endpoint correto geralmente é /chat/downloadMediaMessage ou /message/downloadMedia
            evolution_url = f"http://localhost:8080/chat/downloadMediaMessage/{instance_encoded}"
            
            headers = {
                "apikey": instance_key,
                "Content-Type": "application/json"
            }
            
            # Extrair key da mensagem
            message_key = message_data.get('key', {})
            
            # Payload conforme documentação da Evolution API
            payload = {
                "key": message_key
            }
            
            logger.info(f"📥 Baixando áudio via Evolution API")
            logger.info(f"📡 URL: {evolution_url}")
            logger.info(f"📡 Headers: {headers}")
            logger.info(f"📡 Payload: {payload}")
            
            # Tentar endpoint 1: /chat/downloadMediaMessage
            response = requests.post(evolution_url, json=payload, headers=headers, timeout=30)
            
            logger.info(f"📥 Tentativa 1 - Status: {response.status_code}")
            
            # Se falhar, tentar outros endpoints
            if response.status_code == 404:
                logger.info("⚠️ Endpoint 1 não encontrado, tentando alternativa 2...")
                evolution_url = f"http://localhost:8080/message/downloadMedia/{instance_encoded}"
                response = requests.post(evolution_url, json=payload, headers=headers, timeout=30)
                logger.info(f"📥 Tentativa 2 - Status: {response.status_code}")
            
            if response.status_code == 404:
                logger.info("⚠️ Endpoint 2 não encontrado, tentando alternativa 3...")
                # Tentar com o messageId diretamente
                message_id = message_key.get('id')
                payload_alt = {"messageId": message_id}
                evolution_url = f"http://localhost:8080/chat/getBase64FromMediaMessage/{instance_encoded}"
                response = requests.post(evolution_url, json=payload_alt, headers=headers, timeout=30)
                logger.info(f"📥 Tentativa 3 - Status: {response.status_code}")
            
            logger.info(f"📥 Headers da resposta: {dict(response.headers)}")
            
            # DEBUG: Sempre logar a resposta completa
            try:
                response_text = response.text
                logger.info(f"📥 RESPOSTA COMPLETA (texto): {response_text}")
                
                if response.status_code == 200 or response.status_code == 201:
                    response_data = response.json()
                    logger.info(f"📥 RESPOSTA COMPLETA (JSON): {response_data}")
                    logger.info(f"📥 Campos da resposta: {list(response_data.keys())}")
                    logger.info(f"📥 Tipo de cada campo: {[(k, type(v).__name__) for k, v in response_data.items()]}")
                else:
                    logger.error(f"❌ Erro na API: {response.status_code} - {response_text}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Erro ao parsear resposta: {str(e)}")
                logger.error(f"❌ Resposta bruta: {response.text}")
                return None
            
            # Tentar extrair base64 de diferentes campos possíveis
            audio_base64 = None
            
            # Lista de campos possíveis onde o base64 pode estar
            possible_fields = [
                'base64',
                'media', 
                'base64Media',
                'mediaBase64',
                'audio',
                'audioBase64',
                'data',
                'content',
                'file'
            ]
            
            for field in possible_fields:
                if field in response_data:
                    audio_base64 = response_data[field]
                    logger.info(f"✅ Base64 encontrado no campo '{field}': {len(str(audio_base64))} caracteres")
                    break
            
            # Se não encontrou diretamente, verificar objetos aninhados
            if not audio_base64:
                for key, value in response_data.items():
                    if isinstance(value, dict):
                        logger.info(f"📦 Verificando objeto aninhado '{key}': {list(value.keys())}")
                        for field in possible_fields:
                            if field in value:
                                audio_base64 = value[field]
                                logger.info(f"✅ Base64 encontrado em '{key}.{field}': {len(str(audio_base64))} caracteres")
                                break
                        if audio_base64:
                            break
            
            if not audio_base64:
                logger.error(f"❌ Base64 não encontrado em nenhum campo conhecido")
                logger.error(f"❌ Estrutura completa da resposta: {response_data}")
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
