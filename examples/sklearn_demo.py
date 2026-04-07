"""Minimal scikit-learn demo showcasing fargv's dataclass API.

Commands
--------
::

    python examples/sklearn_demo.py knn
    python examples/sklearn_demo.py knn --dataset=wine --n_neighbors=7
    python examples/sklearn_demo.py svm --C=0.5 --kernel=linear
    python examples/sklearn_demo.py rf  --n_estimators=200 --max_depth=3
    python examples/sklearn_demo.py logistic --dataset=digits --C=10.0
"""
import sys
from dataclasses import dataclass, field
import fargv


@dataclass
class Config:
    """Fit an sklearn classifier on a built-in dataset."""
    dataset: tuple = ("iris", "digits", "breast_cancer", "wine")
    "Dataset to load."
    test_size: float = 0.2
    "Fraction of samples reserved for testing."
    random_seed: int = 42
    "RNG seed."
    classifier: dict = field(default_factory=lambda: {
        "knn":      {"n_neighbors": 5},
        "svm":      {"C": 1.0, "kernel": ("rbf", "linear", "poly")},
        "rf":       {"n_estimators": 100, "max_depth": 5},
        "logistic": {"C": 1.0},
    })
    "Classifier subcommand."


_CLASSIFIERS = {"knn", "svm", "rf", "logistic"}
if not any(a in _CLASSIFIERS or a.startswith("--classifier=") for a in sys.argv[1:]):
    sys.argv.append("--help")

p, _ = fargv.parse(Config, subcommand_return_type="nested")

from sklearn import datasets as skds
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

loaders = {"iris": skds.load_iris, "digits": skds.load_digits,
           "breast_cancer": skds.load_breast_cancer, "wine": skds.load_wine}
X, y = loaders[p.dataset](return_X_y=True)
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=p.test_size, random_state=p.random_seed)
sc = StandardScaler().fit(X_tr)
X_tr, X_te = sc.transform(X_tr), sc.transform(X_te)

sub = p.classifier
if sub.name == "knn":
    from sklearn.neighbors import KNeighborsClassifier
    clf = KNeighborsClassifier(n_neighbors=sub.n_neighbors)
elif sub.name == "svm":
    from sklearn.svm import SVC
    clf = SVC(C=sub.C, kernel=sub.kernel)
elif sub.name == "rf":
    from sklearn.ensemble import RandomForestClassifier
    clf = RandomForestClassifier(n_estimators=sub.n_estimators, max_depth=sub.max_depth,
                                 random_state=p.random_seed)
elif sub.name == "logistic":
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(C=sub.C, random_state=p.random_seed, max_iter=1000)

clf.fit(X_tr, y_tr)
print(f"[{sub.name}] {p.dataset}  accuracy: {accuracy_score(y_te, clf.predict(X_te)):.3f}")
