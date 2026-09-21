class AuthenticationError(Exception):
    """Custom exception for authentication errors."""


class WorkflowNotFoundError(Exception):
    """Custom exception for workflow not found errors."""


class WorkflowParsingError(Exception):
    """Custom exception for workflow parsing errors."""


class UpstreamWorkflowEngineError(Exception):
    """Custom exception for upstream workflow engine errors."""
