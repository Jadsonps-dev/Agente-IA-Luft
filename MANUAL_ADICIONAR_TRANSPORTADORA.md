
# 📦 Manual - Como Adicionar Nova Transportadora

## 🎯 Visão Geral

Este manual ensina como adicionar novas transportadoras ao sistema de rastreamento. A estrutura foi projetada para ser **flexível e adaptável** a diferentes tipos de APIs.

---

## 🏗️ Estrutura do Sistema

```
api/
├── __init__.py              # ✅ Registro de transportadoras (SIM, adicione aqui!)
├── base_transportadora.py   # ✅ Classe base (flexível)
├── api_dialogo.py          # 📖 Exemplo: API que retorna HTML
└── api_NOVA.py             # 🆕 Sua nova transportadora
```

---

## 📋 Diferenças Entre Transportadoras

### Tipo de Consulta

| Transportadora | Parâmetro de Busca | Formato Resposta |
|----------------|-------------------|------------------|
| Dialogo        | CPF do destinatário | HTML |
| Jadlog         | CPF do destinatário | JSON |
| Correios       | Código de rastreio | XML |
| Azul Cargo     | Número da NF + CPF | JSON |
| Total Express  | Código de rastreio | HTML |

**Solução:** A classe base é **genérica** e aceita qualquer parâmetro!

---

## 🔧 Passo a Passo - Adicionar Transportadora

### **PASSO 1:** Criar arquivo da transportadora

Crie o arquivo `api/api_NOME.py`:

