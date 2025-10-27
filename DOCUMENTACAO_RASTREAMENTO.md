# 📦 Sistema de Rastreamento de Pedidos - Documentação

## 🎯 Visão Geral

Sistema completo de rastreamento de pedidos integrado ao assistente WhatsApp da Luft Solutions. Permite que clientes rastreiem pedidos expedidos usando apenas o CPF do destinatário.

## 🏗️ Arquitetura

### Estrutura de Arquivos

```
api/
├── __init__.py              # Gerenciador de transportadoras
├── base_transportadora.py   # Classe abstrata base
└── api_dialogo.py          # Implementação Dialogo Logística

ia.py                        # Lógica de integração com agente
routes/webhook.py            # Webhook WhatsApp (não alterado)
```

### Fluxo de Dados

```
┌──────────────┐
│   Usuário    │
│  WhatsApp    │
└──────┬───────┘
       │
       │ 1. Consulta NF: "2551805"
       ▼
┌──────────────────────┐
│  Agente IA (ia.py)   │
│  - Consulta WMS      │
│  - Detecta EXPEDIDO  │
│  - Salva contexto    │
└──────┬───────────────┘
       │
       │ 2. Status: EXPEDIDO
       │    Resposta: "Envie seu CPF para rastrear"
       │    Redis: contexto_nf:{sender} = {NF, Status}
       ▼
┌──────────────┐
│   Usuário    │
│ Envia CPF    │
└──────┬───────┘
       │
       │ 3. CPF: "004.494.980-42"
       ▼
┌──────────────────────┐
│  Agente IA (ia.py)   │
│  - Detecta CPF       │
│  - Busca contexto    │
│  - Valida EXPEDIDO   │
└──────┬───────────────┘
       │
       │ 4. Rastreamento
       ▼
┌──────────────────────────┐
│  API Transportadora      │
│  (api/api_dialogo.py)    │
│  - consultar_por_cpf()   │
│  - extrair_pedidos()     │
│  - formatar()            │
└──────┬───────────────────┘
       │
       │ 5. Rastreamento formatado
       ▼
┌──────────────┐
│   Usuário    │
│  WhatsApp    │
└──────────────┘
```

## 🔧 Componentes Principais

### 1. BaseTransportadora (api/base_transportadora.py)

Classe abstrata que define a interface para todas as transportadoras.

**Métodos Abstratos (devem ser implementados):**
- `consultar_por_cpf(cpf: str)` → Dict - Consulta API da transportadora
- `extrair_pedidos(dados)` → List[Dict] - Extrai pedidos da resposta
- `formatar_rastreamento(pedido)` → str - Formata para WhatsApp

**Métodos Herdados (prontos para uso):**
- `buscar_pedido_especifico(cpf, numero_nf)` - Busca NF específica
- `limpar_cpf(cpf)` - Remove pontuação do CPF

### 2. DialogoTransportadora (api/api_dialogo.py)

Implementação para Dialogo Logística.

**Processo:**
1. Faz requisição POST com CPF para `ssw.inf.br`
2. Extrai ID da página de detalhes
3. Busca rastreamento completo
4. Parseia HTML com BeautifulSoup
5. Formata com emojis para WhatsApp

### 3. Funções do Agente IA (ia.py)

**Novas Funções:**

```python
eh_cpf(mensagem: str) -> bool
# Detecta se mensagem é um CPF (11 dígitos)

salvar_contexto_nf(sender, numero_nf, status)
# Salva contexto no Redis (expira em 10min)

obter_contexto_nf(sender) -> Dict
# Recupera contexto salvo

processar_rastreamento_cpf(cpf, sender) -> str
# Processa rastreamento completo
```

**Modificações em `perguntar_ia()`:**

1. **Prioridade 1:** Detecta CPF antes de qualquer outra análise
2. **Ao consultar NF:** Se status = EXPEDIDO:
   - Salva contexto no Redis
   - Instrui IA a oferecer rastreamento
3. **Retorna:** Mensagem formatada ou rastreamento

## 📋 Formato de Resposta

### Exemplo de Rastreamento

```
📦 *RASTREAMENTO - DIALOGO LOGÍSTICA*

👤 Destinatário: Julia ****
📄 Nota Fiscal: 2551805
🔢 Pedido: 6337305149589

📍 *HISTÓRICO DE RASTREAMENTO:*

📝 *DOCUMENTO DE TRANSPORTE EMITIDO*
   🕒 23/10/25 21:29
   📍 EXTREMA / MG
   ℹ️ CT-e autorizado com 1 volume e 2 Kg...

🚚 *SAIDA DE UNIDADE*
   🕒 24/10/25 04:11
   📍 JUNDIAI / SP

✅ *MERCADORIA ENTREGUE*
   🕒 25/10/25 11:02
   📍 CACHOEIRINHA / RS
   ℹ️ Nome do recebedor: JULIA LIMA VIEIRA...
```

## 🔐 Segurança e Privacidade

### Redis - Contexto Temporário

