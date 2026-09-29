"""Fixed, untrained forward-pass example. Not a real pass-probability model."""
import numpy as np

X = np.array([[2.0, 60.0], [5.0, 75.0], [8.0, 90.0]])
W = np.array([[0.4], [0.03]])
b = np.array([-3.0])
z = X @ W + b

# Stable sigmoid; also avoids overflow for large negative inputs.
scores = np.exp(-np.logaddexp(0.0, -z))
print("X, W, z shapes:", X.shape, W.shape, z.shape)
print("z:", np.round(z.ravel(), 3))
print("sigmoid:", np.round(scores.ravel(), 3))

assert z.shape == (3, 1)
assert np.allclose(z.ravel(), [-0.4, 1.25, 2.9])
assert np.allclose(np.round(scores.ravel(), 3), [0.401, 0.777, 0.948])
print("checks: PASS")
