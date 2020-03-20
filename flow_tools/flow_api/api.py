import os
from flask import Flask, request
app = Flask(__name__)

'''
input 
'''

@app.route('/save',methods=["POST"])
def save_config():
    '''
    save configuration to folder, if configuration
    already exists,
    input: 
    '''
    pass

@app.route('/load',methods=["POST"])
def load_config():
    '''
    load in configuration to use
    '''
    pass

@app.route('/run',methods=["POST"])
def run():
    '''
    run experiment
    '''
    pass

@app.route('/tbd')
def somethingelse():
    '''
    any other end point the backend needs to do
    '''
    pass

if __name__ = '__main__':
    conf_p = '/configs'
    if not os.path.exists(conf_p):
        os.makedirs(conf_p)
    app.run()