
import requests
from bs4 import BeautifulSoup
import re

print('=' * 90)
print('🧪 DEBUG - HTML DA DIALOGO')
print('=' * 90)
print()

cpf = "00449498042"

url_inicial = "https://ssw.inf.br/2/ssw_resultSSW_dest"

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://dialogologistica.com.br",
    "Referer": "https://dialogologistica.com.br/",
}

payload = {
    "urlori": "https://dialogologistica.com.br/rastreie-seu-pedido",
    "sigla_emp": "DLG",
    "cnpjdest": cpf
}

print(f'📞 Fazendo requisição inicial com CPF: {cpf}')
response = requests.post(url_inicial, headers=headers, data=payload, timeout=30)
response.encoding = "iso-8859-1"

soup = BeautifulSoup(response.text, "html.parser")
onclick_regex = re.compile(r"opx\('/2/ssw_SSWDetalhado\?id=([^&]+)&md=([^']+)'\)")

match = onclick_regex.search(response.text)
if not match:
    print("❌ Nenhum link de detalhes encontrado")
    exit()

id_param, md_param = match.groups()
url_detalhado = f"https://ssw.inf.br/2/ssw_SSWDetalhado?id={id_param}&md={md_param}"

print(f'📄 Buscando detalhes em: {url_detalhado}')
print()

headers_detalhado = {
    "User-Agent": "Mozilla/5.0",
    "Referer": url_inicial,
}

resp_detalhado = requests.get(url_detalhado, headers=headers_detalhado, timeout=30)
resp_detalhado.encoding = "iso-8859-1"

print('📄 HTML COMPLETO:')
print('─' * 90)
print(resp_detalhado.text)
print('─' * 90)
print()

# Analisa estrutura
soup_detalhado = BeautifulSoup(resp_detalhado.text, "html.parser")

print('📊 ANÁLISE DA ESTRUTURA:')
print('─' * 90)

tabelas = soup_detalhado.find_all('table')
print(f'Total de tabelas: {len(tabelas)}')
print()

for idx, tabela in enumerate(tabelas):
    print(f'Tabela {idx + 1}:')
    linhas = tabela.find_all('tr')
    print(f'  - Total de linhas: {len(linhas)}')
    
    for i, linha in enumerate(linhas[:5]):  # Mostra só as 5 primeiras
        texto = linha.get_text(strip=True)
        print(f'  - Linha {i+1}: {texto[:100]}')
    
    if len(linhas) > 5:
        print(f'  ... (mais {len(linhas) - 5} linhas)')
    print()

# Busca por texto específico
print('🔍 BUSCANDO PADRÕES:')
print('─' * 90)

texto_completo = soup_detalhado.get_text()

if '2551805' in texto_completo:
    print('✅ NF 2551805 encontrada no HTML!')
else:
    print('❌ NF 2551805 NÃO encontrada no HTML')

if 'Fiscal' in texto_completo or 'fiscal' in texto_completo:
    print('✅ Palavra "Fiscal" encontrada')
else:
    print('❌ Palavra "Fiscal" NÃO encontrada')

print()
