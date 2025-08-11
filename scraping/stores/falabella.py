import logging
import re
from typing import List, Dict, Any, Optional

import pandas as pd
from playwright.async_api import async_playwright, Page, ElementHandle, Error

# --- Configuración Inicial ---
# Se configura un logger para registrar información y advertencias durante la ejecución.
# Esto es útil para depurar y monitorear el scraper en producción.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [FalabellaScraper] - %(message)s'
)

# --- Constantes ---
# URL base para construir las URLs absolutas de los productos si es necesario.
BASE_URL = "https://www.falabella.com.co"
# URL de búsqueda de celulares. El número de página se añadirá dinámicamente.
SEARCH_URL = "https://www.falabella.com.co/falabella-co/search?Ntt=celulares&page={}"
# Número de páginas a scrapear.
PAGES_TO_SCRAPE = 7


def _clean_price(price_str: Optional[str]) -> Optional[float]:
    """
    Limpia una cadena de texto que representa un precio para convertirla en un flotante.

    Ejemplo:
        '$ 1.999.900' -> 1999900.0

    Args:
        price_str: La cadena de texto del precio. Puede ser None si no se encuentra.

    Returns:
        El precio como un número flotante (float) o None si la entrada es None.
    """
    if price_str is None:
        return None
    # Usa una expresión regular para eliminar todo lo que no sea un dígito.
    # Esto elimina símbolos de moneda, puntos de mil, comas y espacios.
    numeric_string = re.sub(r'\D', '', price_str)
    if numeric_string:
        return float(numeric_string)
    return None


async def _extract_product_data(product_card: ElementHandle) -> Optional[Dict[str, Any]]:
    """
    Extrae la información de una única tarjeta de producto.

    Args:
        product_card: El objeto ElementHandle de Playwright que representa la tarjeta del producto.

    Returns:
        Un diccionario con los datos del producto o None si no se puede extraer la URL o el nombre.
    """
    # --- Extracción de la URL del Producto ---
    # Selector para la etiqueta <a> que contiene el enlace al producto.
    link_element = await product_card.query_selector('a[href]')
    if not link_element:
        logging.warning("No se encontró el enlace para una tarjeta de producto. Saltando.")
        return None
    
    product_url = await link_element.get_attribute('href')
    # Asegura que la URL sea absoluta.
    if product_url and not product_url.startswith('http'):
        product_url = BASE_URL + product_url

    # --- Extracción del Nombre del Producto (Selector Actualizado) ---
    # Se usa 'data-testid' que es más estable que las clases de CSS.
    name_element = await product_card.query_selector('b[data-testid="name"]')
    product_name = await name_element.text_content() if name_element else "Nombre no disponible"
    product_name = product_name.strip()

    # --- Extracción del Precio Actual (Oferta) ---
    # Este selector basado en 'data-testid' sigue siendo robusto.
    current_price_element = await product_card.query_selector('[data-testid="price-value"]')
    current_price_str = await current_price_element.text_content() if current_price_element else None
    
    # --- Extracción del Precio Normal (Tachado) (Selector Actualizado) ---
    # El precio normal no siempre está presente. Se usa 'data-testid' para mayor fiabilidad.
    normal_price_element = await product_card.query_selector('span[data-testid="price-original"]')
    normal_price_str = await normal_price_element.text_content() if normal_price_element else None

    # --- Ensamblaje del Diccionario de Datos ---
    product_data = {
        'product_name': product_name,
        'current_price': _clean_price(current_price_str),
        'normal_price': _clean_price(normal_price_str) or pd.NA, # Usamos pandas.NA para consistencia
        'product_url': product_url,
    }

    return product_data


async def scrape_falabella() -> List[Dict[str, Any]]:
    """
    Función principal para realizar el web scraping en Falabella Colombia.

    Navega a través de las páginas de resultados de búsqueda para "celulares",
    extrae la información de cada producto y la devuelve como una lista de diccionarios.

    Returns:
        Una lista de diccionarios, donde cada diccionario representa un producto.
    """
    logging.info("Iniciando el scraper para Falabella...")
    products_data: List[Dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for page_num in range(1, PAGES_TO_SCRAPE + 1):
            url = SEARCH_URL.format(page_num)
            logging.info(f"Scrapeando página {page_num}: {url}")

            try:
                # --- LÓGICA DE CARGA MEJORADA ---
                # Se aumenta el timeout a 60s y se espera a que la red esté inactiva ('networkidle'),
                # lo que es más fiable para sitios que cargan contenido dinámicamente.
                await page.goto(url, wait_until='networkidle', timeout=60000)

                # Espera explícita para el contenedor principal de productos.
                # Si esto falla, significa que la página no cargó la sección de resultados.
                await page.wait_for_selector('#testId-searchResults-products', timeout=60000)
                
                # Selector de tarjetas de producto actualizado para ser más robusto.
                product_cards = await page.query_selector_all('div[data-testid="pod-item"]')
                logging.info(f"Se encontraron {len(product_cards)} productos en la página {page_num}.")

                if not product_cards:
                    logging.warning(f"No se encontraron tarjetas de producto en la página {page_num}. El sitio puede estar bloqueando el contenido o no hay productos.")
                    continue

                for card in product_cards:
                    try:
                        product_info = await _extract_product_data(card)
                        if product_info:
                            products_data.append(product_info)
                    except Error as e:
                        logging.warning(f"Error de Playwright al procesar un producto en la página {page_num}. Error: {e}")
                    except Exception as e:
                        logging.warning(f"Error inesperado al procesar un producto en la página {page_num}. Error: {e}")

            except Error as e:
                # Este error ahora es más significativo. Si ocurre, es probable que sea un bloqueo de red o un CAPTCHA.
                logging.error(f"No se pudo cargar o procesar la página {page_num} después de 60s. Error: {e}")
                continue
        
        await browser.close()
    
    logging.info(f"Scraping de Falabella finalizado. Se extrajeron {len(products_data)} productos en total.")
    return products_data

# Ejemplo de cómo se podría ejecutar esta función (para pruebas)
# El orquestador `run_scraping.py` llamará directamente a `scrape_falabella`.
if __name__ == '__main__':
    import asyncio
    
    async def main():
        results = await scrape_falabella()
        if results:
            # Convertir a DataFrame de pandas para una mejor visualización
            df = pd.DataFrame(results)
            pd.set_option('display.max_rows', None)
            print("Resultados del scraping:")
            print(df)
            # Guardar en un archivo CSV
            df.to_csv("falabella_celulares.csv", index=False, encoding='utf-8-sig')
            print("\nResultados guardados en falabella_celulares.csv")
        else:
            print("No se extrajo ningún producto.")

    asyncio.run(main())