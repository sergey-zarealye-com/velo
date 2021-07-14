# Getting Started
Accelerate your next web project and start with this Flask App Blueprint. This Getting Started how-to is for written for OS X / macOS.


## 1. Setup your development environment
1. Clone the repository and create a working directory
    1. Run `git clone git@github.com:sergey-zarealye-com/velo.git`
    2. Run `cd velo`

2. Create a virtual environment `python3 -m venv velo`

3. Activate the virtual environment `. velo/bin/activate`

6. Install Packages
    1. Run `pip3 install -r requirements.txt`

## 2. Setup Github, Heroku, and Mandrill
1. Setup Github Repository
    1. Пришли мне SSH ключ для гитхаба
    
            ssh-keygen -t ed25519 -C "your@email.com"
            <use default file location>
            
            $ eval "$(ssh-agent -s)"
            > Agent pid 59566
            
            $ ssh-add ~/.ssh/id_ed25519
            
            sudo cat ~/.ssh/id_ed25519.pub
            <copy public key>

# 5. Create an account on [Mandrill](https://www.mandrill.com/)
#     1. Run `nano $VIRTUAL_ENV/bin/postactivate`
#     2. Add (and modify) the following line: `export MAIL_USERNAME="Your SMTP Username"`
#     2. Add (and modify) the following line: `export MAIL_PASSWORD="Your Mandrill API Key"`
#     2. Add (and modify) the following line: `export MAIL_DEFAULT_SENDER="your@defaultaddress.com"`

## 3. Setup and Initialize Database
1. Setup local database
    1. Download and install [Postgres.app](http://postgresapp.com/)
    2. Open Postgres.app and open psql
            sudo -u postgres psql
    3. Create new database:
            postgres=# create user velo;
            CREATE ROLE
            postgres=# create database velo;
            CREATE DATABASE
            postgres=# alter user velo with encrypted password '123';
            ALTER ROLE
            postgres=# grant all privileges on database velo to velo;
            GRANT
            
    4. Enable passwords authentication in PostreSQL:
            sudo nano /etc/postgresql/12/main/pg_hba.conf 
            --->
                local   all             postgres                                peer
                local   all             all                                     md5
            sudo service postgresql restart


2. Initialize and run database migrations
    4. Run `flask db upgrade`

# 4. Image preprocessor
1. Создайте две директории для работы с картинками (<image_dir>) и хранения индекса (<dedup_dir>).
2. Добавьте пути к этим директориям в image-process-scheduler/docker-compose.yml
3. В директории image-process-scheduler собирается образ:
    cd image-process-scheduler
    docker build -t improsch .
4. Запускается docker-compose:
    docker-compose up # show logs
    docker-compose up -d # detached
5. Примерно после 3-5 секунд сервис готов к работе, можно запускать flask

## 5. Deploy
1. Run locally
    1. Open Postgres.app
    2. Run `. venv/bin/activate`
    3. Run `flask run`
    4. Open in your browser: http://localhost:5000/

2. Make changes, and get them committed
    1. Run `nose2` to ensure all tests still succeed (before running nose2 make sure a database named 'test' is created)
    2. Run `git add .`
    3. Run `git commit -a -m "Your Commit Message"`
    4. Run `git push origin master` to push to GitHub
