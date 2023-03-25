import os
import requests
import json
import pandas as pd
from flask import Flask, request, Response

from gunicorn.app.base import BaseApplication
class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


TOKEN = '6121126670:AAEua-3m7J0iAuP73wn4VaZvWtisAHC3TEw'
API_url = 'https://rossmann-predict-api-c6nz.onrender.com'
chat_id = '1133597071'
# TOKEN = st.secrets["TOKEN"]
# API_url = st.secrets['url']

def send_message(chat_id, text):
	url = f'https://api.telegram.org/bot{TOKEN}/'
	url = url + f'sendMessage?chat_id={chat_id}'
	r = requests.post(url, json={'text':text})
	print(f'Status Code {r.status_code}')
	return None

def load_dataset(store_id):
	# loading test dataset
	df10 = pd.read_csv( 'test.csv' )
	df_store_raw = pd.read_csv('store.csv')

	# merge test dataset + store
	df_test = pd.merge( df10, df_store_raw, how='left', on='Store' )

	# choose store for prediction
	df_test = df_test[df_test['Store']== store_id]

	if not df_test.empty:

		# remove closed days
		df_test = df_test[df_test['Open'] != 0]
		df_test = df_test[~df_test['Open'].isnull()]
		df_test = df_test.drop( 'Id', axis=1 )

		# convert Dataframe to json
		data = json.dumps( df_test.to_dict( orient='records' ) )
	else: 
		data ='error'

	return data

def predict(data):

	# API Call
	url = API_url
	header = {'Content-type': 'application/json' } 
	data = data

	r = requests.post( url, data=data, headers=header )
	print( f'Status Code {r.status_code}.' )

	d1 = pd.DataFrame( r.json(), columns=r.json()[0].keys() )

	return d1

def parse_message(message):
	chat_id = message['message']['chat']['id']
	store_id = message['message']['text']
	store_id = store_id.replace('/', '')

	try:
		store_id = int(store_id )
	except ValueError:
		store_id = 'error'
	return chat_id, store_id



#API initialize
app = Flask(__name__)

@app.route('/', methods = ['GET','POST'])
def index():
	if request.method == 'POST':
		# send_message(chat_id, 'Estoy funcionando') 
		message = request.get_json()
		chat_id, store_id = parse_message(message)
		if store_id!='error': 
		#loadind data
			data =load_dataset(store_id)

			if data!='error':
		#prediction
				d1 = predict(data)			
		#calculation
				d2 = d1[['store', 'prediction']].groupby( 'store' ).sum().reset_index()
		#send message
				msg = f'Store Number {d2['store'].values[0]} forecast for the next 6 weeks: ${d2['prediction'].values[0]:.2f}'
				send_message(chat_id,msg)
				return Response('Ok', status = 200)
			else:	 
				send_message(chat_id, 'Store not available')
				return Response('Ok', status =200)

		else:
			send_message( chat_id, 'Store ID is wrong')
			return Response('Ok', status = 200)
		
	else:
		return '<h1> Rossmann Telegram BOT </h1>'

# if __name__ == '__main__':
#     # Get the port from the environment variable, or use a default value
#     port = int(os.environ.get('PORT', 5000))
    
#     # Run the Flask application using a production-ready web server, such as uWSGI or Gunicorn
#     app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Get the port from the environment variable, or use a default value
    port = int(os.environ.get('PORT', 5000))
    # Run the Flask application using Gunicorn
    gunicorn_options = {
        'bind': f'0.0.0.0:{port}',
        'workers': 2
    }
    from app import app
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)
    StandaloneApplication(app, gunicorn_options).run()
