import logging
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, ElementHandle, Error
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
# URL corregida basada en la estructura real de Falabella Colombia
SEARCH_URL = "https://www.falabella.com.co/falabella-co/category/cat1660941/Celulares-y-Telefonos?page={}"
# URL alternativa de búsqueda si la categoria no funciona
SEARCH_URL_ALT = "https://www.falabella.com.co/falabella-co/search?Ntt=celulares&page={}"
PAGES_TO_SCRAPE = 3  # Reducido para pruebas iniciales

def _clean_price(price_str: Optional[str]) -> Optional[float]:
    """
    Limpia una cadena de texto que representa un precio para convertirla en un flotante.
    Ejemplo: '$ 1.999.900' -> 1999900.0
    """
    if price_str is None or not price_str.strip():
        return None
    
    # Usa una expresión regular para eliminar todo lo que no sea un dígito
    numeric_string = re.sub(r'[^\d]', '', price_str)
    if numeric_string:
        return float(numeric_string)
    return None

async def _extract_product_data(product_card: ElementHandle) -> Optional[Dict[str, Any]]:
    """
    Extrae la información de una única tarjeta de producto con selectores actualizados.
    """
    try:
        # --- Extracción de la URL del Producto ---
        # Múltiples selectores posibles para el enlace
        link_element = await product_card.query_selector('a[href]')
        if not link_element:
            # Selector alternativo
            link_element = await product_card.query_selector('.jsx-2074915182 a')
            
        if not link_element:
            logging.warning("No se encontró el enlace para una tarjeta de producto. Saltando.")
            return None
            
        product_url = await link_element.get_attribute('href')
        if product_url and not product_url.startswith('http'):
            product_url = BASE_URL + product_url

        # --- Extracción del Nombre del Producto ---
        # Múltiples selectores posibles para el nombre
        name_selectors = [
            'b[data-testid="name"]',
            '[data-testid="product-title"]',
            '.product-title',
            'h3',
            'a[title]',
            '.jsx-2074915182 b'
        ]
        
        product_name = "Nombre no disponible"
        for selector in name_selectors:
            name_element = await product_card.query_selector(selector)
            if name_element:
                name_text = await name_element.text_content()
                if name_text and name_text.strip():
                    product_name = name_text.strip()
                    break
            
            # Intentar obtener del atributo title del enlace
            if selector == 'a[title]' and link_element:
                title_attr = await link_element.get_attribute('title')
                if title_attr:
                    product_name = title_attr.strip()
                    break

        # --- Extracción del Precio Actual ---
        price_selectors = [
            '[data-testid="price-value"]',
            '.price-current',
            '.jsx-4184467617',
            '.price',
            '.current-price'
        ]
        
        current_price_str = None
        for selector in price_selectors:
            price_element = await product_card.query_selector(selector)
            if price_element:
                current_price_str = await price_element.text_content()
                if current_price_str:
                    break

        # --- Extracción del Precio Normal (Tachado) ---
        normal_price_selectors = [
            'span[data-testid="price-original"]',
            '.price-original',
            '.strikethrough',
            '.was-price'
        ]
        
        normal_price_str = None
        for selector in normal_price_selectors:
            price_element = await product_card.query_selector(selector)
            if price_element:
                normal_price_str = await price_element.text_content()
                if normal_price_str:
                    break

        product_data = {
            'product_name': product_name,
            'current_price': _clean_price(current_price_str),
            'normal_price': _clean_price(normal_price_str),
            'product_url': product_url,
        }
        
        # Solo retornar si tenemos al menos nombre y precio
        if product_name != "Nombre no disponible" and (current_price_str or normal_price_str):
            return product_data
        else:
            logging.debug(f"Producto descartado - Nombre: {product_name}, Precio actual: {current_price_str}")
            return None
            
    except Exception as e:
        logging.warning(f"Error al extraer datos del producto: {e}")
        return None

