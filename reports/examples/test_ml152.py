import unittest
import numpy as np
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.datasets import load_iris
from sklearn.metrics import silhouette_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from ml152_iris import run


class IrisTests(unittest.TestCase):
    def test_holdout_and_pipeline(self):
        iris, train, test, folds, models, results, chosen, matrix = run()
        self.assertFalse(set(train) & set(test))
        self.assertEqual(len(train), 120)
        self.assertEqual(len(test), 30)
        seen = []
        for learn, validate in folds:
            self.assertFalse(set(learn) & set(validate))
            self.assertFalse(set(train[learn]) & set(test))
            self.assertFalse(set(train[validate]) & set(test))
            pipe = clone(models["logistic"])
            pipe.fit(iris.data[train[learn]], iris.target[train[learn]])
            np.testing.assert_allclose(
                pipe.named_steps["standardscaler"].mean_,
                iris.data[train[learn]].mean(axis=0)
            )
            seen.extend(validate.tolist())
        self.assertEqual(sorted(seen), list(range(120)))
        for scores in results.values():
            for metric in ("accuracy", "f1_macro", "recall_macro"):
                self.assertTrue(np.isfinite(scores["test_" + metric]).all())
        self.assertIn(chosen, models)
        self.assertEqual(matrix.shape, (3, 3))
        self.assertEqual(int(matrix.sum()), 30)

    def test_independent_clustering(self):
        X = load_iris().data
        clusterer = make_pipeline(
            StandardScaler(), KMeans(n_clusters=3, n_init=10, random_state=42)
        )
        labels = clusterer.fit_predict(X)
        scaled = clusterer.named_steps["standardscaler"].transform(X)
        score = silhouette_score(scaled, labels)
        self.assertEqual(len(set(labels)), 3)
        self.assertTrue(-1 <= score <= 1)
        print(f"independent silhouette: {score:.3f}")


if __name__ == "__main__":
    unittest.main()
