import json
from unittest.mock import Mock, patch

from app.settings import get_lifewatch_deployment
from app.workflow_engines.lifewatch_engine import LifeWatchEngine

lifewatch_engine_settings = get_lifewatch_deployment()


def test_get_workflow():
    ## this is just an initial implementation needs to be expanded with more comprehensive tests
    engine = LifeWatchEngine(
        base_url=lifewatch_engine_settings.base_url,
        annotations_prefix=lifewatch_engine_settings.annotations_prefix,
        labels_prefix=lifewatch_engine_settings.labels_prefix,
        api_endpoint=lifewatch_engine_settings.api_endpoint,
    )

    with open("tests/fixtures/successful_workflow.json") as f:
        workflow_fixture = json.load(f)

    with patch("app.workflow_engines.lifewatch_engine.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = workflow_fixture["status"]
        mock_response.raise_for_status.return_value = None

        mock_get.return_value = mock_response

        result = engine.get_workflow(
            workflow_id="test-workflow",
            token="fake-token",
        )

    assert result.metadata.name == "test-workflow"
    assert (
        result.metadata.annotations.title
        == workflow_fixture["metadata"]["annotations"]["workflows.argoproj.io/title"]
    )

    mock_get.assert_called_once_with(
        "https://workflows-demo.bmd.lifewatch.dev/v1/test-workflow/status",
        headers={
            "Authorization": "Bearer fake-token",
            "accept": "application/json",
        },
    )
