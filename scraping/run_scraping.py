# scraping/run_scraping.py

import asyncio
import pandas as pd
from datetime import datetime
import os
import logging

# --- Importación de Scrapers ---
# Se importa el scraper activo para Alkosto.
# Los otros están comentados como placeholders para futuras implementaciones.
from stores.alkosto import scrape_alkosto
# from stores.falabella import scrape_falabella
# from stores.ktronix import scrape_ktronix

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuración ---
OUTPUT_DIR = "data/raw"

# Mapeo de tiendas con sus respectivas funciones de scraping.
# Esto facilita la adición de nuevas tiendas en el futuro.
ACTIVE_STORES = {
    "alkosto": scrape_alkosto,
    # "falabella": scrape_falabella,
    # "ktronix": scrape_ktronix,
}

def save_to_csv(data: list, store_name: str):
    """
    Convierte la lista de datos a un DataFrame de pandas y la guarda en un archivo CSV.
    El nombre del archivo incluye el nombre de la tienda y la fecha de ejecución.
    """
    if not data:
        logging.warning(f"No se recibieron datos para guardar de la tienda '{store_name}'. No se generará el archivo.")
        return

    # Crear el directorio de salida si no existe
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Obtener la fecha actual para el nombre del archivo
    current_date = datetime.now().strftime("%Y-%m-%d")
    filename = f"{store_name}_celulares_{current_date}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Convertir a DataFrame
    df = pd.DataFrame(data)
    
    # Añadir columnas de metadatos
    df['store'] = store_name
    df['extraction_date'] = current_date

    # Guardar en CSV con separador de punto y coma
    try:
        df.to_csv(filepath, sep=';', index=False, encoding='utf-8-sig')
        logging.info(f"Datos guardados exitosamente en: {filepath}")
    except Exception as e:
        logging.error(f"No se pudo guardar el archivo CSV para '{store_name}'. Error: {e}")

async def main():
    """
    Función principal que orquesta la ejecución de los scrapers definidos
    y el guardado de los datos.
    """
    logging.info("Iniciando el proceso de scraping de TechHunter Colombia.")
    
    # Ejecutar el scraper para cada tienda activa
    for store_name, scrape_function in ACTIVE_STORES.items():
        logging.info(f"--- Ejecutando scraper para: {store_name.upper()} ---")
        try:
            # Ejecutar la función de scraping asíncrona
            scraped_data = await scrape_function()
            # Guardar los resultados
            save_to_csv(scraped_data, store_name)
        except Exception as e:
            logging.error(f"Ocurrió un error inesperado durante el scraping de '{store_name}': {e}")
    
    logging.info("Proceso de scraping de TechHunter Colombia finalizado.")

if __name__ == "__main__":
    # Punto de entrada para ejecutar el script
    # asyncio.run() se encarga de gestionar el loop de eventos asíncronos
    asyncio.run(main())