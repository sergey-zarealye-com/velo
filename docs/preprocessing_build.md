Для работы требуется RabbitMQ.

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

Для работы отдельно запустите image-process-scheduler:
    python run.py

А потом приложение на flask.
