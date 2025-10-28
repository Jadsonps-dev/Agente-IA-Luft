from playwright.sync_api import sync_playwright
import time

codigo_rastreio = "6347926569109"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto("https://cademinhaentrega.com.br/magalog", wait_until="networkidle")

    time.sleep(1)
    campo = page.wait_for_selector('input[type="text"]', timeout=10000)
    campo.click()
    campo.fill(codigo_rastreio)
    time.sleep(1)
    campo.press("Enter")

    xpath_botao = '/html/body/app-root/ion-app/ion-router-outlet/app-tracking/ion-content/ion-row/ion-col[2]/ion-card/ion-accordion-group/ion-accordion/ion-item/ion-col[1]/ion-text/h1'
    page.wait_for_selector(f'xpath={xpath_botao}', timeout=20000)
    page.click(f'xpath={xpath_botao}')

    time.sleep(1)
    page.wait_for_selector("ion-list.md.list-md.hydrated", timeout=20000)

    itens = page.locator("ion-list.md.list-md.hydrated ion-item")

    print("\n📦 Detalhes do rastreio:\n")
    for i in range(itens.count()):
        print(itens.nth(i).inner_text())

    browser.close()
