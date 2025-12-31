# Financial Datasets MCP Demo

Este demo muestra cómo usar DSAgent con el MCP server de [Financial Datasets](https://financialdatasets.ai) para obtener y analizar datos financieros de empresas.

## Requisitos

1. **API Key de Financial Datasets**
   - Regístrate en https://financialdatasets.ai
   - Obtén tu API key gratuita

2. **DSAgent con soporte MCP**
   ```bash
   pip install "datascience-agent[mcp]"
   ```

## Configuración

1. Exporta tu API key:
   ```bash
   export FINANCIAL_DATASETS_API_KEY="tu-api-key-aqui"
   ```

2. El archivo `mcp.yaml` ya está configurado para conectarse al servidor MCP.

## Herramientas MCP Disponibles

| Herramienta | Descripción |
|-------------|-------------|
| `getCompanyFacts` | Info de empresa (market cap, sector, empleados) |
| `getIncomeStatement` | Estados de resultados |
| `getBalanceSheet` | Balance general |
| `getCashFlowStatement` | Flujo de caja |
| `getFinancialMetrics` | Ratios financieros históricos |
| `getFinancialMetricsSnapshot` | Métricas de valuación actuales |
| `getStockPrices` | Precios históricos de acciones |
| `getStockPriceSnapshot` | Precio actual de acciones |
| `getFilings` | Lista de reportes SEC |
| `getNews` | Noticias recientes |

## Ejemplos de Uso

### Análisis de una empresa (NVIDIA)

```bash
dsagent "Obtén los datos financieros de NVIDIA (NVDA) incluyendo income statement, \
balance sheet y métricas financieras de los últimos 3 años. \
Analiza la tendencia de ingresos, márgenes y crecimiento. \
Crea visualizaciones de las métricas clave." \
  --data ./portfolio.csv \
  --mcp-config ./mcp.yaml \
  --model gpt-4o
```

### Comparación de empresas tech

```bash
dsagent "Compara las métricas financieras de Apple (AAPL), Microsoft (MSFT) y Google (GOOGL). \
Obtén los datos de valuación, rentabilidad y crecimiento. \
Crea una tabla comparativa y gráficos." \
  --data ./portfolio.csv \
  --mcp-config ./mcp.yaml \
  --model gpt-4o
```

### Análisis de precios y noticias

```bash
dsagent "Obtén los precios históricos de Tesla (TSLA) del último año \
y las noticias recientes. Analiza la correlación entre noticias \
importantes y movimientos de precio." \
  --data ./portfolio.csv \
  --mcp-config ./mcp.yaml \
  --model gpt-4o
```

## Archivo de Datos de Ejemplo

El archivo `portfolio.csv` contiene un portfolio de ejemplo para análisis:

```csv
ticker,shares,purchase_price,purchase_date
AAPL,100,150.00,2023-01-15
NVDA,50,250.00,2023-03-20
MSFT,75,280.00,2023-02-10
GOOGL,30,120.00,2023-04-05
```

## Notas

- La API tiene límites de rate limiting en el tier gratuito
- Algunos datos requieren suscripción premium
- Los datos están disponibles para +30,000 tickers con 30+ años de historia
