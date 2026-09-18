from api.routes.ml import router


def test_ml_training_route_is_registered():
    paths = {route.path for route in router.routes}
    assert "/ml/train" in paths