from api.metrics import MetricsRegistry, metric_path


def test_metric_path_normalizes_dynamic_identifiers():
    assert metric_path("/api/status/12345678-1234-1234-1234-123456789abc") == "/api/status/:id"
    assert metric_path("/api/schema/42") == "/api/schema/:id"


def test_metrics_registry_renders_request_counters():
    metrics = MetricsRegistry()
    metrics.record("GET", "/ready", 200, 0.1)
    metrics.record("GET", "/ready", 503, 2.5)

    output = metrics.render()

    assert 'method="GET",path="/ready",status_class="2xx"' in output
    assert 'method="GET",path="/ready",status_class="5xx"' in output
    assert 'bucket="le_0_5"' in output
    assert 'bucket="gt_2"' in output