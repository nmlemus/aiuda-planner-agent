# Machine Learning Examples

This page shows common machine learning workflows with DSAgent.

## Classification

### Basic Classification Pipeline

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./customers.csv") as agent:
    result = agent.run("""
        Build a classification model to predict customer churn:
        1. Explore and preprocess the data
        2. Handle class imbalance if present
        3. Train multiple models (Logistic Regression, Random Forest, XGBoost)
        4. Compare performance with cross-validation
        5. Select the best model and show feature importance
    """)

    print(result.answer)
```

### Interactive Model Building

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Load and explore
agent.chat("Load the titanic dataset from seaborn")
agent.chat("Show me the survival rate by different features")

# Feature engineering
agent.chat("Create useful features like family_size, is_alone, title from name")

# Model training
agent.chat("Train a random forest with the engineered features")

# Evaluation
agent.chat("Show confusion matrix and classification report")
agent.chat("What are the most important features?")

# Iterate
agent.chat("Try XGBoost and compare with random forest")

agent.shutdown()
```

## Regression

### Price Prediction

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./housing.csv") as agent:
    result = agent.run("""
        Build a house price prediction model:
        1. Analyze feature correlations with price
        2. Handle missing values and outliers
        3. Encode categorical variables
        4. Train Linear Regression, Random Forest, and LightGBM
        5. Evaluate with RMSE, MAE, and R²
        6. Create residual plots
    """)

    print(result.answer)
```

## Clustering

### Customer Segmentation

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

agent.chat("Load customer_transactions.csv")

# Prepare for clustering
agent.chat("""
Create RFM features:
- Recency: days since last purchase
- Frequency: number of purchases
- Monetary: total spend
""")

# Find optimal clusters
agent.chat("Use the elbow method to find optimal number of clusters")

# Perform clustering
agent.chat("Apply K-Means with the optimal k and visualize clusters")

# Interpret results
agent.chat("Describe each customer segment based on their characteristics")

agent.shutdown()
```

## Feature Selection

### Using Boruta

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./high_dimensional_data.csv") as agent:
    result = agent.run("""
        Perform feature selection:
        1. Use Boruta to identify important features
        2. Compare with Recursive Feature Elimination
        3. Show selected features and their importance
        4. Train a model with only selected features
        5. Compare performance vs using all features
    """)

    print(result.answer)
```

## AutoML with PyCaret

### Automated Model Selection

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

agent.chat("Load my_dataset.csv")

# Use PyCaret for AutoML
response = agent.chat("""
Use PyCaret to:
1. Setup the classification experiment
2. Compare all models
3. Tune the top 3 models
4. Create an ensemble
5. Show the final model performance
""")

print(response.content)
agent.shutdown()
```

## Model Interpretation

### SHAP Values

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

agent.chat("Load the breast cancer dataset from sklearn")
agent.chat("Train an XGBoost classifier")

# Interpret with SHAP
agent.chat("""
Explain the model using SHAP:
1. Create a summary plot
2. Show dependence plots for top features
3. Explain a single prediction
""")

agent.shutdown()
```

## Time Series Forecasting

### Sales Forecasting

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./daily_sales.csv") as agent:
    result = agent.run("""
        Create a sales forecast:
        1. Plot historical sales with trend and seasonality
        2. Test for stationarity
        3. Try multiple approaches:
           - ARIMA/SARIMA
           - Prophet
           - XGBoost with lag features
        4. Compare forecast accuracy
        5. Generate 30-day forecast with confidence intervals
    """)

    print(result.answer)
```

## Model Deployment Preparation

### Export Model Pipeline

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

agent.chat("Load training_data.csv")

# Build complete pipeline
agent.chat("""
Create a scikit-learn pipeline that:
1. Imputes missing values
2. Scales numerical features
3. Encodes categorical features
4. Trains a Random Forest

Then save the pipeline with joblib.
""")

# Test the saved model
agent.chat("Load the saved pipeline and test it on sample data")

agent.shutdown()
```

## Hyperparameter Tuning

### Grid Search with Cross-Validation

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./data.csv") as agent:
    result = agent.run("""
        Optimize an XGBoost model:
        1. Define a parameter grid for key hyperparameters
        2. Use RandomizedSearchCV with 5-fold CV
        3. Show the best parameters found
        4. Plot learning curves for the best model
        5. Compare with default parameters
    """)

    print(result.answer)
```

## Next Steps

- [Data Analysis Examples](data-analysis.md)
- [Python API Reference](../api/overview.md)
- [Available Libraries](../guide/cli.md#included-libraries)
