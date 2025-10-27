import json
import redis

class RedisClient:
    def __init__(self, host='85.209.92.10', port=6379, db=6):
        self.redis_client = redis.Redis( 
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True
        )

        try:
            self.redis_client.ping()   
            print("Conexão com o Redis bem-sucedida!")
        except redis.exceptions.ConnectionError:
            print("Erro ao conectar ao Redis.")

    def set(self, key, data, ex=None):
        """Armazena os dados no Redis com suporte a expiração."""
        try:
            valor = json.dumps(data)
            if ex:
                return self.redis_client.set(key, valor, ex=ex)
            return self.redis_client.set(key, valor)
        except Exception as e:
            print(f"Erro ao salvar no Redis: {str(e)}")
            return False

    def get(self, key):
        """Recupera os dados do Redis."""
        data = self.redis_client.get(key)                      
        return json.loads(data) if data else None

    def delete(self, key):
        """Remove uma chave do Redis."""
        print(f"Tentando deletar chave: {key}")   
        return self.redis_client.delete(key)

    def set_conversa(self, sender, data):
        """Armazena o contexto da conversa."""
        self.set(f"conversa:{sender}", data)

    def get_conversa(self, sender):
        """Recupera o contexto da conversa."""
        return self.get(f"conversa:{sender}")

    def set_config_mode(self, sender, data):
        """Armazena os dados de config_mode."""
        self.set(f"config_mode:{sender}", data)

    def get_config_mode(self, sender):
        """Recupera os dados de config_mode."""
        return self.get(f"config_mode:{sender}")

redis_client = RedisClient()