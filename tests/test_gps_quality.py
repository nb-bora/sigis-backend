"""Tests GPS quality scoring."""


from domain.shared.gps_quality import GpsScore, score_gps_accuracy


class TestGpsScoring:
    """GPS accuracy scoring pour détection fraude."""

    def test_excellent_accuracy(self):
        """Accuracy ≤ 5m = EXCELLENT."""
        assert score_gps_accuracy(3.0) == GpsScore.EXCELLENT
        assert score_gps_accuracy(5.0) == GpsScore.EXCELLENT

    def test_good_accuracy(self):
        """Accuracy 5–25m = GOOD."""
        assert score_gps_accuracy(10.0) == GpsScore.GOOD
        assert score_gps_accuracy(25.0) == GpsScore.GOOD

    def test_fair_accuracy(self):
        """Accuracy 25–100m = FAIR."""
        assert score_gps_accuracy(50.0) == GpsScore.FAIR
        assert score_gps_accuracy(100.0) == GpsScore.FAIR

    def test_poor_accuracy(self):
        """Accuracy > 100m = POOR."""
        assert score_gps_accuracy(150.0) == GpsScore.POOR
        assert score_gps_accuracy(500.0) == GpsScore.POOR

    def test_zero_accuracy(self):
        """Accuracy 0 = EXCELLENT."""
        assert score_gps_accuracy(0.0) == GpsScore.EXCELLENT

    def test_none_accuracy_defaults_fair(self):
        """None accuracy defaults to FAIR."""
        assert score_gps_accuracy(None) == GpsScore.FAIR

    def test_boundary_excellent_good(self):
        """Boundary 5m."""
        assert score_gps_accuracy(5.0) == GpsScore.EXCELLENT
        assert score_gps_accuracy(5.1) == GpsScore.GOOD

    def test_boundary_good_fair(self):
        """Boundary 25m."""
        assert score_gps_accuracy(25.0) == GpsScore.GOOD
        assert score_gps_accuracy(25.1) == GpsScore.FAIR

    def test_boundary_fair_poor(self):
        """Boundary 100m."""
        assert score_gps_accuracy(100.0) == GpsScore.FAIR
        assert score_gps_accuracy(100.1) == GpsScore.POOR


class TestGpsQualityScenarios:
    """Scénarios réalistes de qualité GPS."""

    def test_gps_excellent_indoor_weak(self):
        """Indoor avec weak signal mais bon accuracy = EXCELLENT."""
        # Cas rare mais possible avec assisted GPS
        assert score_gps_accuracy(3.0) == GpsScore.EXCELLENT

    def test_gps_poor_rural_area(self):
        """Zone rurale, GPS débile."""
        # Tropique, signal débile
        assert score_gps_accuracy(250.0) == GpsScore.POOR

    def test_gps_fair_urban(self):
        """Urbain classique, accuracy OK."""
        assert score_gps_accuracy(50.0) == GpsScore.FAIR

    def test_gps_good_with_agps(self):
        """Avec assisted GPS (aGPS)."""
        assert score_gps_accuracy(15.0) == GpsScore.GOOD
