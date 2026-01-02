# Kaggle Competition

https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques

House Prices - Advanced Regression Techniques
Predict sales prices and practice feature engineering, RFs, and gradient boosting

```bash
dsagent "predict the sales price for each house. For each Id in the test set, 
you must predict the value of the SalePrice variable.

Metric
Submissions are evaluated on Root-Mean-Squared-Error (RMSE) between the logarithm of 
the predicted value and the logarithm of the observed sales price. (Taking logs means 
that errors in predicting expensive houses and cheap houses will affect the result equally.)

Submission File Format
The file should contain a header and have the following format:

Id,SalePrice
1461,169000.1
1462,187724.1233
1463,175221
etc. 

Use boruta (already installed) for feature selection and pycaret to select the best 
model." --data /Users/nmlemus/Downloads/house-prices-advanced-regression-techniques \
--model claude-sonnet-4-5-20250929 --workspace examples
```