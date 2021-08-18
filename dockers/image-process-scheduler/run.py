from improsch.pipeline import Preprocessor
import yaml
import os
from celery import Celery
from celery.result import allow_join_result


def parse_config(config_path: str):
    with open(config_path) as file:
        config: dict = yaml.safe_load(file)

    return config


IN_DOCKER = os.environ.get("DOCKER_USE", False)
STORAGE_PATH = os.environ.get("STORAGE_PATH", None)
REDIS_PASSW = os.getenv('REDIS_PASSWORD')
if IN_DOCKER:
    app = Celery(
        'improsch',
        backend=f'redis://:{REDIS_PASSW}@redis:6379/1',
        broker=f'redis://:{REDIS_PASSW}@redis:6379/1'
    )
    app_scoring = Celery(
        'score',
        backend=f'redis://:{REDIS_PASSW}@redis:6379/2',
        broker=f'redis://:{REDIS_PASSW}@redis:6379/2'
    )
else:
    app = Celery('improsch', backend='redis://localhost:6379/1', broker='redis://localhost:6379/1')
    app_scoring = Celery('score', backend='redis://localhost:6379/2', broker='redis://localhost:6379/2')
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

    if request.get('is_scoring'):
        with allow_join_result():
            scoring_task = app_scoring.send_task(
                'main.process',
                args=(request['scoring_model'], request['directory'], request['is_resize'])
            )
            scoring_task.wait(timeout=None, interval=0.5)

            print('STATE:', scoring_task.state)
            print(scoring_task.result)

            if scoring_task.state == 'SUCCESS':
                result['scoring'] = scoring_task.result
            else:
                result['scoring'] = 'ERROR'

    return result
