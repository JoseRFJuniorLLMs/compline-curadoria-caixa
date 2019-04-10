# -*- coding: utf-8 -*-
# Bibliotecas
import pandas as pd
import threading
import warnings
import json
import os

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.externals import joblib
from sklearn import metrics

from configparser import ConfigParser
from pymongo import MongoClient
from time import time, strftime, perf_counter

warnings.filterwarnings("ignore")

# Tarefas Assincronas
class asynctask(threading.Thread):
    '''Classe para criação de tarefas assincronas.
    Esta classe recebe uma funcao e a transforma em uma tarefa assincrona.
    
    Atributos:
        - task
        - func
    
    Metodos:
        - run
    '''
    def __init__(self, func):
        '''task: nome da tarefas.
        func: funcao a ser decorada.
        '''
        threading.Thread.__init__(self)
        self.task = func.__name__
        self.func = func
    def run(self):
        '''Inicia um cronometro.
        Procura as informacoes da tarefa dentro de uma colecao MongoDB.
        Inicia a funcao assincronamente.
        Para o cronometro.
        Atualiza as informacoes da thread (duracao e log de erro).
        '''
        try:
            t0 = time()
            query = {'tarefa':self.task}
            update = {'$set': {'emProcessamento':True,'ultimaExecucao': strftime("%m/%d/%Y %H:%M:%S")}}
            threads.update_one(query, update)
            self.func()
            update = {'$set': {'emProcessamento':False,'ultimaDuracao': int(time()-t0), 'error':''}}
            threads.update_one(query, update)
            print(self.task+' done!')
        except Exception as e:
            update = {'$set': {'emProcessamento':False,'ultimaDuracao': -1, 'error':str(e)}}
            threads.update_one(query, update)
            print(self.task+' error!')

# Processamento de Texto
def process(s):
    '''Trata um texto, removendo tudo o que nao for letra e passando todas estas para minusculo.'''
    return ''.join(c if c.isalpha() else ' ' for c in s.encode('ascii', errors='ignore').decode()).lower()
            
# Data Wrangling
def extrair_mongo():
    '''Extrai todos os processos e palavras-chave do MongoDB.
    Faz o merge com o gabarito(csv).
    Remove todas as chave nulas.
    Exporta o resultado para o arquivo df.csv
    '''
    df = pd.DataFrame.from_records(processos.find({'palavrasChave':{'$gt':[]}}, {'numeroProcesso':1, 'palavrasChave':1}))
    df.set_index('_id', inplace=True)
    df.palavrasChave = df.palavrasChave.apply(lambda x: ' '.join(x).replace("'", ''))
    df1 = pd.read_csv('gabarito.csv')
    columns=['NU_PROCESSO', 'NU_ACAO', 'NU_GRUPO_ASSUNTO', 'NU_ASSUNTO', 'palavrasChave']
    df = df.merge(df1, 'left', left_on='numeroProcesso', right_on='NU_PROCESSO')[columns]
    df = df[df.NU_PROCESSO.notnull()]
    df.to_csv('df.csv')
    print(df.shape)

# Modelo de Acao
def retreino_acao():
    '''(Re)Treina o modelo de Acao utilizando as palvras-chave.
    Exporta o modelo para o arquivo model_acao.pkl.
    Gera as metricas de acuracia e as exporta para accuray_acao.json
    '''
    model_acao.fit(df.palavrasChave, df.NU_ACAO)
    df['AcaoPred'] = model_acao.predict(df.palavrasChave)
    joblib.dump(model_acao, 'model_acao.pkl')
    
    accuracy_acao = metrics.classification_report(df.NU_ACAO, df['AcaoPred'], output_dict=True)
    with open('accuracy_acao.json', 'w') as f:
        json.dump(accuracy_acao, f)

# Modelo de Grupo
def retreino_grupo():
    '''(Re)Treina o modelo de Grupo utilizando as palvras-chave.
    Exporta o modelo para o arquivo model_grupo.pkl.
    Gera as metricas de acuracia e as exporta para accuray_grupo.json
    '''
    model_grupo.fit(df.palavrasChave, df.NU_GRUPO_ASSUNTO)
    df['GrupoPred'] = model_grupo.predict(df.palavrasChave)
    joblib.dump(model_grupo, 'model_grupo.pkl')
    
    accuracy_grupo = metrics.classification_report(df.NU_GRUPO_ASSUNTO, df['GrupoPred'], output_dict=True)
    with open('accuracy_grupo.json', 'w') as f:
        json.dump(accuracy_grupo, f)

# Modelo de Assunto
def retreino_assunto():
    '''(Re)Treina o modelo de Assunto utilizando as palvras-chave.
    Exporta o modelo para o arquivo model_assunto.pkl.
    Gera as metricas de acuracia e as exporta para accuray_assunto.json
    '''
    model_assunto.fit(df.palavrasChave, df.NU_ASSUNTO)
    df['AssuntosPred'] = model_assunto.predict(df.palavrasChave)
    joblib.dump(model_assunto, 'model_assunto.pkl')
    
    accuracy_assunto = metrics.classification_report(df.NU_ASSUNTO, df['AssuntosPred'], output_dict=True)
    with open('accuracy_assunto.json', 'w') as f:
        json.dump(accuracy_assunto, f)

