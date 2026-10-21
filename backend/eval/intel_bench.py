"""F14: the same scikit-learn workloads on stock scikit-learn and on Intel Extension for Scikit-learn
(sklearnex, oneDAL). KMeans is what camp placement uses for demand areas (USE_INTEL_SKLEARN=true
switches the app to the Intel path); logistic regression is the learned donor-ranker upgrade.
Optional: pip install -r requirements-extras.txt"""
import platform
import statistics
import time


def _time(fn, repeats: int = 3) -> float:
    out = []
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000)
    return statistics.median(out)


def run() -> tuple[str, dict]:
    try:
        import numpy as np
        from sklearn.cluster import KMeans as SkKMeans
        from sklearn.linear_model import LogisticRegression as SkLR
        from sklearnex.cluster import KMeans as IntelKMeans
        from sklearnex.linear_model import LogisticRegression as IntelLR
    except ImportError as e:
        return f"Skipped: {e}. Install with `pip install -r requirements-extras.txt`.", {}
    rng = np.random.default_rng(0)
    centres = rng.uniform([28.3, 76.9], [28.9, 77.6], size=(12, 2))
    pts = np.vstack([c + rng.normal(0, 0.03, size=(25_000, 2)) for c in centres])  # 300k donor-like points
    X = rng.random((200_000, 6))
    y = (X @ np.array([2.4, 1.8, 0.9, 0.8, 0.3, 0.1]) + rng.normal(0, 0.5, 200_000) > 3.0).astype(int)
    rows, metrics = [], {}
    for name, sk, intel in [
        ("KMeans k=8, 300k points (camp demand areas)", lambda: SkKMeans(8, n_init=3, random_state=0).fit(pts),
         lambda: IntelKMeans(8, n_init=3, random_state=0).fit(pts)),
        ("LogisticRegression, 200k x 6 (donor ranker)", lambda: SkLR(max_iter=200).fit(X, y), lambda: IntelLR(max_iter=200).fit(X, y)),
    ]:
        a, b = _time(sk), _time(intel)
        rows.append([name, f"{a:.0f} ms", f"{b:.0f} ms", f"{a / b:.1f}x"])
        metrics[name] = {"sklearn_ms": round(a), "sklearnex_ms": round(b)}
    cpu = platform.processor() or platform.machine()
    head = "| workload | scikit-learn | Intel sklearnex | speed-up |\n| --- | --- | --- | --- |\n"
    return (f"Median of 3 runs on this machine ({cpu}).\n\n" + head + "\n".join("| " + " | ".join(r) + " |" for r in rows)), metrics
