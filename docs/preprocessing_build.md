Для работы требуется RabbitMQ. Можно развернуть отдельный контейнер с RabbitMQ или запустить его на холсте или воспользоваться docker-compose.yml в папке image-process-scheduler.

Для того, чтобы запустить docker compose, соберите образ improsch:

    cd image-process-scheduler
    docker build -t improsch . # осторожно, очень тяжёлый образ
    docker-compose up -d

Если RabbitMQ запускается в отдельном контейнере:

    docker pull rabbitmq:3-management
    docker run --rm -it --hostname my-rabbit -p 15672:15672 -p 5672:5672 rabbitmq:3-management

По умолчанию в кролике создан пользователь guest:guest. Порт 15672 - порт для веб интерфейса, 5672 - для использования приложением.
Можно менять, но тогда нужно поменять следующие параметры в .flaskenv:
    RABBIT_LOGIN = 'guest'
    RABBIT_PASSW = 'guest'
    RABBIT_PORT = 5672
    RABBIT_HOST = '127.0.0.1'

Сервису нужно знать, откуда показывать картинки, за это отвечает флаг STORAGE_DIR в .flaskenv.

За предобработку  изображений отвечает https://github.com/NRshka/image-process-scheduler

Нужно отдельно установить faiss, который устанавливается через conda:
    conda install faiss -c pytorch
И пакеты из pypi:
    pip install -r requirements.txt

Для работы отдельно запустите image-process-scheduler:
    python run.py


А потом приложение на flask.
