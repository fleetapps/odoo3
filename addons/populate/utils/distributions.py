from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from random import Random
from typing import TYPE_CHECKING

from odoo import _

if TYPE_CHECKING:
    from collections.abc import Callable

DistributionKwargs = Mapping[str, float]


class Distribution(ABC):
    """Base class for statistical distributions."""

    def __init__(self, rng: Random | None = None, **kwargs):
        if rng is None:
            rng = Random()

        self.rng = rng

    def __eq__(self, other):
        if not isinstance(self, type(other)):
            return False

        return hash(self) == hash(other)

    def __hash__(self):
        return hash(tuple(sorted((k, v) for k, v in self.__dict__.items() if k != 'rng')))

    @staticmethod
    def _parse(distribution_def: str) -> tuple[str, DistributionKwargs]:
        """
        Parse distribution string like "normal(mean=50.0, std=10.0)"

        Example:
            >>> Distribution._parse("normal(mean=50, std=10)")
            ('normal', {'mean': 50.0, 'std': 10.0})
        """
        pattern = r'^(\w+)\((.*)\)$'
        match = re.match(pattern, distribution_def.strip())

        if not match:
            raise ValueError(_(
                "Invalid distribution format: '%(distribution_def)s'. "
                "Expected format: 'name(param1=value1, param2=value2)', e.g. 'normal(mean=50, std=10)'.",
                distribution_def=distribution_def,
            ))

        dist_name = match.group(1)
        params_str = match.group(2)

        params = {}
        if params_str.strip():
            for param in params_str.split(','):
                key, value = param.split('=')
                key = key.strip()
                value = value.strip()
                params[key] = float(value)

        return dist_name, params

    @staticmethod
    def from_definition(distribution_def, partial=False) -> Distribution | Callable[[Random], Distribution]:
        name, params = Distribution._parse(distribution_def)
        distribution_class = DISTRIBUTIONS[name]
        if partial:
            def distribution_factory(rng: Random | None = None) -> Distribution:
                return distribution_class(rng=rng, **params)

            return distribution_factory

        return distribution_class(**params)

    @abstractmethod
    def sample(self) -> float:
        """Get a single sample from the distribution."""
        ...

    @abstractmethod
    def normalize(self, value: float) -> float:
        """
        Normalize a value to the range [0, 1] using the distribution's properties.

        :param value: The value to normalize.
        :return: The normalized value in the range [0, 1].
        """
        ...

    def sample_discrete(self, start: int, end: int) -> int:
        """
        Sample an integer between [start, end].

        :param start: Start of the range (inclusive)
        :param end: End of the range (inclusive)
        :return: An integer in [start, end]
        """
        if start >= end:
            raise ValueError(_(
                "sample_discrete requires start < end, got start=%(start)s, end=%(end)s.",
                start=start, end=end,
            ))

        sample = self.normalize(self.sample())
        range = end - start + 1
        return start + min(math.floor(sample * range), range - 1)

    def sample_continuous(self, start: float, end: float) -> float:
        """
        Sample a value in the continuous range [start, end].

        :param start: Start of the range (inclusive)
        :param end: End of the range (inclusive)
        :return: A value in [start, end]
        """
        if start >= end:
            raise ValueError(_(
                "sample_continuous requires start <= end, got start=%(start)s, end=%(end)s.",
                start=start, end=end,
            ))

        sample = self.normalize(self.sample())
        return start + (sample * (end - start))


class NormalDistribution(Distribution):
    """
    Normal (Gaussian) distribution.

    The classic bell curve. Values cluster around the mean, with fewer values further away.

    When to use:
    - Modeling natural variations (heights, measurement errors, response times)
    - When you expect most values near the average with symmetrical spread
    - Real-world phenomena that result from many small random factors

    Example: User response times, server latency with consistent behavior
    """

    def __init__(self, mean: float, std: float, **kwargs):
        """
        :param mean: Mean of the distribution
        :param std: Standard deviation (must be > 0)
        """
        super().__init__(**kwargs)
        if std <= 0:
            raise ValueError(_("Standard deviation must be positive, get %s instead.", std))

        self.mean = mean
        self.std = std

    def sample(self):
        return self.rng.gauss(self.mean, self.std)

    def normalize(self, value):
        z = (value - self.mean) / self.std
        # Use an error function approximation
        return NormalDistribution.cdf(z)

    @staticmethod
    def cdf(x: float) -> float:
        """
        Approximate the cumulative distribution function of standard normal.

        Uses the error function approximation. Accurate to about 7 decimal places.
        Based on Abramowitz and Stegun approximation.
        (ref: Handbook of Mathematical Functions, formula 7.1.26)
        """
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911

        sign = 1 if x >= 0 else -1
        x = abs(x) / math.sqrt(2.0)

        # A&S formula 7.1.26
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

        return 0.5 * (1.0 + sign * y)


class UniformDistribution(Distribution):
    """
    Uniform distribution.

    Every value in the range has an equal probability. Completely flat distribution.

    When to use:
    - Random selection where all options are equally likely
    - When you have no reason to prefer any value over another in a range

    Example: Random color picker, dice rolls, shuffling items, selecting random test data
    """

    def __init__(self, min: float, max: float, **kwargs):
        """
        :param min: Minimum value
        :param max: Maximum value (must be > min)
        """
        super().__init__(**kwargs)
        if min >= max:
            raise ValueError(_(
                "`min` must be less than `max`, got min=%(min)s, max=%(max)s instead.",
                min=min, max=max,
            ))

        self.min = min
        self.max = max

    def sample(self):
        return self.rng.uniform(self.min, self.max)

    def normalize(self, value):
        return UniformDistribution.cdf(value, self.min, self.max)

    @staticmethod
    def cdf(x: float, min: float, max: float) -> float:
        if x <= min:
            return 0.0
        if x >= max:
            return 1.0
        return (x - min) / (max - min)


