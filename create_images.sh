cd dockers && sudo -S docker build -t base_image .
cd image-process-scheduler && sudo -S docker build -t improsch .
cd ../../project/celery && sudo -S docker build -t moderation .
cd ../../scoring && sudo -S docker build -t scoring .