```python
"""
API de rastreamento para [NOME DA TRANSPORTADORA].
"""
import re
import logging
import requests
from api.base_transportadora import BaseTransportadora

logger = logging.getLogger(__name__)


class NOMETransportadora(BaseTransportadora):
    """Implementação para [NOME]"""

    def __init__(self):
        super().__init__(nome="NOME")
        # Configurações específicas da API
        self.url_base = "https://api.transportadora.com"
        self.api_key = "sua-chave-aqui"  # ou use variável de ambiente

    def consultar_por_cpf(self, cpf: str) -> dict:
        """
        Consulta pedidos usando CPF do destinatário.
        
        ATENÇÃO: Se sua transportadora NÃO usa CPF, renomeie este método!
        Exemplo: consultar_por_codigo_rastreio(self, codigo: str)
        
        Args:
            cpf: CPF do destinatário (ou outro parâmetro)

        Returns:
            Dict ou HTML com dados da resposta
        """
        try:
            # EXEMPLO 1: API que retorna JSON
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {"cpf": cpf}
            
            response = requests.post(
                f"{self.url_base}/rastreamento",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()  # ← Retorna JSON
            
            # EXEMPLO 2: API que retorna HTML (como Dialogo)
            # response = requests.get(url, timeout=30)
            # response.encoding = "iso-8859-1"
            # return response.text  # ← Retorna HTML
            
        except Exception as e:
            logger.error(f"Erro ao consultar {self.nome}: {str(e)}")
            return {}

    def extrair_pedidos(self, dados_resposta: dict) -> list:
        """
        Extrai lista de pedidos da resposta da API.

        Args:
            dados_resposta: Dados retornados por consultar_por_cpf()

        Returns:
            Lista de dicionários com pedidos
        """
        pedidos = []
        
        try:
            # EXEMPLO 1: Resposta JSON
            for item in dados_resposta.get('pedidos', []):
                pedido = {
                    'numero_fiscal': item.get('nf'),
                    'numero_pedido': item.get('pedido'),
                    'destinatario': item.get('destinatario'),
                    'eventos': []
                }
                
                for evento in item.get('rastreamento', []):
                    pedido['eventos'].append({
                        'data': evento.get('data'),
                        'status': evento.get('status'),
                        'localizacao': evento.get('local')
                    })
                
                pedidos.append(pedido)
            
            # EXEMPLO 2: Resposta HTML (como Dialogo)
            # from bs4 import BeautifulSoup
            # soup = BeautifulSoup(dados_resposta, 'html.parser')
            # ... parsing do HTML ...
            
            logger.info(f"Total de pedidos extraídos: {len(pedidos)}")
            return pedidos
            
        except Exception as e:
            logger.error(f"Erro ao extrair pedidos: {str(e)}")
            return []

    def formatar_rastreamento(self, pedido: dict) -> str:
        """
        Formata os dados do pedido para envio no WhatsApp.

        Args:
            pedido: Dicionário com dados do pedido

        Returns:
            Mensagem formatada com emojis
        """
        if not pedido:
            return "❌ Pedido não encontrado"

        mensagem = f"📦 *RASTREAMENTO - {self.nome.upper()}*\n\n"
        
        if pedido.get('destinatario'):
            mensagem += f"👤 *Destinatário:* {pedido['destinatario']}\n"
        
        mensagem += f"🧾 *Nota Fiscal:* {pedido.get('numero_fiscal', 'N/A')}\n"
        
        if pedido.get('numero_pedido'):
            mensagem += f"🔢 *Pedido:* {pedido['numero_pedido']}\n"

        eventos = pedido.get('eventos', [])
        
        if not eventos:
            mensagem += "\n⚠️ Nenhum evento de rastreamento encontrado."
            return mensagem

        mensagem += "\n📍 *HISTÓRICO:*\n"

        # Mapear status para emojis (personalize conforme sua transportadora)
        emoji_map = {
            'ENTREGUE': '✅',
            'EM_TRANSITO': '🚚',
            'SAIU_PARA_ENTREGA': '📦',
            'COLETADO': '📥',
        }

        for evento in eventos:
            status = evento.get('status', '')
            emoji = emoji_map.get(status, '📝')
            
            mensagem += f"\n{emoji} *{status}*\n"
            mensagem += f"🕒 {evento.get('data', 'N/A')}\n"
            mensagem += f"📍 {evento.get('localizacao', 'N/A')}\n"

        return mensagem

    # MÉTODO OPCIONAL: Se precisa de lógica customizada
    def buscar_pedido_especifico(self, cpf: str, numero_fiscal: str) -> dict:
        """
        Sobrescreve o método herdado se precisar de lógica diferente.
        
        Por padrão, o método da classe base já funciona!
        Só sobrescreva se sua API exigir algo específico.
        """
        # Exemplo: API que exige NF + CPF na mesma requisição
        try:
            payload = {
                "cpf": cpf,
                "nota_fiscal": numero_fiscal
            }
            
            response = requests.post(
                f"{self.url_base}/consulta-especifica",
                json=payload,
                timeout=30
            )
            
            dados = response.json()
            pedidos = self.extrair_pedidos(dados)
            
            return pedidos[0] if pedidos else None
            
        except Exception as e:
            logger.error(f"Erro na busca específica: {str(e)}")
            return None


# 🔥 IMPORTANTE: Criar instância global
nome_transportadora = NOMETransportadora()
```

---

### **PASSO 2:** Registrar em `api/__init__.py`

Abra o arquivo `api/__init__.py` e adicione sua transportadora:

```python
"""
Módulo de APIs de transportadoras.
Gerencia integração com múltiplas transportadoras para rastreamento de pedidos.
"""
from api.base_transportadora import BaseTransportadora
from api.api_dialogo import DialogoTransportadora, dialogo

# 🆕 ADICIONE AQUI: Importar sua nova transportadora
from api.api_NOME import NOMETransportadora, nome_transportadora

# ✅ Registro de transportadoras disponíveis
TRANSPORTADORAS = {
    'dialogo': dialogo,
    'nome': nome_transportadora,  # 🆕 ADICIONE AQUI
    # Adicione outras:
    # 'jadlog': jadlog,
    # 'correios': correios,
}

# ... resto do arquivo permanece igual
```

**✅ Pronto!** Sua transportadora está registrada!

---

## 🎨 Casos de Uso Avançados

### **CASO 1:** Transportadora que usa CÓDIGO DE RASTREIO (não CPF)

