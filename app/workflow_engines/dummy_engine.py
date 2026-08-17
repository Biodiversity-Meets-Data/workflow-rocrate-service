from app.workflow_engines.base import WorkflowEngine


class DummyEngine(WorkflowEngine):
    name: str = "dummy"
    annotations_prefix: str = "dummy"
    base_url: str = f"http://localhost:8000/workflow-engines/{name}/workflows"

    def get_workflow(self, workflow_id: str, token: str) -> dict:
        return {
            "metadata": {
                "name": workflow_id,
                "annotations": {
                    f"{self.annotations_prefix}/author_names": "Lena Creator",
                    f"{self.annotations_prefix}/author_ids": "0000-0001-2345-6789",
                    f"{self.annotations_prefix}/keywords": "RO-Crate, test, workflow",
                    f"{self.annotations_prefix}/license": "CC-BY-4.0",
                    "workflows.argoproj.io/description": "A small workflow used to test RO-Crate generation",
                    "workflows.argoproj.io/last-seen-version": "550452",
                    "workflows.argoproj.io/pod-name-format": "v2",
                    "workflows.argoproj.io/title": "RO-Crate Test Workflow",
                },
            },
            "spec": {
                "workflowTemplateRef": {
                    "name": "dummy-template",
                },
            },
            "status": {
                "phase": "Succeeded",
                "storedWorkflowTemplateSpec": {
                    "templates": [],
                    "entrypoint": "",
                    "arguments": {},
                    "workflowMetadata": {},
                },
            },
        }

    def post_workflow(self, workflow_data: dict, token: str):
        pass
