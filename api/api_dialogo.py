import requests
from bs4 import BeautifulSoup
import re

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
    "cnpjdest": "00449498042"
}

response = requests.post(url_inicial, headers=headers, data=payload)
response.encoding = "iso-8859-1"

soup = BeautifulSoup(response.text, "html.parser")
onclick_regex = re.compile(r"opx\('/2/ssw_SSWDetalhado\?id=([^&]+)&md=([^']+)'\)")

match = onclick_regex.search(response.text)
if not match:
    print("Nenhum link de detalhes encontrado.")
    exit()

id_param, md_param = match.groups()

url_detalhado = f"https://ssw.inf.br/2/ssw_SSWDetalhado?id={id_param}&md={md_param}"

headers_detalhado = {
    "User-Agent": "Mozilla/5.0",
    "Referer": url_inicial,
}

resp_detalhado = requests.get(url_detalhado, headers=headers_detalhado)
resp_detalhado.encoding = "iso-8859-1"

soup_detalhado = BeautifulSoup(resp_detalhado.text, "html.parser")

conteudo = soup_detalhado.get_text(separator="\n", strip=True)

linhas = [linha.strip() for linha in conteudo.split("\n") if linha.strip()]

print("\nInformações detalhadas do rastreio:\n")
for linha in linhas:
    print(linha)