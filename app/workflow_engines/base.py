from abc import ABC, abstractmethod

from app.argo.models import Annotations, Author, Workflow


class WorkflowEngine(ABC):
    name: str
    annotations_prefix: str
    labels_prefix: str = "workflows.argoproj.io"
    base_url: str

    @abstractmethod
    def authenticate(self, token: str) -> None:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @abstractmethod
    def get_workflow(self, workflow_id: str, **kwargs) -> Workflow:
        pass

    @abstractmethod
    def submit_workflow(self, workflow: Workflow, token: str) -> str:
        pass

    @abstractmethod
    def get_artifact_download_url(self, artifact_key: str) -> str:
        pass

    def parse_workflow(self, data: dict) -> Workflow:
        annotations = data["metadata"].get("annotations", {})
        prefix = self.annotations_prefix

        authors = [
            Author(name=name.strip(), id=id.strip())
            for name, id in zip(
                annotations[f"{prefix}/author_names"].split(","),
                annotations[f"{prefix}/author_ids"].split(","),
                strict=True,
            )
        ]

        workflow_annotations = Annotations(
            authors=authors,
            license=annotations[f"{prefix}/license"],
            keywords=[
                keyword.strip()
                for keyword in annotations[f"{prefix}/keywords"].split(",")
            ],
            description=annotations["workflows.argoproj.io/description"],
            title=annotations["workflows.argoproj.io/title"],
        )

        metadata = data["metadata"].copy()
        metadata["annotations"] = workflow_annotations

        data = data.copy()
        data["metadata"] = metadata

        return Workflow.model_validate(data, by_name=True)

    def serialize_workflow(self, workflow: Workflow, snake_case: bool = False) -> dict:

        data = workflow.model_dump(
            exclude_none=True,
            by_alias=snake_case,
        )

        annotations = data["metadata"]["annotations"]

        # Replace normalized annotations with Argo annotation keys
        data["metadata"]["annotations"] = {
            # **{key: value for key, value in annotations.items() if "/" in key},
            f"{self.annotations_prefix}/author_names": ",".join(
                [author["name"] for author in annotations["authors"]]
            ),
            f"{self.annotations_prefix}/author_ids": ",".join(
                [author["id"] for author in annotations["authors"]]
            ),
            f"{self.annotations_prefix}/keywords": ", ".join(annotations["keywords"]),
            f"{self.annotations_prefix}/license": annotations["license"],
            "workflows.argoproj.io/description": annotations["description"],
            "workflows.argoproj.io/title": annotations["title"],
        }

        return data
