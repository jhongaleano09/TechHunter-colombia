# scraping/stores/alkosto.py

import asyncio
import logging
from playwright.async_api import async_playwright
from typing import List, Dict, Any, Optional
import re

# Configuración del logging para mostrar mensajes informativos
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constantes ---
BASE_URL = "https://www.alkosto.com"
MAX_PAGES = 7  # Número de páginas a scrapear

# --- Selectores CSS (centralizados para fácil mantenimiento) ---
# Se usan selectores que buscan atributos específicos para mayor robustez.
PRODUCT_CARD_SELECTOR = "li.product__item"
PRODUCT_NAME_SELECTOR = "h3.product__item__top__title"
# <<< CORREGIDO: Se define el selector para el enlace del producto.
# Este selector apunta a la etiqueta <a> que envuelve la imagen y el título.
PRODUCT_LINK_SELECTOR = "a.product__item__top__link"
# <<< CORREGIDO: Selector específico para el precio actual (con descuento).
# Apunta directamente al <span> que contiene el precio final.
CURRENT_PRICE_SELECTOR = "span.price"
# <<< CORREGIDO: Selector para el precio normal (tachado), como indicaste.
NORMAL_PRICE_SELECTOR = "p.product__price--discounts__old"


def clean_price(price_text: Optional[str]) -> Optional[float]:
    """
    Limpia un texto de precio para convertirlo en un número flotante.
    Ejemplo: '$1.299.900' -> 1299900.0
    """
    if not price_text:
        return None
    try:
        # Remover el símbolo de moneda, los puntos de miles y espacios.
        cleaned_price = re.sub(r'[$\s.]', '', price_text)
        return float(cleaned_price)
    except (ValueError, TypeError):
        # En caso de que el formato no sea el esperado, retorna None.
        return None

async def scrape_alkosto() -> List[Dict[str, Any]]:
    """
    Función principal para realizar el web scraping de celulares en Alkosto.
    Itera a través de las páginas, extrae la información de cada producto
    y la devuelve como una lista de diccionarios.
    """
    logging.info("Iniciando scraping en Alkosto para celulares.")
    products_data = []

    async with async_playwright() as p:
        # Se recomienda usar Firefox o WebKit para evitar bloqueos comunes de sitios a bots
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for page_num in range(MAX_PAGES):
            # La paginación en Alkosto empieza en 0
            url = f"{BASE_URL}/search?text=celulares&page={page_num}&sort=relevance"
            logging.info(f"Scrapeando página: {page_num + 1}/{MAX_PAGES} -> {url}")

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # Esperar a que el contenedor de productos esté visible
                await page.wait_for_selector(PRODUCT_CARD_SELECTOR, timeout=30000)
            except Exception as e:
                logging.error(f"No se pudo cargar la página {page_num + 1} o no se encontraron productos. Error: {e}")
                continue # Salta a la siguiente página

            # Obtener todos los contenedores de productos en la página actual
            product_cards = await page.query_selector_all(PRODUCT_CARD_SELECTOR)

            for card in product_cards:
                product = {}
                try:
                    # 1. Extraer nombre del producto
                    product_name_element = await card.query_selector(PRODUCT_NAME_SELECTOR)
                    product['product_name'] = await product_name_element.inner_text() if product_name_element else "No disponible"

                    # 2. Extraer precio actual (de oferta)
                    current_price_element = await card.query_selector(CURRENT_PRICE_SELECTOR)
                    current_price_text = await current_price_element.inner_text() if current_price_element else None
                    product['current_price'] = clean_price(current_price_text)

                    # 3. Extraer precio normal (tachado) - puede no existir
                    normal_price_element = await card.query_selector(NORMAL_PRICE_SELECTOR)
                    normal_price_text = await normal_price_element.inner_text() if normal_price_element else None
                    product['normal_price'] = clean_price(normal_price_text)

                    # 4. Extraer URL del producto
                    link_element = await card.query_selector(PRODUCT_LINK_SELECTOR)
                    relative_url = await link_element.get_attribute('href') if link_element else ""
                    product['product_url'] = f"{BASE_URL}{relative_url}" if relative_url.startswith('/') else relative_url

                    # <<< CORREGIDO: Se eliminó la extracción de 'image_url' como solicitaste.

                    products_data.append(product)

                except Exception as e:
                    logging.warning(f"Error al procesar un producto. Saltando al siguiente. Error: {e}")
                    continue # Continúa con el siguiente producto en caso de error

        await browser.close()
        logging.info(f"Scraping de Alkosto finalizado. Total de productos extraídos: {len(products_data)}")
        return products_data

if __name__ == '__main__':
    # Bloque para permitir pruebas directas del scraper
    async def main_test():
        data = await scrape_alkosto()
        if data:
            print(f"Se extrajeron {len(data)} productos. Mostrando los primeros 3:")
            for item in data[:3]:
                print(item)

    asyncio.run(main_test())