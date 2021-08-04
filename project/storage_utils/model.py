import os
from typing import NamedTuple


def build_model_prefix(model_id: str) -> str:
    return os.path.join('models', model_id)


def build_torchscript_model_path(model_id: str) -> str:
    return os.path.join(build_model_prefix(model_id), 'torchscript_model.pt')


def build_classes_file_path(model_id: str) -> str:
    return os.path.join(build_model_prefix(model_id), 'classes.json')


def upload_model_to_s3_component(
        s3_endpoint: str,
        model_bucket: str,
        model_path: str
) -> NamedTuple('UploadModelsOutput', [
    ('model_prefix', str),
    ('model_s3_uri', str),
    ('model_id', str)
]):
    import os
    import uuid
    import logging
    from typing import NamedTuple

    import boto3

    from utils import s3_utils
    from utils.model import build_model_prefix

    logging.basicConfig(level=logging.INFO)

    s3 = boto3.resource(
        service_name='s3',
        endpoint_url=s3_endpoint
    )

    bucket = s3_utils.create_bucket_if_not_exists(s3, model_bucket)

    model_id = str(uuid.uuid4())

    model_prefix = build_model_prefix(model_id)
    model_s3_uri = os.path.join('s3://', model_bucket, model_prefix)

    logging.info(f'Uploading... model to {model_s3_uri}')
    s3_utils.upload_dir_to_bucket(
        s3_bucket=bucket,
        local_dir=model_path,
        prefix=model_prefix
    )
    logging.info(f'Uploaded model to {model_s3_uri}')

    result_type = NamedTuple('UploadModelsOutput', [
        ('model_prefix', str),
        ('model_s3_uri', str),
        ('model_id', str)
    ])
    return result_type(
        model_prefix=model_prefix,
        model_s3_uri=model_s3_uri,
        model_id=model_id
    )


def download_trained_model_component(
        s3_endpoint: str,
        model_bucket: str,
        trained_model_id: str,
        save_path: str
) -> NamedTuple('DownloadTrainedModelOutput', [
    ('trained_model_path', str)
]):
    import boto3
    import logging
    from typing import NamedTuple

    from utils import s3_utils
    from utils.model import build_model_prefix

    logging.basicConfig(level=logging.INFO)

    s3 = boto3.resource(
        service_name='s3',
        endpoint_url=s3_endpoint
    )

    s3_utils.download_bucket_to_dir(
        s3_bucket=s3.Bucket(model_bucket),
        local_dir=save_path,
        prefix=build_model_prefix(trained_model_id)
    )
    logging.info('Downloaded model')

    return_type = NamedTuple('DownloadTrainedModelOutput', [
        ('trained_model_path', str)
    ])
    return return_type(trained_model_path=save_path)


