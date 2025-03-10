import numpy as np
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb
import matplotlib.pyplot as plt


def load_data():
    """
    Load California Housing dataset and split into train and test sets
    """
    # Load dataset
    california = fetch_california_housing()
    X, y = california.data, california.target

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    return X_train, X_test, y_train, y_test, california.feature_names


def train_model(X_train, y_train, X_test, y_test):
    """
    Train XGBoost model with early stopping
    """
    # Convert data into DMatrix format
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)

    # Set parameters
    params = {
        'objective': 'reg:squarederror',
        'max_depth': 6,
        'learning_rate': 0.05,
        'n_estimators': 1000,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'min_child_weight': 1,
        'seed': 42
    }

    # Train model with early stopping
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=1000,
        evals=[(dtrain, 'train'), (dtest, 'test')],
        early_stopping_rounds=50,
        verbose_eval=100
    )

    return model


def evaluate_model(model, X_test, y_test):
    """
    Evaluate model performance
    """
    # Make predictions
    dtest = xgb.DMatrix(X_test)
    y_pred = model.predict(dtest)

    # Calculate metrics
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    print("Model Performance Metrics:")
    print("-------------------------")
    print("RMSE: {:.4f}".format(rmse))
    print("R2 Score: {:.4f}".format(r2))

    return y_pred


def plot_feature_importance(model, feature_names):
    """
    Plot feature importance
    """
    importance = model.get_score(importance_type='weight')
    importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

    features, scores = zip(*importance)

    plt.figure(figsize=(12, 6))
    plt.bar(range(len(scores)), scores)
    plt.xticks(range(len(scores)), [
               feature_names[int(f[1:])] for f in features], rotation=45)
    plt.title('Feature Importance in California Housing Price Prediction')
    plt.xlabel('Features')
    plt.ylabel('Importance Score')
    plt.tight_layout()
    plt.savefig('feature_importance.png')
    plt.close()


def main():
    # Load and split data
    X_train, X_test, y_train, y_test, feature_names = load_data()

    # Train model
    print("Training XGBoost model...")
    model = train_model(X_train, y_train, X_test, y_test)

    # Evaluate model
    print("\nEvaluating model performance...")
    y_pred = evaluate_model(model, X_test, y_test)

    # Plot feature importance
    print("\nPlotting feature importance...")
    plot_feature_importance(model, feature_names)

    print("\nFeature importance plot saved as 'feature_importance.png'")


if __name__ == "__main__":
    main()