- **Key:** `contexto_nf:{sender}`
- **Dados:** `{numero_nf, status, timestamp}`
- **Expiração:** 600 segundos (10 minutos)
- **Limpeza:** Automática após uso

### Validações

1. ✅ CPF deve ter 11 dígitos
2. ✅ Contexto deve existir no Redis
3. ✅ Status deve ser EXPEDIDO
4. ✅ NF deve ser encontrada na transportadora

## 🚀 Como Adicionar Nova Transportadora

### Passo 1: Criar arquivo `api/api_NOME.py`

```python
from api.base_transportadora import BaseTransportadora

class NOMETransportadora(BaseTransportadora):
    
    def __init__(self):
        super().__init__("NOME")
        # configurações...
    
    def consultar_por_cpf(self, cpf: str):
        # implementar consulta
        pass
    
    def extrair_pedidos(self, dados):
        # implementar extração
        pass
    
    def formatar_rastreamento(self, pedido):
        # implementar formatação
        pass

# Instância global
nome_transp = NOMETransportadora()
```

### Passo 2: Registrar em `api/__init__.py`

```python
from api.api_nome import nome_transp

TRANSPORTADORAS = {
    'dialogo': dialogo,
    'nome': nome_transp,  # ← ADICIONAR AQUI
}
```

### Passo 3: Testar

```python
from api import rastrear_pedido

resultado = rastrear_pedido(
    cpf="12345678901",
    numero_fiscal="123456",
    transportadora='nome'  # ← usar nome registrado
)
```

## 🧪 Testes

### Teste de Estrutura

```bash
python3 test_transportadoras.py
```

### Teste de Fluxo

```bash
python3 test_rastreamento_simples.py
```

### Teste Manual (com dados reais)

```python
from api import rastrear_pedido

# Substitua pelos dados reais
resultado = rastrear_pedido(
    cpf="00449498042",
    numero_fiscal="2551805"
)
print(resultado)
```

## 📊 Métricas e Logs

### Logs Importantes

```
✅ CPF detectado: 00449498042
💾 Contexto NF salvo para 5511999999999: NF=2551805, Status=EXPEDIDO
📖 Contexto NF recuperado para 5511999999999
🔍 Rastreando NF 2551805 com CPF fornecido
🚚 Transportadora Dialogo inicializada
✅ Dados da Dialogo obtidos com sucesso
✅ Pedido extraído - NF: 2551805, Pedido: 6337305149589
```

### Erros Comuns

```
❌ Para rastrear seu pedido, primeiro consulte o número da nota fiscal
❌ O pedido XXX não está com status EXPEDIDO
❌ Pedido XXX não encontrado no rastreamento
❌ Erro ao buscar rastreamento
```

## 🎯 Casos de Uso

### Caso 1: Fluxo Normal

1. Usuário: "2551805"
2. Sistema: "Pedido EXPEDIDO via Dialogo. Para rastrear, envie seu CPF"
3. Usuário: "004.494.980-42"
4. Sistema: [Rastreamento completo formatado]

### Caso 2: CPF sem Contexto

1. Usuário: "123.456.789-01"
2. Sistema: "Para rastrear seu pedido, primeiro consulte o número da nota fiscal"

### Caso 3: Status não EXPEDIDO

1. Usuário: "12345" (consulta NF)
2. Sistema: "Status: IMPORTADO" (sem oferta de rastreamento)
3. Usuário: "123.456.789-01"
4. Sistema: "O pedido não está com status EXPEDIDO"

## 📝 Notas Técnicas

### Dependências Adicionadas

- `beautifulsoup4` - Parse HTML da API Dialogo
- `requests` - HTTP requests (já existente)

### Timeouts

- Requisições HTTP: 30 segundos
- Contexto Redis: 600 segundos (10 minutos)

### Encoding

- API Dialogo usa `iso-8859-1`
- WhatsApp usa UTF-8
- Conversão automática no código

## 🔄 Manutenção

### Atualizar URL da Transportadora

Editar `api/api_dialogo.py`:

```python
self.url_inicial = "https://nova-url.com"
```

### Adicionar Novo Emoji

Editar `formatar_rastreamento()` em `api/api_dialogo.py`:

```python
emoji_map = {
    'NOVA_SITUACAO': '🆕',
    # ...
}
```

### Ajustar Tempo de Contexto

Editar `ia.py`:

```python
redis_client.set(contexto_key, contexto, ex=600)  # ← Alterar aqui
```

## 🎉 Status Atual

- ✅ Estrutura de classes implementada
- ✅ Dialogo Transportadora funcionando
- ✅ Integração completa no agente IA
- ✅ Detecção de CPF
- ✅ Salvamento de contexto Redis
- ✅ Formatação com emojis
- ✅ Testes passando
- ⏳ Teste em produção pendente
- ⏳ Adicionar outras transportadoras

## 📞 Suporte

Para adicionar novas transportadoras ou modificar o fluxo, consultar:

- `api/base_transportadora.py` - Interface base
- `api/api_dialogo.py` - Exemplo de implementação
- `COMO_ADICIONAR_APRENDIZADO.md` - Guia de learning
