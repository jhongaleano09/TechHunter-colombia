import logging
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Error
import asyncio
import pandas as pd
from datetime import datetime
import os

# --- Configuración Inicial ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [FalabellaScraper] - %(message)s'
)

# --- Constantes Actualizadas ---
BASE_URL = "https://www.falabella.com.co"
SEARCH_URL_ALT = "https://www.falabella.com.co/falabella-co/search?Ntt=celulares&page={}"
PAGES_TO_SCRAPE = 3
DEBUG_DIR = os.path.join('scraping', 'debug')

def _clean_price(price_str: Optional[str]) -> Optional[float]:
    if price_str is None or not price_str.strip():
        return None
    # Remove all non-digit characters except for the comma and period for decimals, then replace comma with period
    numeric_string = re.sub(r'[^\d,.]', '', price_str).replace('.', '').replace(',', '.')
    try:
        return float(numeric_string)
    except ValueError:
        return None

async def _handle_notification(page: Page):
    try:
        close_button_selector = "button.dy-modal-close-button"
        close_button = page.locator(close_button_selector).first
        await close_button.wait_for(state="visible", timeout=5000)
        logging.info("Notificación emergente detectada. Intentando cerrarla.")
        await close_button.click()
        await asyncio.sleep(1)
        logging.info("Notificación cerrada exitosamente.")
    except Error:
        logging.info("No se detectó ninguna notificación emergente o no se pudo cerrar.")
    except Exception as e:
        logging.warning(f"Error inesperado al manejar la notificación: {e}")

async def scrape_falabella() -> List[Dict[str, Any]]:
    logging.info("Iniciando el scraper para Falabella...")
    products_data: List[Dict[str, Any]] = []
    
    os.makedirs(DEBUG_DIR, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='es-CO'
        )
        
        page = await context.new_page()
        
        await page.route('**/*.{png,jpg,jpeg,gif,webp,svg}', lambda route: route.abort())
        
        for page_num in range(1, PAGES_TO_SCRAPE + 1):
            url = SEARCH_URL_ALT.format(page_num)
            logging.info(f"Scrapeando página {page_num}: {url}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await asyncio.sleep(10)
                await _handle_notification(page)
                
                await page.evaluate('window.scrollBy(0, 1000)')
                await asyncio.sleep(5)

                product_locator = '//a[contains(@class, "pod-4_GRID")]'
                await page.locator(f"xpath={product_locator}").first.wait_for(timeout=30000)

                product_cards = page.locator(f"xpath={product_locator}")
                count = await product_cards.count()
                logging.info(f"Encontradas {count} tarjetas de producto en la página {page_num}.")

                if count == 0:
                    logging.warning(f"No se encontraron tarjetas de producto en la página {page_num}.")
                    debug_path = os.path.join(DEBUG_DIR, f"falabella_page_{page_num}_debug_no_product_card.png")
                    await page.screenshot(path=debug_path)
                    logging.info(f"Screenshot de depuración guardado en: {debug_path}")
                    continue
                
                for i in range(count):
                    card = product_cards.nth(i)
                    
                    # Check if it is a product card
                    price_element = card.locator('xpath=.//ol[contains(@class, "pod-prices")]').first
                    if await price_element.count() == 0:
                        continue

                    name_element = card.locator('xpath=.//b[contains(@class, "pod-title")]').first
                    url_element = card.locator('xpath=.//a').first

                    product_name = await name_element.text_content() if await name_element.count() > 0 else "Nombre no disponible"
                    current_price_str = await price_element.text_content() if await price_element.count() > 0 else None
                    product_url = await url_element.get_attribute('href') if await url_element.count() > 0 else "URL no disponible"

                    if product_url and not product_url.startswith('http'):
                        product_url = BASE_URL + product_url

                    product_info = {
                        'product_name': product_name.strip() if product_name else "Nombre no disponible",
                        'current_price': _clean_price(current_price_str),
                        'normal_price': None, 
                        'product_url': product_url,
                    }
                    
                    if product_name != "Nombre no disponible" and current_price_str:
                        products_data.append(product_info)

                logging.info(f"Extraídos {len(products_data)} productos de la página {page_num}.")
                
            except Error as e:
                logging.error(f"Error de Playwright al cargar o procesar la página {page_num}: {e}")
                debug_path = os.path.join(DEBUG_DIR, f"falabella_page_{page_num}_error.png")
                try:
                    await page.screenshot(path=debug_path)
                    logging.info(f"Screenshot de depuración guardado en: {debug_path}")
                except Exception as screenshot_e:
                    logging.warning(f"No se pudo tomar screenshot de depuración: {screenshot_e}")
                continue
            except Exception as e:
                logging.error(f"Error inesperado en página {page_num}: {e}")
                continue
        
        await context.close()
        await browser.close()
    
    logging.info(f"Scraping de Falabella finalizado. Se extrajeron {len(products_data)} productos en total.")
    return products_data

async def main():
    """Función principal para ejecutar el scraper"""
    results = await scrape_falabella()
    
    if results:
        df = pd.DataFrame(results)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        
        print("Resultados del scraping:")
        print(df)
        
        print(f"\nEstadísticas:")
        print(f"Total de productos: {len(results)}")
        print(f"Productos con precio actual: {df['current_price'].notna().sum()}")
        print(f"Productos con precio normal: {df['normal_price'].notna().sum()}")
        
        output_dir = r"c:\Users\decid\Downloads\TechHunter-colombia\data\raw"
        os.makedirs(output_dir, exist_ok=True)
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"falabella_celulares_{current_date}.csv"
        full_path = os.path.join(output_dir, filename)
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"\nResultados guardados en {full_path}")
        
        print(f"\nPrimeros 5 productos:")
        for i, product in enumerate(results[:5]):
            print(f"{i+1}. {product['product_name']}")
            print(f"   Precio: ${product['current_price']:,.0f}" if product['current_price'] else "   Precio: No disponible")
            print(f"   URL: {product['product_url']}")
            print()
    else:
        print("No se extrajo ningún producto. Revisa los logs para más detalles.")

if __name__ == '__main__':
    asyncio.run(main())
