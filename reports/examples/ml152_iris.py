"""Train-only model selection, then one untouched Iris holdout evaluation."""
import numpy as np
import sklearn
from sklearn.datasets import load_iris
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def run():
    iris = load_iris()
    train_ids, test_ids = train_test_split(
        np.arange(len(iris.target)), test_size=0.2,
        stratify=iris.target, random_state=42
    )
    X_train, y_train = iris.data[train_ids], iris.target[train_ids]
    X_test, y_test = iris.data[test_ids], iris.target[test_ids]
    folds = list(StratifiedKFold(
        n_splits=5, shuffle=True, random_state=42
    ).split(X_train, y_train))
    models = {
        "dummy": DummyClassifier(strategy="most_frequent"),
        "logistic": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000)
        ),
        "forest": RandomForestClassifier(
            n_estimators=100, random_state=42, n_jobs=1
        ),
    }
    print("scikit-learn:", sklearn.__version__)
    print("train / test:", len(train_ids), len(test_ids))
    print("train counts:", np.bincount(y_train).tolist())
    print("test counts:", np.bincount(y_test).tolist())
    results = {}
    for name, model in models.items():
        scores = cross_validate(
            model, X_train, y_train, cv=folds,
            scoring=["accuracy", "f1_macro", "recall_macro"]
        )
        results[name] = scores
        print(name)
        for metric in ("accuracy", "f1_macro", "recall_macro"):
            values = scores["test_" + metric]
            print(f"  {metric}: {values.mean():.3f} +/- {values.std():.3f}")
    # Toy rule: highest mean macro F1; tied scores keep dictionary order.
    chosen = max(results, key=lambda name: results[name]["test_f1_macro"].mean())
    model = models[chosen]
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    matrix = confusion_matrix(y_test, pred, labels=[0, 1, 2])
    print("chosen:", chosen)
    print(f"holdout accuracy: {accuracy_score(y_test, pred):.3f}")
    print(f"holdout macro F1: {f1_score(y_test, pred, average='macro'):.3f}")
    print("rows=actual, columns=predicted:", iris.target_names.tolist())
    print(matrix)
    return iris, train_ids, test_ids, folds, models, results, chosen, matrix


if __name__ == "__main__":
    run()
