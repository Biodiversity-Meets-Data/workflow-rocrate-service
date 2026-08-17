from unittest.mock import Mock, patch

from app.workflow_engines.lifewatch_engine import LifeWatchEngine


def test_get_workflow():
    fake_workflow = {
        "metadata": {
            "name": "test-workflow",
        },
        "spec": {},
        "status": {
            "phase": "Succeeded",
        },
    }

    engine = LifeWatchEngine()

    with patch("app.workflow_engines.lifewatch_engine.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = fake_workflow
        mock_response.raise_for_status.return_value = None

        mock_get.return_value = mock_response

        result = engine.get_workflow(
            workflow_id="test-workflow",
            token="fake-token",
        )

    assert result == fake_workflow

    mock_get.assert_called_once_with(
        "https://workflows-demo.bmd.lifewatch.dev/v1/test-workflow/status",
        headers={
            "Authorization": "Bearer fake-token",
        },
    )
