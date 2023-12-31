import sys
import os
import json
import datetime
import pickle
import db

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR

# List of regressors to try
regressors = {
    "Linear Regression": {"model": LinearRegression(), "params": {}},
    "Ridge Regression": {
        "model": Ridge(),
        "params": {
            "alpha": [0.1, 1, 10, 100],
        },
    },
    "Lasso Regression": {
        "model": Lasso(),
        "params": {
            "alpha": [0.1, 1, 10, 100],
        },
    },
    "Random Forest": {
        "model": RandomForestRegressor(),
        # Random Forest was too slow to run with GridSearchCV, so it will use the default parameters
        "params": {},
    },
    "Gradient Boosting": {
        "model": GradientBoostingRegressor(),
        "params": {
            "n_estimators": [10, 100],
            "max_depth": [3, 10],
            "min_samples_split": [2, 5],
        },
    },
}

# List of setups to use, each will result in a model that can be used for a specific purpose
# "features" will be a list of features to use, every feature that is not here will be dropped
setups = {
    "bostadspriser-without-askingPrice-combine-cpi": {
        "features": [
            "cpi",
            "fee",
            "livingArea",
            "rooms",
            "runningCosts",
            "hasElevator",
            "hasBalcony",
            "lat",
            "long",
            "hasHousingCooperative",
            "isPlot",
            "isWinterLeisureHouse",
            "isApartment",
            "isFarmWithForest",
            "isHouse",
            "isRowHouse",
            "isPairHouse",
            "isPairTerracedRowHouse",
            "isTerracedHouse",
            "isFarmWithoutForest",
            "isLeisureHouse",
            "isOtherHousingForm",
            "isFarmWithAgriculture",
            "age",
            "sinceLastRenovation",
            "yearsSinceSold",
        ],
        "target": "finalPrice",
    },
    "bostadspriser-with-askingPrice-combine-cpi": {
        "features": [
            "cpi",
            "fee",
            "livingArea",
            "rooms",
            "runningCosts",
            "hasElevator",
            "hasBalcony",
            "lat",
            "long",
            "hasHousingCooperative",
            "isPlot",
            "isWinterLeisureHouse",
            "isApartment",
            "isFarmWithForest",
            "isHouse",
            "isRowHouse",
            "isPairHouse",
            "isPairTerracedRowHouse",
            "isTerracedHouse",
            "isFarmWithoutForest",
            "isLeisureHouse",
            "isOtherHousingForm",
            "isFarmWithAgriculture",
            "age",
            "sinceLastRenovation",
            "yearsSinceSold",
            "askingPrice",
        ],
        "target": "finalPrice",
    },
}


def print_same_line(text):
    print(text, end="")
    sys.stdout.flush()


def get_test_train_split(dataset, features, target):
    y = dataset[target]
    X = dataset[features]

    # Sort columns alphabetically to make sure the model will use the same order as the API
    X = X.reindex(sorted(X.columns), axis=1)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    return X_train, X_test, y_train, y_test, scaler


def evaluate_model(
    name, regressor_name, model, params, X_train, y_train, X_test, y_test
):
    print(f"[{name}] Evaluating " + regressor_name + "... ")

    print(f"[{name}] Grid searching... ")
    gs_model = GridSearchCV(
        estimator=model,
        param_grid=params,
        scoring="neg_mean_squared_error",
        cv=5,
        n_jobs=-1,
    )

    print(f"[{name}] Fitting model... ")
    gs_model.fit(X_train, y_train)

    print(f"[{name}] Best params (" + str(gs_model.best_params_) + ") ")

    print(f"[{name}] Predicting... ")
    y_pred = gs_model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    print(f"[{name}] MSE: " + str(mse) + ", RMSE: " + str(rmse) + ", R^2: " + str(r2))
    return gs_model, gs_model.best_params_, mse, rmse, r2


def train(name, X_train, y_train, X_test, y_test):
    results = {}
    for regressor_name, regressor in regressors.items():
        model, best_params, mse, rmse, r2 = evaluate_model(
            name,
            regressor_name,
            regressor["model"],
            regressor["params"],
            X_train,
            y_train,
            X_test,
            y_test,
        )
        results[regressor_name] = {
            "model": model,
            "bestParams": best_params,
            "mse": mse,
            "rmse": rmse,
            "r2": r2,
        }

    return results


def main():
    print(
        f" --- Starting training for {len(setups)} setups {datetime.datetime.now().isoformat()} --- "
    )
    print("Loading data...")
    file_path = "../dataset/listings.parquet"
    data = pd.read_parquet(file_path)

    # print how many rows and columns
    print("Rows: " + str(data.shape[0]) + ", Columns: " + str(data.shape[1]))

    print("Preprocessing...")
    # Dropping NaN values will drop every row without coordinates
    data = data.dropna()

    # Combine CPI with finalPrice and askingPrice
    cpiNow = db.get_cpi(datetime.datetime.now())
    if cpiNow is None:
        print("Could not get CPI for now, exiting...")
        exit()

    # transform finalPrice and asking price to be finalPrice* (cpiNow/cpi) and askingPrice* (cpiNow/cpi)
    data["finalPrice"] = data["finalPrice"] * (cpiNow / data["cpi"])
    data["askingPrice"] = data["askingPrice"] * (cpiNow / data["cpi"])

    # Sort column names alphabetically to make it easier to use the model from the API later (it will also sort alphabetically)
    data = data.reindex(sorted(data.columns), axis=1)

    for name, setup in setups.items():
        # Allow multiple timed versions of the same model
        now = datetime.datetime.now()
        name_with_date = name + "-" + now.strftime("%Y-%m-%d-%H-%M")

        print(f"[{name}] Getting test train split...")
        X_train, X_test, y_train, y_test, scaler = get_test_train_split(
            data, setup["features"], setup["target"]
        )

        print(f"[{name}] Training...")
        results = train(
            name,
            X_train,
            y_train,
            X_test,
            y_test,
        )

        # Find the best model
        results_df = pd.DataFrame(results)
        results_df = results_df.drop("model", axis=0)
        results_df = results_df.transpose()
        results_df = results_df.sort_values(by=["rmse"])
        best_model = results_df.index[0]
        print(f"[{name}] Best model: " + best_model)

        print(f"[{name}] Saving model and results...")
        folder = f"../models/{name_with_date}"

        # Make directory
        os.makedirs(folder, exist_ok=True)

        # Save model
        with open(f"{folder}/model.pkl", "wb") as f:
            pickle.dump(results[best_model]["model"], f)

        # Save scaler
        with open(f"{folder}/scaler.pkl", "wb") as f:
            pickle.dump(scaler, f)

        # Save results
        results_df.to_csv(f"{folder}/results.csv")

        # Save metadata
        metadata = {
            "name": name,
            "nameWithDate": name_with_date,
            "features": setup["features"],
            "target": setup["target"],
            "trainedAt": now.isoformat(),
            "model": {
                "name": best_model,
                "params": results[best_model]["bestParams"],
                "mse": results[best_model]["mse"],
                "rmse": results[best_model]["rmse"],
                "r2": results[best_model]["r2"],
            },
        }
        with open(f"{folder}/metadata.json", "w") as f:
            json.dump(metadata, f)

        print(f"[{name}] Done!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting...")
        exit()