def deploy_model_with_kfserving_component(
        s3_endpoint: str,
        model_bucket: str,
        model_id: str,
        serving_image: str,
        staging_prefix: str,
        namespace: str
) -> NamedTuple('DeployModelOutput', [
    ('service_name', str),
    ('deploy_id', str)
]):
    import os
    import time
    import uuid
    import logging
    import tempfile
    from typing import NamedTuple

    import boto3

    from utils import s3_utils
    from utils.model import build_torchscript_model_path, build_classes_file_path

    from kubernetes.client import (
        V1ObjectMeta, V1EnvVar, V1Container,
        V1ResourceRequirements
    )

    from kfserving import (
        KFServingClient,
        V1beta1InferenceService, V1beta1InferenceServiceSpec,
        V1beta1TransformerSpec, V1beta1PredictorSpec, V1beta1TritonSpec
    )
    from kfserving.constants import constants

    logging.basicConfig(level=logging.INFO)

    # TODO: Triton crashes for some reason with KIND_GPU
    triton_config_pbtxt = """name: "cv"
platform: "pytorch_libtorch"
max_batch_size: 1
input [
  {
    name: "INPUT__0"
    data_type: TYPE_FP32
    dims: [3, 224, 224]
  }
]
output [
  {
    name: "OUTPUT__0"
    data_type: TYPE_FP32
    dims: [10]
  }
]

instance_group [
    {
        count: 1
        kind: KIND_CPU
    }
]"""

    s3 = boto3.resource(
        service_name='s3',
        endpoint_url=s3_endpoint
    )

    deploy_id = str(uuid.uuid4())
    staging_prefix = os.path.join(staging_prefix, deploy_id)
    classes_file_path = 'cv/classes.json'

    with tempfile.TemporaryDirectory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, 'cv/1'))

        s3.Bucket(model_bucket).download_file(
            build_torchscript_model_path(model_id),
            os.path.join(temp_dir, 'cv/1/model.pt')
        )

        s3.Bucket(model_bucket).download_file(
            build_classes_file_path(model_id),
            os.path.join(temp_dir, classes_file_path)
        )

        with open(os.path.join(temp_dir, 'cv/config.pbtxt'), 'w') as config_file:
            config_file.write(triton_config_pbtxt)

        s3_utils.upload_dir_to_bucket(s3.Bucket(model_bucket), temp_dir, staging_prefix)
        classes_file_path = os.path.join(staging_prefix, classes_file_path)

    service_name = f'cv-{model_id[:8]}'

    inference_service = V1beta1InferenceService(
        api_version=constants.KFSERVING_V1BETA1,
        kind=constants.KFSERVING_KIND,
        metadata=V1ObjectMeta(
            name=service_name,
            namespace=namespace
        ),
        spec=V1beta1InferenceServiceSpec(
            predictor=V1beta1PredictorSpec(
                service_account_name='kfserving-service-credentials',
                triton=V1beta1TritonSpec(
                    storage_uri=f's3://{model_bucket}/{staging_prefix}',
                    runtime_version='20.10-py3',
                    env=[
                        V1EnvVar(
                            name='OMP_NUM_THREADS',
                            value='1'
                        )
                    ],
                    args=['--log-verbose=1'],
                    resources=V1ResourceRequirements(
                        requests={
                            'cpu': '100m',
                            'memory': '1Gi',
                            #                        'nvidia.com/gpu': '1'
                        },
                        limits={
                            'cpu': '200m',
                            'memory': '2Gi',
                            #                        'nvidia.com/gpu': '1'
                        }
                    )
                ),
            ),
            transformer=V1beta1TransformerSpec(
                service_account_name='kfserving-service-credentials',
                containers=[
                    V1Container(
                        image=serving_image,
                        name='transformer',
                        command=['python', '-m', 'serving'],
                        args=[
                            '--model_name', 'cv',
                            '--s3_endpoint', s3_endpoint,
                            '--classes_file_uri', f's3://{model_bucket}/{classes_file_path}'
                        ],
                        resources=V1ResourceRequirements(
                            requests={'cpu': '100m', 'memory': '1Gi'},
                            limits={'cpu': '200m', 'memory': '2Gi'}
                        ),
                        env=[
                            V1EnvVar(
                                name='AWS_ACCESS_KEY_ID',
                                value=os.environ['AWS_ACCESS_KEY_ID']
                            ),
                            V1EnvVar(
                                name='AWS_SECRET_ACCESS_KEY',
                                value=os.environ['AWS_SECRET_ACCESS_KEY']
                            )
                        ],
                    )
                ],
            )
        )
    )

    kfclient = KFServingClient()

    # noinspection PyBroadException
    try:
        kfclient.delete(service_name, namespace=namespace)
        logging.warning('Deleted existing service')
        # Need to wait for the service to get deleted, otherwise the creation will fail
        time.sleep(60)
    except Exception:
        pass

    result = kfclient.create(inference_service)
    logging.info(f'Deployed service: {result}')

    return_type = NamedTuple('DeployModelOutput', [
        ('service_name', str),
        ('deploy_id', str)
    ])
    return return_type(
        service_name=service_name,
        deploy_id=deploy_id
    )
