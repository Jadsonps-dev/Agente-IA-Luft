import requests

url = "https://endpoint.simexpress.com.br/logan/consumidor/index.php"

payload = {
    "documento": "34101183813",
    "primeironome": "lavinia", 
    "cep": "13325041", 
    "login": ""
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
              "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://endpoint.simexpress.com.br",
    "Referer": "https://endpoint.simexpress.com.br/logan/consumidor/index.php",
    "Connection": "keep-alive",
}

response = requests.post(url, data=payload, headers=headers)

print("Status code:", response.status_code)
print("Resposta (texto):")
print(response.text)