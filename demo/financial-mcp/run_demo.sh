#!/bin/bash
# Financial Datasets MCP Demo
# Usage: ./run_demo.sh [your-api-key]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for API key
if [ -z "$FINANCIAL_DATASETS_API_KEY" ]; then
    if [ -n "$1" ]; then
        export FINANCIAL_DATASETS_API_KEY="$1"
    else
        echo "Error: FINANCIAL_DATASETS_API_KEY not set"
        echo ""
        echo "Usage:"
        echo "  export FINANCIAL_DATASETS_API_KEY='your-key'"
        echo "  ./run_demo.sh"
        echo ""
        echo "Or:"
        echo "  ./run_demo.sh your-api-key"
        echo ""
        echo "Get your free API key at: https://financialdatasets.ai"
        exit 1
    fi
fi

echo "=============================================="
echo "Financial Datasets MCP Demo"
echo "=============================================="
echo ""
echo "This demo will:"
echo "1. Connect to Financial Datasets MCP server"
echo "2. Fetch financial data for NVIDIA (NVDA)"
echo "3. Analyze income statements and metrics"
echo "4. Create visualizations"
echo ""
echo "Press Enter to start..."
read

dsagent "Analiza los datos financieros de NVIDIA (NVDA):
1. Obtén la información de la empresa (getCompanyFacts)
2. Obtén los income statements de los últimos 4 trimestres (getIncomeStatement)
3. Obtén las métricas financieras actuales (getFinancialMetricsSnapshot)
4. Obtén los precios de la acción del último mes (getStockPrices)

Con estos datos:
- Crea un resumen de la empresa
- Analiza la tendencia de ingresos y márgenes
- Visualiza el precio de la acción
- Da una conclusión sobre la salud financiera de la empresa" \
  --data "$SCRIPT_DIR/portfolio.csv" \
  --mcp-config "$SCRIPT_DIR/mcp.yaml" \
  --model gpt-4o
