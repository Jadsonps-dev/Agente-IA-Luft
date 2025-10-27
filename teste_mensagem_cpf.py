"""
Teste para verificar se a mensagem de CPF é adicionada
automaticamente quando o status é EXPEDIDO
"""

# Simula o contexto que seria criado quando status = EXPEDIDO
contexto_expedido = """
INFORMAÇÕES DA NOTA FISCAL 2551805:
- Status: EXPEDIDO
- Transportadora: DIÁLOGO LOGÍSTICA
- Código de Rastreio: 6337305149589

⚠️ AÇÃO OBRIGATÓRIA - O pedido está EXPEDIDO:
Você DEVE incluir na sua resposta a seguinte mensagem EXATAMENTE como está escrito:

"📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."

Esta mensagem deve aparecer AO FINAL da sua resposta, após as informações da nota fiscal.
NÃO OMITA esta mensagem. É OBRIGATÓRIO incluí-la.
"""

# Simula resposta da IA SEM a mensagem de CPF
resposta_ia_sem_cpf = """Aqui estão as informações da sua nota fiscal 2551805:

📦 Status: EXPEDIDO

🚚 Transportadora: DIÁLOGO LOGÍSTICA INTELIGENTE LTDA - EPP

✅ Código de Rastreio: 6337305149589

Se precisar de mais alguma coisa, estou à disposição!"""

# Simula resposta da IA COM a mensagem de CPF
resposta_ia_com_cpf = """Aqui estão as informações da sua nota fiscal 2551805:

📦 Status: EXPEDIDO

🚚 Transportadora: DIÁLOGO LOGÍSTICA INTELIGENTE LTDA - EPP

✅ Código de Rastreio: 6337305149589

📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."""

print('=' * 90)
print('🧪 TESTE DE MENSAGEM DE CPF AUTOMÁTICA')
print('=' * 90)
print()

print('📋 CONTEXTO GERADO (quando status = EXPEDIDO):')
print('─' * 90)
print(contexto_expedido)
print()

print('━' * 90)
print('TESTE 1: IA não incluiu a mensagem de CPF')
print('━' * 90)
print()
print('Resposta Original da IA:')
print(resposta_ia_sem_cpf)
print()

# Simula a lógica de fallback
content = resposta_ia_sem_cpf.strip()
if "AÇÃO OBRIGATÓRIA" in contexto_expedido and "📍 Deseja rastrear" not in content:
    content += "\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."
    print('✅ FALLBACK ATIVADO! Mensagem adicionada automaticamente.')
else:
    print('⚠️ Fallback não necessário.')

print()
print('Resposta Final Enviada ao WhatsApp:')
print('─' * 90)
print(content)
print()

print('━' * 90)
print('TESTE 2: IA incluiu a mensagem de CPF')
print('━' * 90)
print()
print('Resposta Original da IA:')
print(resposta_ia_com_cpf)
print()

# Simula a lógica de fallback
content2 = resposta_ia_com_cpf.strip()
if "AÇÃO OBRIGATÓRIA" in contexto_expedido and "📍 Deseja rastrear" not in content2:
    content2 += "\n\n📍 Deseja rastrear seu pedido em tempo real? Envie o CPF do destinatário."
    print('✅ FALLBACK ATIVADO! Mensagem adicionada automaticamente.')
else:
    print('✅ Mensagem já presente! Fallback não necessário.')

print()
print('Resposta Final Enviada ao WhatsApp:')
print('─' * 90)
print(content2)
print()

print('=' * 90)
print('✅ GARANTIA DUPLA IMPLEMENTADA!')
print('=' * 90)
print()
print('🎯 COMO FUNCIONA:')
print()
print('1. Quando NF tem status EXPEDIDO:')
print('   └─> Salva contexto no Redis')
print('   └─> Adiciona "AÇÃO OBRIGATÓRIA" ao contexto da IA')
print()
print('2. IA gera resposta:')
print('   └─> CASO 1: IA segue instrução e inclui mensagem ✅')
print('   └─> CASO 2: IA ignora instrução → Fallback adiciona mensagem ✅')
print()
print('3. Usuário sempre recebe a mensagem pedindo CPF!')
print()
print('4. Quando usuário envia CPF:')
print('   └─> Sistema detecta CPF (11 dígitos)')
print('   └─> Busca contexto no Redis')
print('   └─> Valida status EXPEDIDO')
print('   └─> Chama API transportadora')
print('   └─> Retorna rastreamento completo')
print()
print('=' * 90)