# Atualizacao do Mongo
def atualizar_processos():
    '''Inicia um cronometro.
    Carrega os modelos de Acao, Grupo e Assunto.
    Carrega as acuracias dos modelos.
    Pesquisa no Mongo quais sao os documentos Aguardando Classificacao (Situacao 2)\
         e quais foram alterado.
    Para cada documento que possua palavra-chave:
        Realiza predicao para cada um dos modelos.
        Atualiza as classificacoes e acuracias.
        Muda a Situacao para Classificado (Situacao 3).
        Retorna o estado para nao alterado.
    Para o cronometro.
    Atualiza as informacoes de controle.
    '''
    # Start Timer
    t0 = time()
    controle.update_one({}, {'$set': {'emProcessamento': True}})

    # Load Models
    model_acao = joblib.load('model_acao.pkl')
    model_grupo = joblib.load('model_grupo.pkl')
    model_assunto = joblib.load('model_assunto.pkl')

    # Load Models Accuracy
    with open('accuracy_acao.json') as f:
        accuracy_acao = json.load(f)

    with open('accuracy_grupo.json') as f:
        accuracy_grupo = json.load(f)

    with open('accuracy_assunto.json') as f:
        accuracy_assunto = json.load(f)

    # Update Mongo
    for p in processos.find({ "$or": [ { "idSituacao": 2 }, { "alterado": True } ] }):
        if p['palavrasChave']:
            acaoId = str(model_acao.predict(p['palavrasChave'])[0])
            grupoId = str(model_grupo.predict(p['palavrasChave'])[0])
            assuntos = model_assunto.predict(p['palavrasChave'])[0]
            query = {'_id': p['_id']}
            update = {'$set': {'idSituacao': 3,
                               'acao': acao.find_one({'acaoId':int(float(acaoId))})['nome'],
                               'acaoAcuracia': round(accuracy_acao[acaoId]['f1-score'], 2),
                               'grupo': grupo.find_one({'grupoAssuntoId':int(float(grupoId))})['nome'],
                               'grupoAcuracia': round(accuracy_grupo[grupoId]['f1-score'], 2),
                               'assunto': [assunto.find_one({'assuntoId': int(assuntoId)})['nome'] for assuntoId in eval(assuntos)],
                               'assuntoAcuracia': round(accuracy_assunto[assuntos]['f1-score'], 2),
                               'dataClassificacao': strftime("%m/%d/%Y %H:%M:%S"),
                               'alterado': False
                              }
                     }
            processos.update_one(query, update)
        else:
            print(p['_id'])

    # Stop Timer
    controle.update_one({}, {'$set': {'emProcessamento': False,
                                      'dataUltimoProcessamento': strftime("%m/%d/%Y %H:%M:%S"),
                                      'tempoUltimoProcessamentoSec': int(time()-t0)
                                     }
                            })
    print(controle.find_one({}))

# Flask
from flask import Flask
app = Flask(__name__)

# Configurations
config = ConfigParser()
config.read(os.path.join(app.root_path,'Compline.ini'))
compline = config['MongoDB']
database = config['Curadoria']['DBNAME']

# Mongo Connection
client = MongoClient(**compline)
processos = client[database].Processo
acao = client[database].Acao
grupo = client[database].GrupoAssunto
assunto = client[database].Assunto
controle = client[database].ControleReaprendizagem
threads = client[database].PythonThreads

# Model Creation
try:
    df = pd.read_csv(os.path.join(app.root_path,'df.csv'))
except:
    print('Extraindo Mongo...')
    extrair_mongo()
finally:
    df = pd.read_csv(os.path.join(app.root_path,'df.csv'))
    with open(os.path.join(app.root_path,'portuguese')) as f:
        ptbr = f.read().splitlines()

    stopw = ['não', 'ser', 'será', 'serão']
    vec = CountVectorizer(preprocessor=process,
                        stop_words=list(map(process,ptbr+stopw)),
                        max_df=.6,
                        min_df=5,
                        ngram_range=(2, 3))
    clf = MultinomialNB()
    mclf = OneVsRestClassifier(MultinomialNB())
    model_acao = Pipeline([('vec', vec), ('clf', clf)])
    model_grupo = Pipeline([('vec', vec), ('clf', clf)])
    model_assunto = Pipeline([('vec', vec), ('clf', mclf)])

# Saudar
@app.route("/")
def hello():
    if not threads.find_one():
        threads.insert_many([
            {'tarefa': 'extrair_mongo'},
            {'tarefa': 'retreino_acao'},
            {'tarefa': 'retreino_grupo'},
            {'tarefa': 'retreino_assunto'},
            {'tarefa': 'atualizar_processos'},
        ])
    return "hello world!"

# Testar
@app.route('/processar/<texto>')
def processar(texto):
    return process(texto)

# Extrair
@app.route("/extrair")
def extrair():
    extrair_mongo()
    #t1 = asynctask(extrair_mongo)
    #t1.start()
    return 'Extraido!'

# Retreinar Acao
@app.route("/retreinar_acao")
def retreinar_acao():
    retreino_acao()
    #t2 = asynctask(retreino_acao)
    #t2.start()
    return 'Acao Retreinado!'

# Retreinar Grupo
@app.route("/retreinar_grupo")
def retreinar_grupo():
    retreino_grupo()
    #t3 = asynctask(retreino_grupo)
    #t3.start()
    return 'Grupo Retreinado!'

# Retreinar Assunto
@app.route("/retreinar_assunto")
def retreinar_assunto():
    retreino_assunto()
    #t4 = asynctask(retreino_assunto)
    #t4.start()
    return 'Assunto Retreinado!'

# Retreinar
@app.route("/retreinar")
def retreinar():
    retreino_acao()
    #t2 = asynctask(retreino_acao)
    #t2.start()

    retreino_grupo()
    #t3 = asynctask(retreino_grupo)
    #t3.start()
    
    retreino_assunto()
    #t4 = asynctask(retreino_assunto)
    #t4.start()
    return 'Retreinado!'

# Atualizar
@app.route("/atualizar")
def atualizar():
    atualizar_processos()
    #t5 = asynctask(atualizar_processos)
    #t5.start()
    return 'Atualizado!'

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