class ExponentialDistribution(Distribution):
    """
    Exponential distribution.

    Models time between events. Many small values, few large ones. Heavily skewed right.

    When to use:
    - Time until something happens (waiting times, failures)
    - Intervals between independent events

    Example: Time between customer arrivals, time until next system failure, session durations
    """

    def __init__(self, rate: float, **kwargs):
        """
        :param rate: Rate parameter λ (must be > 0)
        """
        super().__init__(**kwargs)
        if rate <= 0:
            raise ValueError(_("Rate must be positive, got %s instead.", rate))

        self.rate = rate

    def sample(self):
        return self.rng.expovariate(self.rate)

    def normalize(self, value):
        if value < 0:
            return 0.0
        return ExponentialDistribution.cdf(value, self.rate)

    @staticmethod
    def cdf(x: float, rate: float) -> float:
        return 1.0 - math.exp(-rate * x)


class BetaDistribution(Distribution):
    """
    Beta distribution.

    Bounded between 0 and 1. Shape varies dramatically based on parameters - can be U-shaped, bell-shaped, or skewed.

    When to use:
    - Modeling percentages, probabilities, or proportions
    - When values must stay within [0, 1] range
    - A/B testing and conversion rates

    Example: Click-through rates, success probabilities, confidence scores
    """

    def __init__(self, alpha: float, beta: float, **kwargs):
        """
        :param alpha: Shape parameter α (must be > 0)
        :param beta: Shape parameter β (must be > 0)
        """  # noqa: RUF002
        super().__init__(**kwargs)
        if alpha <= 0:
            raise ValueError(_("Alpha must be positive, got %s instead.", alpha))
        if beta <= 0:
            raise ValueError(_("Beta must be positive, got %s instead.", beta))

        self.alpha = alpha
        self.beta = beta

    def sample(self):
        return self.rng.betavariate(self.alpha, self.beta)

    def normalize(self, value):
        # Already in [0, 1], just clamp
        return max(0.0, min(1.0, value))


class PoissonDistribution(Distribution):
    """
    Poisson distribution (discrete).

    Counts how many events occur in a fixed interval. Discrete (whole numbers only).

    When to use:
    - Counting rare events in a fixed time/space
    - Events that occur independently at a constant average rate

    Example: Number of bugs per 1000 lines of code, API requests per minute, emails received per hour
    """

    def __init__(self, lam: float, **kwargs):
        """
        :param lam: Average rate λ (must be > 0)
        """
        super().__init__(**kwargs)
        if lam <= 0:
            raise ValueError(_("Lambda must be positive, got %s instead.", lam))

        self.lam = lam

    def sample(self):
        # Knuth's algorithm for Poisson sampling
        L = math.e ** (-self.lam)  # e^(-lambda)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= self.rng.random()
        return k - 1

    def normalize(self, value):
        # For small lambda, use exact Poisson's CDF formula
        if self.lam < 10:
            return PoissonDistribution.cdf(value, self.lam)

        # Normal approximation: Poisson(λ) ≈ Normal(λ, λ)
        # With continuity correction: P(X ≤ k) ≈ Φ((k + 0.5 - λ) / √λ)
        z = (value + 0.5 - self.lam) / math.sqrt(self.lam)
        return NormalDistribution.cdf(z)

    @staticmethod
    def cdf(x: float, lam: float) -> float:
        k = math.floor(x)
        if k < 0:
            return 0.0

        cdf = 0.0
        for i in range(k + 1):
            # We use exp and log to prevent overflow with large factorials/powers
            cdf += math.exp(-lam + math.log(lam) * i - math.lgamma(i + 1))
        return cdf


class TriangularDistribution(Distribution):
    """
    Triangular distribution.

    Simple distribution with a min, max, and most likely value (mode). Linear increase to the peak, then linear decrease.

    When to use:
    - When you only know min/max/most-likely values (common in project estimation)
    - Quick approximations without detailed data

    Example: Task duration estimates, risk modeling, cost estimates when you have "best case, worst case, most likely"
    """

    def __init__(self, min: float, max: float, mode: float, **kwargs):
        """
        :param min: Minimum value
        :param max: Maximum value
        :param mode: Most likely value (peak of distribution)
        """
        super().__init__(**kwargs)
        if not (min <= mode <= max):
            raise ValueError(_(
                "`mode` must be between `min` and `max`, got min=%(min)s, max=%(max)s, mode=%(mode)s instead.",
                min=min, max=max, mode=mode,
            ))

        self.min = min
        self.max = max
        self.mode = mode

    def sample(self):
        return self.rng.triangular(self.min, self.max, self.mode)

    def normalize(self, value):
        return TriangularDistribution.cdf(value, self.min, self.max, self.mode)

    @staticmethod
    def cdf(x: float, min: float, max: float, mode: float) -> float:
        if x <= min:
            return 0.0
        if x >= max:
            return 1.0
        if x <= mode:
            return ((x - min) ** 2) / ((max - min) * (mode - min))

        return 1.0 - ((max - x) ** 2) / ((max - min) * (max - mode))


DISTRIBUTIONS = {
    'normal': NormalDistribution,
    'uniform': UniformDistribution,
    'exponential': ExponentialDistribution,
    'beta': BetaDistribution,
    'poisson': PoissonDistribution,
    'triangular': TriangularDistribution,
}
