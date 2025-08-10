# TechHunter Colombia — Comparador Inteligente de Ofertas 🤖

<div align="center">

[![Licencia: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Estado del Proyecto](https://img.shields.io/badge/estado-en%20desarrollo-green.svg)](https://github.com/tu_usuario/TechHunter)

**Tu copiloto de IA para encontrar y analizar las mejores ofertas de tecnología en el mercado colombiano.**

</div>

---

## 📌 Descripción

**TechHunter** es una solución de ingeniería de datos y ciencia de datos que ataca un problema común: la dificultad de encontrar la mejor oferta tecnológica. La aplicación **automatiza el proceso de búsqueda, comparación y análisis de productos** de las principales tiendas de Colombia.

No se limita a mostrar una lista de precios; su verdadero poder reside en la integración de un **Modelo de Lenguaje Grande (LLM) que se ejecuta localmente**. Este modelo actúa como un experto en tecnología, generando **resúmenes y explicaciones en lenguaje natural** sobre por qué una oferta es valiosa, destacando sus pros, contras y la relación costo-beneficio para que tomes la mejor decisión de compra.

---

## ✨ Características Clave

* **📈 Análisis de Mercado en Tiempo Real:** Realiza web scraping automatizado de múltiples tiendas para obtener los datos más recientes.
* **🧹 Procesamiento de Datos Robusto:** Un pipeline ETL que limpia, normaliza y estandariza los datos de productos para un análisis preciso.
* **🧠 Motor de Recomendación Inteligente:** Utiliza un sistema de scoring para clasificar las ofertas no solo por precio, sino por su verdadera relación valor/precio.
* **🤖 Explicaciones con IA:** El LLM local analiza las mejores ofertas y explica en español claro por qué son recomendables, como si hablaras con un experto.
* **🖥️ Interfaz Interactiva:** Un dashboard web construido con Streamlit que permite filtrar, ordenar y explorar los productos y sus análisis detallados.
* **📦 Portabilidad y Control:** Todo el sistema, incluido el LLM, está diseñado para ejecutarse localmente o ser empaquetado con Docker, dándote control total.

---

## 📸 Demo de la Aplicación

<div align="center">

*Aquí puedes insertar una captura de pantalla o un GIF animado de la interfaz de Streamlit.*

!
*Interfaz principal de TechHunter mostrando las recomendaciones y filtros.*

</div>

---

## 🏗️ Arquitectura y Flujo de Datos

El proyecto sigue una arquitectura modular y escalable, separando cada etapa del proceso en componentes lógicos.

<div align="center">

*Diagrama de la arquitectura del sistema.*

!

</div>

El flujo de datos se puede resumir en 5 pasos clave:
1.  **EXTRACCIÓN (Scraping):** Un orquestador ejecuta los scripts de scraping (`Playwright/Requests`) para cada tienda. Los datos crudos (HTML/JSON) se guardan en `data/raw/`.
2.  **TRANSFORMACIÓN (ETL):** Un pipeline de `Pandas` toma los datos crudos, los limpia (manejo de nulos, formatos), mapea atributos a un esquema unificado (ej. "16 GB RAM" -> 16) y guarda los datos procesados y listos para el análisis en `data/processed/`.
3.  **ANÁLISIS (Recommender):** El motor de recomendación carga los datos limpios, calcula un `score` para cada producto basado en sus especificaciones y precio, y genera un ranking.
4.  **ENRIQUECIMIENTO (LLM):** Las mejores ofertas del ranking se envían al `LLM Adapter`. Usando plantillas de prompts predefinidas, el modelo genera un análisis cualitativo para cada una.
5.  **PRESENTACIÓN (UI):** La aplicación de `Streamlit` consume los datos enriquecidos y los presenta al usuario a través de una interfaz interactiva.

---

## 🧩 Stack Tecnológico

| Componente      | Tecnología                                                                   |
| --------------- | ---------------------------------------------------------------------------- |
| **Lenguaje** | Python 3.11+                                                                 |
| **Web Scraping**| Playwright / BeautifulSoup + Requests                                        |
| **Procesamiento**| Pandas, NumPy                                                                |
| **Base de Datos**| SQLite (para almacenamiento local de datos procesados)                       |
| **LLM** | `Mistral-7B-Instruct.Q4_K_M.gguf` con `llama-cpp-python`                       |
| **Frontend** | Streamlit                                                                    |
| **Contenedores**| Docker & Docker Compose (Opcional, para despliegue)                          |

---

## 📂 Estructura del Proyecto

<details>
<summary>Haz clic para ver la estructura detallada de carpetas y archivos</summary>

```plaintext
techhunter_colombia/
│
├── README.md
├── requirements.txt
├── config/
│   ├── config.yaml               # Configuración global (paths, DB, parámetros)
│   └── llm_config.yaml           # Configuración específica del modelo LLM
│
├── data/
│   ├── raw/                      # Datos crudos del scraping (ej. alkosto_laptops.json)
│   ├── processed/                # Datos limpios y normalizados (ej. products.db)
│   └── models/                   # Modelos LLM locales (ej. mistral-7b...)
│
├── etl/
│   ├── __init__.py
│   ├── run_etl.py                # Script principal para ejecutar el pipeline ETL
│   └── modules/
│       ├── cleaning.py           # Funciones de limpieza de datos
│       └── mapping.py            # Mapeo de atributos (RAM, GPU, etc.)
│
├── llm/
│   ├── __init__.py
│   ├── llm_adapter.py            # Interfaz para integrar diferentes LLMs
│   ├── prompt_templates.py       # Plantillas de prompts para las explicaciones
│
├── recommender/
│   ├── __init__.py
│   ├── scoring.py                # Lógica para el cálculo de score valor/precio
│   └── engine.py                 # Motor principal de recomendación
│
├── scraping/
│   ├── __init__.py
│   ├── run_scraping.py           # Orquestador que ejecuta todos los scrapers
│   └── stores/
│       ├── alkosto.py
│       ├── falabella.py
│       └── ktronix.py
│
├── scripts/
│   └── download_model.sh         # Script para descargar el modelo GGUF
│
├── tests/
│   ├── test_etl.py
│   └── test_recommender.py
│
└── webapp/
    ├── app.py                    # App principal de Streamlit (punto de entrada)
    └── pages/
        ├── 1_📈_Dashboard.py
        └── 2_ℹ️_Acerca_del_Proyecto.py