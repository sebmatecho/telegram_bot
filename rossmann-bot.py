import os
import requests
import json
import pandas as pd
from flask import Flask, request, Response


#constants
TOKEN = '5293016879:AAEZBzhu_MJXOxq1UHplKAd-Sxi2A7gHuIY'

# Info about the bot
#https://api.telegram.org/bot5293016879:AAEZBzhu_MJXOxq1UHplKAd-Sxi2A7gHuIY/getMe
# Get updates
#https://api.telegram.org/bot5293016879:AAEZBzhu_MJXOxq1UHplKAd-Sxi2A7gHuIY/getUpdates
## Webhook
#https://api.telegram.org/bot5293016879:AAEZBzhu_MJXOxq1UHplKAd-Sxi2A7gHuIY/setWebhook?url=https://2c1e-70-52-175-39.ngrok.io
# Send Messages
#https://api.telegram.org/bot5293016879:AAEZBzhu_MJXOxq1UHplKAd-Sxi2A7gHuIY/sendMessage?chat_id=1133597071&text=Hi, Sebmatecho. Doing great, thanks!


def send_message(chat_id, text):
	url = 'https://api.telegram.org/bot{}/'.format(TOKEN)
	url = url + 'sendMessage?chat_id={}'.format(chat_id)
	r = requests.post(url, json={'text':text})
	print('Status Code {}'.format(r.status_code))

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
	url = 'https://rossmann-forecast-test.herokuapp.com/rossmann/predict'
	header = {'Content-type': 'application/json' } 
	data = data

	r = requests.post( url, data=data, headers=header )
	print( 'Status Code {}'.format( r.status_code ) )

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
				msg =  'Store Number {} forecast for the next 6 weeks: ${:,.2f}'.format( 
				d2['store'].values[0], 
				d2['prediction'].values[0] ) 
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

if __name__ == '__main__':
	port= os.environ.get('PORT',5000 )
	app.run(host='127.0.0.1', port = port)