```python
class CorreiosTransportadora(BaseTransportadora):
    
    def consultar_por_codigo(self, codigo_rastreio: str) -> dict:
        """Usa código de rastreio em vez de CPF"""
        url = f"https://api.correios.com.br/rastro/{codigo_rastreio}"
        response = requests.get(url, timeout=30)
        return response.json()
    
    def buscar_pedido_especifico(self, codigo_rastreio: str, numero_fiscal: str = None) -> dict:
        """
        Sobrescreve método base - não precisa de NF, só do código
        """
        dados = self.consultar_por_codigo(codigo_rastreio)
        pedidos = self.extrair_pedidos(dados)
        return pedidos[0] if pedidos else None

# Na hora de usar:
# rastrear_pedido(cpf="AA123456789BR", numero_fiscal="", transportadora='correios')
```

---

### **CASO 2:** API que exige CPF + NF juntos

```python
class AzulCargoTransportadora(BaseTransportadora):
    
    def consultar_por_cpf_e_nf(self, cpf: str, numero_fiscal: str) -> dict:
        """API exige CPF E NF na mesma requisição"""
        payload = {
            "cpf": cpf,
            "nota_fiscal": numero_fiscal
        }
        response = requests.post(self.url_base, json=payload)
        return response.json()
    
    def buscar_pedido_especifico(self, cpf: str, numero_fiscal: str) -> dict:
        """Já consulta direto com CPF + NF"""
        dados = self.consultar_por_cpf_e_nf(cpf, numero_fiscal)
        pedidos = self.extrair_pedidos(dados)
        return pedidos[0] if pedidos else None
```

---

### **CASO 3:** API com autenticação complexa

```python
class JadlogTransportadora(BaseTransportadora):
    
    def __init__(self):
        super().__init__("Jadlog")
        self.token = None
        self.token_expira_em = None
    
    def obter_token(self):
        """Autentica e obtém token"""
        if self.token and self.token_expira_em > datetime.now():
            return self.token
        
        response = requests.post(
            "https://api.jadlog.com/auth",
            json={"username": "xxx", "password": "yyy"}
        )
        
        dados = response.json()
        self.token = dados['access_token']
        self.token_expira_em = datetime.now() + timedelta(hours=1)
        
        return self.token
    
    def consultar_por_cpf(self, cpf: str) -> dict:
        token = self.obter_token()
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"https://api.jadlog.com/rastreamento?cpf={cpf}",
            headers=headers
        )
        
        return response.json()
```

---

## 🧪 Como Testar Sua Transportadora

Crie o arquivo `test_minha_transportadora.py`:

```python
"""
Teste para nova transportadora.
"""
from api import rastrear_pedido

# Teste com dados reais
resultado = rastrear_pedido(
    cpf="00000000000",           # ← Seu CPF de teste
    numero_fiscal="123456",      # ← Sua NF de teste
    transportadora='nome'        # ← Nome registrado em TRANSPORTADORAS
)

print(resultado)
```

Execute:
```bash
python test_minha_transportadora.py
```

---

## 📊 Checklist de Implementação

- [ ] ✅ Criar arquivo `api/api_NOME.py`
- [ ] ✅ Herdar de `BaseTransportadora`
- [ ] ✅ Implementar `consultar_por_cpf()` (ou método equivalente)
- [ ] ✅ Implementar `extrair_pedidos()`
- [ ] ✅ Implementar `formatar_rastreamento()`
- [ ] ✅ Criar instância global no final do arquivo
- [ ] ✅ Adicionar import em `api/__init__.py`
- [ ] ✅ Registrar em `TRANSPORTADORAS`
- [ ] ✅ Criar teste básico
- [ ] ✅ Testar com dados reais
- [ ] ✅ Atualizar documentação (se necessário)

---

## 🎯 Exemplo Completo - Jadlog (JSON)

