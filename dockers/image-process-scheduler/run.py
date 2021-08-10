from improsch.pipeline import Preprocessor
import yaml
import os
from celery import Celery


def parse_config(config_path: str):
    with open(config_path) as file:
        config: dict = yaml.safe_load(file)

    return config


IN_DOCKER = os.environ.get("DOCKER_USE", False)
STORAGE_PATH = os.environ.get("STORAGE_PATH", None)
if IN_DOCKER:
    app = Celery('improsch', backend='redis://redis:6379/0', broker='redis://redis:6379/0')
else:
    app = Celery('improsch', backend='redis://localhost:6379/0', broker='redis://localhost:6379/0')
app.autodiscover_tasks(force=True)


config = parse_config('config.yml')
processor = Preprocessor(
    storage_path=config['storage_path'],
    saving_pool_size=config['saving_pool_size'],
    dedup_batch_size=config['dedup_batch_size'],
    dedup_index_path=config['dedup_index_path']
)


@app.task(bind=True)
def process(self, request: dict):
    print('\tGot request:')
    print(request)

    if not request.get('id'):
        return {'error': 'request has no id reqquired field'}

    if request.get('directory'):
        request["directory"] = os.path.join(config['storage_path'], request["directory"])
        print("\tDirectory:\t", request["directory"])
    result = processor.preprocessing(request)

    if request.get('label_ds') is not None:
        result['label_ds'] = request['label_ds']

    if request.get('selected_ds') is not None:
        result['selected_ds'] = request['selected_ds']

    result['id'] = request['id']

    return result
