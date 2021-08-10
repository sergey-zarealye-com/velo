from typing import Dict
from .model import ClassificationModel


class Register:
    def __init__(self) -> None:
        self.models: Dict[str, ClassificationModel] = {}

    def register(self, model, rewrite: bool = False):
        assert model.name not in self.models or rewrite, ValueError(
            f"{model.name} name has register already. Define rewirte=True to rewrite it."
        )

        self.models[model.name] = model

    def process(self, model_name, *args):
        return self.models[model_name].score(*args)

    def get_models_info(self):
        return list(self.models.keys())
