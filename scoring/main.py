import os
from celery import Celery
from models import EfficientModel, Register
from datasets import ImageDataLoader


IN_DOCKER = os.getenv("IN_DOCKER")
if IN_DOCKER:
    app = Celery('score', backend='redis://rabbit:6379/0', broker='redis://rabbit:6379/0')
else:
    app = Celery('score', backend='redis://localhost:6379/0', broker='redis://localhost:6379/0')
app.autodiscover_tasks(force=True)

CHECKPOINT = '/storage1/mrowl/efficient.pth'
model = EfficientModel('eff-b3', CHECKPOINT, 'cpu', {})
register = Register()
register.register(model)


@app.task(bind=True)
def process(self, model_name: str, directory: str, has_images_resized: bool):
    dataloader = ImageDataLoader(directory, 64, not has_images_resized)
    result = register.process(model_name, dataloader, dataloader.filepaths)

    return result


@app.task
def get_models():
    return register.get_models_info()
