from typing import Dict
import os
from .model import ClassificationModel


class Register:
    def __init__(self) -> None:
        self.models: Dict[str, ClassificationModel] = {}

    def find_models(self, storage_path: str, base_class):
        filenames = map(
            lambda x: os.path.join(storage_path, x),
            os.listdir(storage_path)
        )

        for filename in filenames:
            _, name = os.path.split(filename)
            self.models[name] = base_class(filename)

    def register(self, model, rewrite: bool = False):
        assert model.name not in self.models or rewrite, ValueError(
            f"{model.name} name has register already. Define rewirte=True to rewrite it."
        )

        self.models[model.name] = model

    def process(self, model_name, *args):
        self.models[model_name].load_model()
        return self.models[model_name].score(*args)

    def get_models_info(self):
        return list(self.models.keys())
