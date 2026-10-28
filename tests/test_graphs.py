import os
import unittest
from matplotlib.figure import Figure
from results.generate_graphs import build_figure, CHART_CONFIGS, load_benchmark_data


class TestGraphGeneration(unittest.TestCase):
    """
    Unit and integration tests for benchmark graph generation and configuration.
    Verifies data integrity, figure structure, annotations, and formatting.
    """

    def setUp(self):
        self.csv_path = os.path.join(
            os.path.dirname(__file__), "..", "results", "workload_results.csv"
        )
        self.assertTrue(os.path.exists(self.csv_path), "Benchmark CSV file missing")

    def test_load_benchmark_data(self):
        labels, data = load_benchmark_data(self.csv_path)
        self.assertEqual(len(labels), 7)
        self.assertIn("Normal Avg Waiting", data)
        self.assertIn("StarveGuard Avg Waiting", data)
        self.assertIn("Normal Avg Response", data)
        self.assertIn("StarveGuard Avg Response", data)
        self.assertIn("Normal Fairness", data)
        self.assertIn("StarveGuard Fairness", data)
        for key in data:
            self.assertEqual(len(data[key]), 7)

    def test_build_figure_waiting(self):
        fig = build_figure("waiting", csv_path=self.csv_path)
        self.assertIsInstance(fig, Figure)
        ax = fig.axes[0]
        self.assertEqual(ax.get_title(), CHART_CONFIGS["waiting"]["title"])
        self.assertEqual(ax.get_ylabel(), CHART_CONFIGS["waiting"]["ylabel"])
        # 2 bar containers (Normal Priority and StarveGuard)
        self.assertEqual(len(ax.containers), 2)
        # 7 bars per container
        self.assertEqual(len(ax.containers[0]), 7)
        self.assertEqual(len(ax.containers[1]), 7)

    def test_build_figure_response(self):
        fig = build_figure("response", csv_path=self.csv_path)
        self.assertIsInstance(fig, Figure)
        ax = fig.axes[0]
        self.assertEqual(ax.get_title(), CHART_CONFIGS["response"]["title"])
        self.assertEqual(ax.get_ylabel(), CHART_CONFIGS["response"]["ylabel"])
        self.assertEqual(len(ax.containers), 2)

    def test_build_figure_fairness(self):
        fig = build_figure("fairness", csv_path=self.csv_path)
        self.assertIsInstance(fig, Figure)
        ax = fig.axes[0]
        self.assertEqual(ax.get_title(), CHART_CONFIGS["fairness"]["title"])
        self.assertEqual(ax.get_ylabel(), CHART_CONFIGS["fairness"]["ylabel"])
        self.assertEqual(len(ax.containers), 2)
        # Fairness chart has fixed y-limits allowing headroom for 1.000 values
        ylim = ax.get_ylim()
        self.assertGreaterEqual(ylim[0], 0.0)
        self.assertGreater(ylim[1], 1.0)

    def test_invalid_chart_type(self):
        with self.assertRaises(ValueError):
            build_figure("non_existent_chart_type", csv_path=self.csv_path)


if __name__ == "__main__":
    unittest.main()
