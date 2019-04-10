# Compline Curadoria Caixa

1. Criar um Azure Virtual Machine
   1. Region: http://azurespeedtest.azurewebsites.net/
   1. Image: Ubuntu Server 18.04 LTS
   1. Size: D4s v3 (4vCPUS, 16 GB)
   1. Allow Ports: ssh
1. Liberar Portas
   1. VM criada
   1. Settings>Network
   1. Add inbound
      1. name:flask_debug; port:5000
      1. name:flask_production; port:8000
1. Instalar Pacotes Básicos
   1. Acessar VM(overview> connect> SSH)
      1. ssh usuario@ip
      1. Password: senha
   1. sudo apt install python3-pip -y
   1. sudo pip3 install virtualenv
   1. sudo pip3 install virtualenvwrapper
1. Configurações Básicas
   1. export WORKON_HOME=~/.virtualenvs
   1. mkdir $WORKON_HOME
   1. echo "export WORKON_HOME=$WORKON_HOME" >> ~/.bashrc
   1. echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bashrc
   1. export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3
   1. source ~/.bashrc
1. Preparar App
   1. mkvirtualenv venv
   1. git clone https://github.com/OneWaySolution/Compline-CuradoriaCaixa.git
   1. cd Compline-CuradoriaCaixa
   1. pip install -r requirements.txt
1. Publicar App
   1. gunicorn app:app -b 0.0.0.0:8000 --reload
1.Acessar VM para Debug
   1. Acessar VM(overview> connect> SSH)
      1. ssh usuario@ip
      1. Password: senha
  1. source .virtualenvs/venv/bin/activate
  1. cd Compline-CuradoriaCaixa
  1. python app.py


References
----

http://timmyreilly.azurewebsites.net/running-flask-on-ubuntu-vm/
http://flask.pocoo.org/docs/0.12/deploying/wsgi-standalone/#gunicorn
https://github.com/OneWaySolution/Compline-CuradoriaCaixa/blob/master/app.py
