import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://rastreamento.correios.com.br/"
})

home_url = "https://rastreamento.correios.com.br/"
session.get(home_url)

captcha_url = "https://rastreamento.correios.com.br/core/securimage/securimage_show.php"
resp = session.get(captcha_url)
resp.raise_for_status()

with open("captcha.jpg", "wb") as f:
    f.write(resp.content)

print("Captcha salvo como captcha.jpg. Resolva manualmente e use o valor no request de rastreamento.")

captcha_value = input("Digite o captcha: ")

rast_url = "https://rastreamento.correios.com.br/app/resultado.php"
params = {
    "objeto": "AB569530491BR",
    "captcha": captcha_value,
    "mqs": "S"
}

resp_rast = session.get(rast_url, params=params)
resp_rast.raise_for_status()

print(resp_rast.text[:1000]) 