import os
import time
import base64
import logging
import requests


class EvolutionAPI:
    def __init__(self):
        self.base_url = "http://localhost:8080"
        self.logger = logging.getLogger(__name__)

    def _make_request(self, method, endpoint, payload=None, headers=None):
        try:
            response = requests.request(
                method,
                f"{self.base_url}/{endpoint}",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            self.logger.error(
                f"Erro HTTP {response.status_code}: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro de conexão: {str(e)}")
            raise

    def enviar_mensagem(self, message, instance, instance_key, sender_number):
        """Envia mensagem de texto com tratamento completo de erros"""
        try:

            if not sender_number or not sender_number.strip().isdigit():
                raise ValueError(f"sender_number inválido: '{sender_number}'")

            if not instance or not instance.strip():
                raise ValueError(f"instance inválida: '{instance}'")

            if not instance_key:
                raise ValueError("instance_key (apikey) não fornecida")

            if not message or not message.strip():
                message = "(mensagem vazia)"

            payload = {
                "number": sender_number.strip(),
                "text": message.strip(),
                "delay": 2000,
            }

            headers = {
                "apikey": instance_key,
                "Content-Type": "application/json"
            }

            self.logger.info(f"Enviando mensagem para {sender_number} na instância {instance}")
            self.logger.info(f"Mensagem: {message[:100]}...")
            self.logger.info(f"Endpoint: {self.base_url}/message/sendText/{instance}")

            response = self._make_request(
                "POST", f"message/sendText/{instance}", payload, headers)

            json_response = response.json()

            return {
                "status": "success",
                "message_id": json_response.get('key', {}).get('id'),
                "timestamp": json_response.get('messageTimestamp')
            }

        except Exception as e:
            self.logger.error(f"Falha ao enviar mensagem: {str(e)}")
            return {"status": "error", "details": str(e)}

    def enviar_imagem(self, instance, apikey, phone, qr_filename):
        try:
            with open(qr_filename, "rb") as image_file:
                image_binary = image_file.read()

            base64_image = base64.b64encode(image_binary).decode('utf-8')

            payload = {
                "number": f"{phone}",
                "mediatype": "image",
                "mimetype": "image/png",  
                "caption": "",
                "media": base64_image,
                "fileName": qr_filename.split("/")[-1]
            }

            headers = {
                "apikey": apikey,
                "Content-Type": "application/json"
            }

            url = f"{self.base_url}/message/sendMedia/{instance}"

            print(f"Enviando para: {url}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            print(f"Resposta ({response.status_code}): {response.text}")

            if response.status_code == 201:
                print("Imagem enviada com sucesso!")
                return True
            else:
                print(f"Erro na API: {response.json().get('message', 'Erro desconhecido')}")
                return False

        except Exception as e:
            print(f"Erro crítico: {str(e)}")
            return False

    def download_media(self, media_id, instance, instance_key):
        """Baixa mídia com verificação de tipo e tamanho"""
        try:
            headers = {"apikey": instance_key}
            payload = {"mediaId": media_id}

            response = self._make_request(
                "POST", f"media/download/{instance}", payload, headers)

            content_type = response.headers.get('Content-Type', '')
            content_length = int(response.headers.get('Content-Length', 0))

            if content_length > 5 * 1024 * 1024:
                raise ValueError("Arquivo muito grande")

            if 'application/json' not in content_type:
                raise ValueError("Tipo de arquivo inválido")

            return {
                "status": "success",
                "content": response.content,
                "metadata": {
                    "type": content_type,
                    "size": content_length,
                    "encoding": response.encoding
                }
            }

        except Exception as e:
            self.logger.error(f"Falha no download: {str(e)}")
            return {"status": "error", "details": str(e)}

    def baixar_arquivo_de_whatsapp(self, media_data, instance, instance_key):
        try:

            if 'base64' in media_data:
                decoded_data = base64.b64decode(media_data['base64'])
                file_path = os.path.join('temp_downloads', f"credenciais_{int(time.time())}.json")

                os.makedirs('temp_downloads', exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.write(decoded_data)

                return True, file_path

            url = f"http://localhost:8080/message/sendMedia/{instance}"
            headers = {
                "apikey": instance_key,
                "Content-Type": "application/json"
            }

            payload = {
                "number": media_data['sender'],   
                "mediaMessage": {
                    "mediaType": "document",
                    "fileName": media_data.get('fileName', 'credenciais.json'),
                    "media": media_data['url']   
                }
            }

            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 201:
                file_url = response.json().get('message', {}).get('documentMessage', {}).get('url')
                if not file_url:
                    raise Exception("URL do arquivo não encontrada na resposta")

                file_response = requests.get(file_url, timeout=30)
                file_path = os.path.join('temp_downloads', f"credenciais_{int(time.time())}.json")

                with open(file_path, 'wb') as f:
                    f.write(file_response.content)

                return True, file_path

            raise Exception(f"Erro na API: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"FALHA NO PROCESSAMENTO: {str(e)}")
            return False, None