```python
"""
API de rastreamento para Jadlog.
"""
import re
import logging
import requests
from api.base_transportadora import BaseTransportadora

logger = logging.getLogger(__name__)


class JadlogTransportadora(BaseTransportadora):
    """Implementação para Jadlog"""

    def __init__(self):
        super().__init__(nome="Jadlog")
        self.url_base = "https://www.jadlog.com.br/sitejadlog/tracking/json"

    def consultar_por_cpf(self, cpf: str) -> dict:
        """
        Consulta pedidos usando CPF do destinatário.
        A API Jadlog retorna JSON.
        """
        cpf_limpo = re.sub(r'\D', '', cpf)
        
        try:
            logger.info(f"🔍 Consultando Jadlog com CPF: {cpf_limpo}")
            
            params = {
                "cte": cpf_limpo,
                "tipo": "D"  # D = Destinatário
            }
            
            response = requests.get(
                self.url_base,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            dados = response.json()
            
            logger.info("✅ Dados da Jadlog obtidos com sucesso")
            return dados
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar Jadlog: {str(e)}")
            return {}

    def extrair_pedidos(self, dados_resposta: dict) -> list:
        """
        Extrai lista de pedidos da resposta JSON da Jadlog.
        """
        pedidos = []
        
        try:
            # A estrutura JSON da Jadlog pode variar
            # Ajuste conforme a resposta real
            for item in dados_resposta.get('tracking', []):
                pedido = {
                    'numero_fiscal': item.get('nf'),
                    'numero_pedido': item.get('shipmentId'),
                    'destinatario': item.get('recipient', {}).get('name'),
                    'eventos': []
                }
                
                for evento in item.get('events', []):
                    pedido['eventos'].append({
                        'data': evento.get('date'),
                        'status': evento.get('status'),
                        'localizacao': evento.get('unit')
                    })
                
                if pedido['numero_fiscal']:
                    pedidos.append(pedido)
            
            logger.info(f"📦 Total de pedidos extraídos: {len(pedidos)}")
            return pedidos
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair pedidos: {str(e)}")
            return []

    def formatar_rastreamento(self, pedido: dict) -> str:
        """
        Formata rastreamento para WhatsApp.
        """
        if not pedido:
            return "❌ Pedido não encontrado"

        mensagem = f"📦 *RASTREAMENTO - JADLOG*\n\n"
        
        if pedido.get('destinatario'):
            mensagem += f"👤 *Destinatário:* {pedido['destinatario']}\n"
        
        mensagem += f"🧾 *Nota Fiscal:* {pedido.get('numero_fiscal', 'N/A')}\n"
        mensagem += f"🔢 *Código:* {pedido.get('numero_pedido', 'N/A')}\n"

        eventos = pedido.get('eventos', [])
        
        if not eventos:
            mensagem += "\n⚠️ Sem eventos de rastreamento."
            return mensagem

        mensagem += "\n📍 *HISTÓRICO:*\n"

        for evento in eventos:
            mensagem += f"\n📝 *{evento.get('status', 'N/A')}*\n"
            mensagem += f"🕒 {evento.get('data', 'N/A')}\n"
            mensagem += f"📍 {evento.get('localizacao', 'N/A')}\n"

        return mensagem


# Instância global
jadlog = JadlogTransportadora()
```

**Registrar em `api/__init__.py`:**

```python
from api.api_jadlog import JadlogTransportadora, jadlog

TRANSPORTADORAS = {
    'dialogo': dialogo,
    'jadlog': jadlog,  # 🆕
}
```

---

## ❓ FAQ

**Q: E se minha transportadora não usa CPF?**  
A: Renomeie o método! Ex: `consultar_por_codigo_rastreio()` e sobrescreva `buscar_pedido_especifico()`.

**Q: Posso usar múltiplos parâmetros?**  
A: Sim! Crie um método como `consultar_por_cpf_e_nf(cpf, nf)` e ajuste a lógica.

**Q: E se a API retornar XML?**  
A: Use `xml.etree.ElementTree` ou `BeautifulSoup` para parsear.

**Q: Preciso modificar `base_transportadora.py`?**  
A: **Não!** A classe base é genérica. Só sobrescreva os métodos necessários.

**Q: Como adiciono autenticação?**  
A: Adicione no `__init__()` ou crie método `obter_token()`. Veja exemplo Jadlog acima.

---

## 🎉 Conclusão

A estrutura está pronta para **qualquer tipo de API**:
- ✅ JSON, XML, HTML
- ✅ CPF, código de rastreio, ou ambos
- ✅ Autenticação simples ou complexa
- ✅ Respostas paginadas ou únicas

**Basta implementar os 3 métodos principais e registrar em `TRANSPORTADORAS`!**

---

📝 **Documentação criada em:** 27/10/2024  
🔄 **Última atualização:** 27/10/2024
