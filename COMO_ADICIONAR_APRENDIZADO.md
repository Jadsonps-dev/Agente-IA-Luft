# 📚 Como Adicionar Mais Aprendizado ao Sistema

## 🎯 Objetivo
Este guia mostra como adicionar novos exemplos de aprendizado sem mexer no código Python.

---

## 📝 Para Consultas de Nota Fiscal

**Arquivo:** `docs/query_nf_learning.json`

### Adicionar novo exemplo na seção `exemplos_aprendizado_completos`:

```json
{
  "pergunta_usuario": "Sua pergunta aqui",
  "analise_ia": {
    "tipo_consulta": "nota_fiscal",
    "numero_nf": "NUMERO_AQUI",
    "explicacao_decisao": "Por que essa é uma consulta de NF"
  },
  "acao": "Chamar API query_nf com numero_nf=NUMERO_AQUI"
}
```

### Exemplo prático:
```json
{
  "pergunta_usuario": "Onde está meu pedido 55555?",
  "analise_ia": {
    "tipo_consulta": "nota_fiscal",
    "numero_nf": "55555",
    "explicacao_decisao": "Usuário quer rastrear um pedido específico"
  },
  "acao": "Chamar API query_nf com numero_nf=55555"
}
```

---

## 📊 Para Consultas Operacionais

**Arquivo:** `docs/query_consulta_op_learning.json`

### Adicionar novo exemplo na seção `exemplos_aprendizado_completos`:

```json
{
  "id": 7,
  "pergunta_usuario": "Sua pergunta aqui",
  "analise_passo_a_passo": {
    "passo_1": "Identificar tipo: pedidos ou peças",
    "passo_2": "Identificar status",
    "passo_3": "Escolher coluna data (PESADO_EM ou IMPORTADO_EM)",
    "passo_4": "Identificar período",
    "passo_5": "Identificar cliente (B2B, B2C ou todos)"
  },
  "resultado_analise": {
    "tipo_consulta": "pedidos ou pecas",
    "status_filtro": ["STATUS_AQUI"],
    "coluna_data": "PESADO_EM ou IMPORTADO_EM",
    "periodo": "hoje, ontem, semana, mes",
    "tipo_cliente": "B2C, B2B ou null"
  }
}
```

### Exemplo prático:
```json
{
  "id": 7,
  "pergunta_usuario": "Quantas peças B2B foram faturadas essa semana?",
  "analise_passo_a_passo": {
    "passo_1": "Identificar tipo: 'peças' → SUM(QTDE)",
    "passo_2": "Identificar status: 'faturadas' → STATUS='FATURADO'",
    "passo_3": "Escolher coluna data: STATUS=FATURADO (não é EXPEDIDO) → IMPORTADO_EM",
    "passo_4": "Identificar cliente: 'B2B' → CLASSIFICACAO_CODIGO LIKE 'INSIDER_B2B%'",
    "passo_5": "Identificar período: 'essa semana' → últimos 7 dias"
  },
  "resultado_analise": {
    "tipo_consulta": "pecas",
    "status_filtro": ["FATURADO"],
    "coluna_data": "IMPORTADO_EM",
    "periodo": "semana",
    "tipo_cliente": "B2B"
  }
}
```

---

## 🔑 Regras Importantes

### ✅ Para escolher a coluna de data:

| Status | Coluna a usar |
|--------|---------------|
| EXPEDIDO | **PESADO_EM** |
| IMPORTADO | IMPORTADO_EM |
| FATURADO | IMPORTADO_EM |
| SEPARACAO | IMPORTADO_EM |
| CANCELADO | IMPORTADO_EM |

### ✅ Para tipo de consulta:

| Pergunta fala de... | Tipo |
|---------------------|------|
| Pedidos, Notas, NFs | pedidos → COUNT(NOTA_FISCAL) |
| Peças, Produtos, Itens | pecas → SUM(QTDE) |

### ✅ Para cliente B2B/B2C:

| Classificação começa com... | Tipo |
|-----------------------------|------|
| INSIDER_B2C* | B2C |
| INSIDER_B2B* | B2B |

---

## 🚀 Depois de adicionar exemplos:

**Não precisa fazer nada!** O sistema carrega automaticamente os JSONs quando roda.

Para testar:
```bash
python3 -c "from ia import analisar_pergunta_com_ia; print(analisar_pergunta_com_ia('sua pergunta aqui'))"
```

---

## 📌 Dicas

1. **Adicione casos reais** que os usuários perguntam
2. **Documente edge cases** que você encontrar
3. **Seja específico** na explicação de decisão
4. **Mantenha consistência** com exemplos existentes
5. **Teste** suas mudanças depois de adicionar

---

## 🎓 Quanto mais exemplos, melhor o agente aprende!

O agente usa todos esses exemplos para entender padrões e tomar decisões melhores.
Não tenha medo de adicionar muitos exemplos - quanto mais, melhor!
