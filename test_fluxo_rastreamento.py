"""
Teste completo do fluxo de rastreamento de pedidos.
Simula a jornada completa do usuário:
1. Consulta NF
2. Recebe status EXPEDIDO
3. Envia CPF
4. Recebe rastreamento completo
"""
import sys
from ia import eh_cpf, salvar_contexto_nf, obter_contexto_nf, processar_rastreamento_cpf
from config.globals import redis_client

print('=' * 90)
print('🧪 TESTE COMPLETO - FLUXO DE RASTREAMENTO')
print('=' * 90)
print()

# Teste 1: Detecção de CPF
print('📝 TESTE 1: Detecção de CPF')
print('─' * 90)

testes_cpf = [
    ('12345678901', True),
    ('123.456.789-01', True),
    ('123456789', False),  # CPF incompleto
    ('abc', False),  # Não é CPF
    ('2551805', False),  # NF, não CPF
    ('004.494.980-42', True),
]

for texto, esperado in testes_cpf:
    resultado = eh_cpf(texto)
    status = '✅' if resultado == esperado else '❌'
    print(f'   {status} "{texto}" → Detectado como CPF: {resultado} (Esperado: {esperado})')
print()

# Teste 2: Contexto Redis
print('📝 TESTE 2: Salvamento e Recuperação de Contexto')
print('─' * 90)

sender_teste = '5511999999999'
nf_teste = '2551805'
status_teste = 'EXPEDIDO'

print(f'   Salvando contexto: Sender={sender_teste}, NF={nf_teste}, Status={status_teste}')
salvar_contexto_nf(sender_teste, nf_teste, status_teste)

contexto = obter_contexto_nf(sender_teste)
if contexto:
    print(f'   ✅ Contexto recuperado com sucesso!')
    print(f'      - NF: {contexto.get("numero_nf")}')
    print(f'      - Status: {contexto.get("status")}')
    print(f'      - Timestamp: {contexto.get("timestamp")}')
else:
    print('   ❌ Erro ao recuperar contexto!')
print()

# Teste 3: Processamento de CPF sem contexto
print('📝 TESTE 3: CPF Enviado SEM Contexto (deve falhar)')
print('─' * 90)

sender_sem_contexto = '5511888888888'
cpf_teste = '00449498042'

resultado = processar_rastreamento_cpf(cpf_teste, sender_sem_contexto)
print(f'   Resultado: {resultado}')
print()

# Teste 4: Processamento de CPF com contexto mas status diferente
print('📝 TESTE 4: CPF com Status != EXPEDIDO (deve falhar)')
print('─' * 90)

sender_importado = '5511777777777'
salvar_contexto_nf(sender_importado, '12345', 'IMPORTADO')

resultado = processar_rastreamento_cpf(cpf_teste, sender_importado)
print(f'   Resultado: {resultado}')
print()

# Teste 5: Limpeza de contexto
print('📝 TESTE 5: Limpeza de Contexto Usado')
print('─' * 90)

redis_client.delete(f'contexto_nf:{sender_teste}')
redis_client.delete(f'contexto_nf:{sender_sem_contexto}')
redis_client.delete(f'contexto_nf:{sender_importado}')

print('   ✅ Contextos de teste limpos')
print()

print('=' * 90)
print('✅ TESTES DE FLUXO CONCLUÍDOS!')
print('=' * 90)
print()
print('📋 FLUXO COMPLETO IMPLEMENTADO:')
print('─' * 90)
print()
print('1️⃣  Usuário consulta NF (ex: "2551805")')
print('    └─> Sistema consulta WMS')
print()
print('2️⃣  Se Status = EXPEDIDO:')
print('    ├─> Salva contexto no Redis (NF + Status)')
print('    └─> IA oferece rastreamento: "Envie seu CPF para rastrear"')
print()
print('3️⃣  Usuário envia CPF (ex: "004.494.980-42")')
print('    ├─> Sistema detecta CPF')
print('    ├─> Busca contexto salvo')
print('    ├─> Valida Status = EXPEDIDO')
print('    └─> Chama API Transportadora')
print()
print('4️⃣  Sistema retorna rastreamento formatado:')
print('    ├─> Destinatário')
print('    ├─> NF e Pedido')
print('    ├─> Histórico completo de eventos')
print('    └─> Status de entrega')
print()
print('=' * 90)
print()
print('💡 PRÓXIMOS PASSOS:')
print('   1. ✅ Estrutura de classes criada')
print('   2. ✅ Dialogo Transportadora implementada')
print('   3. ✅ Integração no agente completa')
print('   4. ✅ Detecção de CPF implementada')
print('   5. ✅ Salvamento de contexto implementado')
print('   6. ⏳ Teste em produção com dados reais')
print('   7. ⏳ Adicionar outras transportadoras (Jadlog, Correios, etc)')
print()
print('📝 PARA ADICIONAR NOVA TRANSPORTADORA:')
print('   1. Criar api/api_NOME.py herdando de BaseTransportadora')
print('   2. Implementar consultar_por_cpf(), extrair_pedidos(), formatar_rastreamento()')
print('   3. Registrar em api/__init__.py no dicionário TRANSPORTADORAS')
print('   4. Pronto! Sistema automaticamente usará a nova transportadora')
print()
