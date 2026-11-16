"""Statistical noise generators ensuring signal dominates noise."""

import random
from collections.abc import Sequence


class StochasticNoiseEngine:
    """Provides bounded statistical perturbations for continuous and discrete metrics."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def gaussian_multiplier(
        self, mean: float = 1.0, std_dev: float = 0.04, min_val: float = 0.85, max_val: float = 1.15
    ) -> float:
        """Generates bounded Gaussian multiplier around mean."""
        val = self.rng.gauss(mean, std_dev)
        return max(min_val, min(max_val, val))

    def additive_gaussian(self, base_val: float, std_dev: float, min_val: float = 0.0) -> float:
        """Adds Gaussian perturbation with a floor."""
        pert = self.rng.gauss(0.0, std_dev)
        return max(min_val, base_val + pert)

    def lognormal_order_value(self, mean_target: float = 85.0, sigma: float = 0.55) -> float:
        """Generates realistic order dollar amounts using log-normal distribution.

        Produces many common orders ($30-$90), fewer expensive orders ($120-$300),
        and rare high-value purchases ($400-$750).
        """
        # For lognormal: E[X] = exp(mu + sigma^2 / 2) => mu = ln(mean_target) - sigma^2 / 2
        import math

        mu = math.log(mean_target) - (sigma**2) / 2
        val = self.rng.lognormvariate(mu, sigma)
        # Guard against zero or extreme tail outliers
        return round(max(9.99, min(850.0, val)), 2)

    def poisson_count(self, lam: float) -> int:
        """Simulates Poisson random count for arrival processes (e.g. ticket counts, complaints)."""
        import math

        if lam <= 0:
            return 0
        if lam > 100:
            # Gaussian approximation for large lambda
            val = int(round(self.rng.gauss(lam, math.sqrt(lam))))
            return max(0, val)

        # Knuth algorithm for small lambda
        limit = math.exp(-lam)
        prod = self.rng.random()
        count = 0
        while prod > limit:
            count += 1
            prod *= self.rng.random()
        return count

    def choice(self, seq: Sequence):
        """Picks a random item from a sequence."""
        return self.rng.choice(seq)

    def uniform(self, a: float, b: float) -> float:
        """Uniform random float between a and b."""
        return self.rng.uniform(a, b)

    def random(self) -> float:
        """Uniform random float between 0.0 and 1.0."""
        return self.rng.random()