async def scrape_falabella() -> List[Dict[str, Any]]:
    """
    Función principal para realizar el web scraping en Falabella Colombia.
    """
    logging.info("Iniciando el scraper para Falabella...")
    products_data: List[Dict[str, Any]] = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Cambio a False para debugging
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='es-CO'
        )
        
        page = await context.new_page()
        
        # Bloquear recursos innecesarios pero permitir JS esencial
        await page.route('**/*.{png,jpg,jpeg,gif,webp,svg}', lambda route: route.abort())
        
        for page_num in range(1, PAGES_TO_SCRAPE + 1):
            url = SEARCH_URL.format(page_num)
            logging.info(f"Scrapeando página {page_num}: {url}")
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                
                # Esperar a que la página cargue contenido
                await asyncio.sleep(3)
                
                # Selectores actualizados para contenedores de productos
                product_container_selectors = [
                    '#testId-searchResults-products',
                    '.search-results',
                    '.products-grid',
                    '[data-automation-id="search-results"]'
                ]
                
                container_found = False
                for container_selector in product_container_selectors:
                    try:
                        await page.wait_for_selector(container_selector, timeout=10000)
                        container_found = True
                        logging.info(f"Contenedor encontrado con selector: {container_selector}")
                        break
                    except:
                        continue
                
                if not container_found:
                    logging.warning(f"No se encontró el contenedor de productos en página {page_num}")
                    # Intentar con URL alternativa
                    if page_num == 1:
                        url_alt = SEARCH_URL_ALT.format(page_num)
                        logging.info(f"Intentando con URL alternativa: {url_alt}")
                        await page.goto(url_alt, wait_until='domcontentloaded', timeout=60000)
                        await asyncio.sleep(3)
                
                # Selectores para tarjetas de producto
                product_card_selectors = [
                    'div[data-testid="pod-item"]',
                    '.jsx-2074915182',
                    '.product-item',
                    '.product-card',
                    '[data-automation-id="product-item"]'
                ]
                
                product_cards = []
                for card_selector in product_card_selectors:
                    product_cards = await page.query_selector_all(card_selector)
                    if product_cards:
                        logging.info(f"Se encontraron {len(product_cards)} productos con selector: {card_selector}")
                        break
                
                if not product_cards:
                    logging.warning(f"No se encontraron tarjetas de producto en la página {page_num}")
                    # Guardar screenshot para debugging
                    await page.screenshot(path=f"falabella_page_{page_num}_debug.png")
                    continue
                
                extracted_count = 0
                for i, card in enumerate(product_cards):
                    try:
                        product_info = await _extract_product_data(card)
                        if product_info:
                            products_data.append(product_info)
                            extracted_count += 1
                        
                        # Pequeña pausa entre extracciones
                        if i % 10 == 0:
                            await asyncio.sleep(0.5)
                            
                    except Error as e:
                        logging.warning(f"Error de Playwright al procesar producto {i} en página {page_num}: {e}")
                    except Exception as e:
                        logging.warning(f"Error inesperado al procesar producto {i} en página {page_num}: {e}")
                
                logging.info(f"Extraídos {extracted_count} productos de {len(product_cards)} tarjetas en página {page_num}")
                
                # Pausa entre páginas
                await asyncio.sleep(2)
                
            except Error as e:
                logging.error(f"No se pudo cargar la página {page_num}. Error: {e}")
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
        # Convertir a DataFrame de pandas para una mejor visualización
        df = pd.DataFrame(results)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        
        print("Resultados del scraping:")
        print(df)
        
        # Estadísticas básicas
        print(f"\nEstadísticas:")
        print(f"Total de productos: {len(results)}")
        print(f"Productos con precio actual: {df['current_price'].notna().sum()}")
        print(f"Productos con precio normal: {df['normal_price'].notna().sum()}")
        
        # Guardar en archivo CSV
        output_dir = r"c:\Users\decid\Downloads\TechHunter-colombia\data\raw"
        os.makedirs(output_dir, exist_ok=True)
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"falabella_celulares_{current_date}.csv"
        full_path = os.path.join(output_dir, filename)
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"\nResultados guardados en {full_path}")
        
        # Mostrar algunos ejemplos
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