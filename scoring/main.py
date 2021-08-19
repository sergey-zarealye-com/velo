import os
from celery import Celery
from models import Register, TorchModel
from datasets import ImageDataLoader


MODELS_STORAGE = os.getenv("MODELS_STORAGE")
assert MODELS_STORAGE
IN_DOCKER = os.getenv("IN_DOCKER")
REDIS_PASSW = os.getenv("REDIS_PASSWORD")
assert REDIS_PASSW

if IN_DOCKER:
    app = Celery(
        'score',
        backend=f'redis://:{REDIS_PASSW}@redis:6379/2',
        broker=f'redis://:{REDIS_PASSW}@redis:6379/2'
    )
else:
    app = Celery('score', backend='redis://localhost:6379/2', broker='redis://localhost:6379/2')
app.autodiscover_tasks(force=True)


register = Register()
register.find_models(MODELS_STORAGE, TorchModel)


@app.task(bind=True)
def process(self, model_name: str, directory: str, has_images_resized: bool):
    print(directory)
    directory = directory.split('/')  # type: ignore
    print(directory)
    if directory[-1] == '/':
        directory = directory[-2]
    else:
        directory = directory[-1]
    print(directory)
    directory = os.path.join('/storage', directory)
    print(directory)

    print(f'\tReading in {directory}')
    filenames = []
    for root, _, files in os.walk(directory):
        filepaths = list(map(lambda x: os.path.join(root, x), files))
        filenames.extend(filepaths)
    print(f'\tCount of images: {len(filenames)}')

    internal_result = []
    chunk_size = 500
    print("Count of images:", len(filenames))
    for i in range(0, len(filenames), chunk_size):
        print("\tChunk:", i)
        dataloader = ImageDataLoader(filenames[i:i+chunk_size], 64, not has_images_resized)
        result = register.process(model_name, dataloader, dataloader.filepaths)
        internal_result.extend(result)

    return internal_result


@app.task
def get_models():
    return register.get_models_info()

