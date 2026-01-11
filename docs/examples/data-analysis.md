# Data Analysis Examples

This page shows common data analysis workflows with DSAgent.

## Exploratory Data Analysis

### Load and Explore a Dataset

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Load data
response = agent.chat("""
Load the file sales_data.csv and give me:
1. Basic statistics
2. Data types
3. Missing values
4. First few rows
""")

print(response.content)
agent.shutdown()
```

### CLI Equivalent

```bash
dsagent run "Load sales_data.csv and provide exploratory analysis" --data ./sales_data.csv
```

## Time Series Analysis

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./stock_prices.csv") as agent:
    result = agent.run("""
        Perform time series analysis:
        1. Plot the price over time
        2. Calculate moving averages (7-day, 30-day)
        3. Identify trends and seasonality
        4. Create a simple forecast
    """)

    print(result.answer)
    print(f"Charts saved to: {result.artifacts}")
```

## Statistical Analysis

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Load and analyze
agent.chat("Load experiment_results.csv")

# Statistical tests
response = agent.chat("""
Perform statistical analysis:
1. Test for normality (Shapiro-Wilk)
2. Compare groups A and B (t-test or Mann-Whitney)
3. Calculate effect size
4. Report confidence intervals
""")

print(response.content)
agent.shutdown()
```

## Data Cleaning Pipeline

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./messy_data.csv") as agent:
    result = agent.run("""
        Clean this dataset:
        1. Handle missing values appropriately
        2. Remove duplicates
        3. Fix data types
        4. Handle outliers
        5. Save cleaned data to cleaned_data.csv
    """)

    print(f"Cleaning complete: {result.answer}")
```

## Visualization Gallery

### Creating Multiple Charts

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

agent.chat("Load the iris dataset")

# Create various visualizations
agent.chat("Create a pair plot colored by species")
agent.chat("Create a correlation heatmap")
agent.chat("Create violin plots for each feature")
agent.chat("Create a 3D scatter plot of the first 3 features")

# Export all work
agent.export_notebook("iris_visualizations.ipynb")
agent.shutdown()
```

## Report Generation

### PDF Report (Docker with LaTeX)

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Perform analysis
agent.chat("Load quarterly_sales.csv and analyze trends")
agent.chat("Create visualizations for the report")

# Generate LaTeX report (requires Docker :full image)
agent.chat("""
Create a professional PDF report with:
1. Executive summary
2. Data overview
3. Key findings with charts
4. Recommendations

Use LaTeX to generate the PDF.
""")

agent.shutdown()
```

## Working with Multiple Files

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Load multiple datasets
agent.chat("Load customers.csv and orders.csv")

# Join and analyze
response = agent.chat("""
1. Join customers with orders on customer_id
2. Calculate total spend per customer
3. Segment customers by spending
4. Create a visualization of segments
""")

print(response.content)
agent.shutdown()
```

## Batch Processing

### Analyze Multiple Files

```python
from dsagent import PlannerAgent
from pathlib import Path

reports = []
for csv_file in Path("./data").glob("*.csv"):
    with PlannerAgent(model="gpt-4o", data=str(csv_file)) as agent:
        result = agent.run("Provide a summary with key statistics")
        reports.append({
            "file": csv_file.name,
            "summary": result.answer,
            "notebook": result.notebook_path
        })

# Combine reports
for report in reports:
    print(f"\n=== {report['file']} ===")
    print(report['summary'])
```

## Next Steps

- [Machine Learning Examples](machine-learning.md)
- [Python API Reference](../api/overview.md)
- [CLI Reference](../guide/cli.md)
