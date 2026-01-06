from odoo.tests import TransactionCase

from odoo.addons.populate.utils.distributions import (
    BetaDistribution,
    Distribution,
    ExponentialDistribution,
    NormalDistribution,
    PoissonDistribution,
    TriangularDistribution,
    UniformDistribution,
)


class TestDistributionParsing(TransactionCase):

    def test_parse_normal_distribution(self):
        name, params = Distribution._parse("normal(mean=50.0, std=10.0)")
        self.assertEqual(name, 'normal')
        self.assertEqual(params, {'mean': 50.0, 'std': 10.0})

    def test_parse_uniform_distribution(self):
        name, params = Distribution._parse("uniform()")
        self.assertEqual(name, 'uniform')
        self.assertEqual(params, {})

    def test_parse_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            Distribution._parse("invalid_format")

    def test_from_definition(self):
        dist = Distribution.from_definition("normal(mean=50, std=10)")
        self.assertIsInstance(dist, NormalDistribution)
        self.assertEqual(dist.mean, 50.0)
        self.assertEqual(dist.std, 10.0)


class TestNormalDistribution(TransactionCase):

    def test_sample(self):
        dist = NormalDistribution(mean=50.0, std=10.0)
        samples = [dist.sample() for _ in range(100)]
        self.assertTrue(all(isinstance(s, (int, float)) for s in samples))

    def test_normalize(self):
        dist = NormalDistribution(mean=50.0, std=10.0)
        normalized = dist.normalize(50.0)
        self.assertIsInstance(normalized, float)
        self.assertGreaterEqual(normalized, 0.0)
        self.assertLessEqual(normalized, 1.0)

    def test_sample_discrete(self):
        dist = NormalDistribution(mean=50.0, std=10.0)
        samples = [dist.sample_discrete(start=1, end=100) for _ in range(50)]
        self.assertTrue(all(isinstance(s, int) for s in samples))
        self.assertTrue(all(1 <= s <= 100 for s in samples))

    def test_equality(self):
        dist1 = NormalDistribution(mean=50.0, std=10.0)
        dist2 = NormalDistribution(mean=50.0, std=10.0)
        dist3 = NormalDistribution(mean=40.0, std=10.0)
        self.assertEqual(dist1, dist2)
        self.assertNotEqual(dist1, dist3)

    def test_hash(self):
        dist1 = NormalDistribution(mean=50.0, std=10.0)
        dist2 = NormalDistribution(mean=50.0, std=10.0)
        self.assertEqual(hash(dist1), hash(dist2))


class TestUniformDistribution(TransactionCase):

    def test_sample(self):
        dist = UniformDistribution(0, 1)
        samples = [dist.sample() for _ in range(100)]
        self.assertTrue(all(isinstance(s, float) for s in samples))
        self.assertTrue(all(0.0 <= s <= 1.0 for s in samples))

    def test_normalize(self):
        dist = UniformDistribution(0, 1)
        normalized = dist.normalize(0.5)
        self.assertEqual(normalized, 0.5)


class TestExponentialDistribution(TransactionCase):

    def test_sample(self):
        dist = ExponentialDistribution(rate=1.0)
        samples = [dist.sample() for _ in range(100)]
        self.assertTrue(all(isinstance(s, float) for s in samples))
        self.assertTrue(all(s >= 0.0 for s in samples))

    def test_normalize(self):
        dist = ExponentialDistribution(rate=1.0)
        normalized = dist.normalize(1.0)
        self.assertIsInstance(normalized, float)
        self.assertGreaterEqual(normalized, 0.0)
        self.assertLessEqual(normalized, 1.0)


class TestBetaDistribution(TransactionCase):

    def test_sample(self):
        dist = BetaDistribution(alpha=2.0, beta=5.0)
        samples = [dist.sample() for _ in range(100)]
        self.assertTrue(all(isinstance(s, float) for s in samples))
        self.assertTrue(all(0.0 <= s <= 1.0 for s in samples))

    def test_normalize(self):
        dist = BetaDistribution(alpha=2.0, beta=5.0)
        normalized = dist.normalize(0.3)
        self.assertIsInstance(normalized, float)
        self.assertGreaterEqual(normalized, 0.0)
        self.assertLessEqual(normalized, 1.0)


class TestTriangularDistribution(TransactionCase):

    def test_sample(self):
        dist = TriangularDistribution(min=0.0, max=10.0, mode=5.0)
        samples = [dist.sample() for _ in range(100)]
        self.assertTrue(all(isinstance(s, float) for s in samples))
        self.assertTrue(all(0.0 <= s <= 10.0 for s in samples))

    def test_normalize(self):
        dist = TriangularDistribution(min=0.0, max=10.0, mode=5.0)
        normalized = dist.normalize(5.0)
        self.assertIsInstance(normalized, float)
        self.assertGreaterEqual(normalized, 0.0)
        self.assertLessEqual(normalized, 1.0)


class TestPoissonDistribution(TransactionCase):

    def test_sample(self):
        dist = PoissonDistribution(lam=5.0)
        samples = [dist.sample() for _ in range(100)]
        self.assertTrue(all(isinstance(s, int) for s in samples))
        self.assertTrue(all(s >= 0 for s in samples))

    def test_normalize(self):
        dist = PoissonDistribution(lam=5.0)
        normalized = dist.normalize(5)
        self.assertIsInstance(normalized, float)
        self.assertGreaterEqual(normalized, 0.0)
        self.assertLessEqual(normalized, 1.0)
