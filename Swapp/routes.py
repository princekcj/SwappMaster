from flask import jsonify, render_template, url_for, flash, redirect, request
from Swapp.horizonforms import RegistrationForm, LoginForm, TransferForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm, TopUpForm, UpdatePasswordForm
from urllib.request import urlopen
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask_mail import Message
import phonenumbers
import pycountry
import time
from Swapp import db, app, bcrypt, mail
from sqlalchemy import desc
from Swapp.models import User, Transaction, ActiveBid, UserEvents
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from twelvedata import TDClient
import json
import atexit
import requests

# Initialize client - apikey parameter is requiered
td = TDClient(apikey="3acf704ee4ce4e2089cd73928b08c114")

def Fulfilmentcheck(requests):
    if (requests.RequesterAcceptorCompletion == True )& (requests.RequesterCompletion == True ):
        requests.Fufilled = True
        requester = User.query.filter_by(id=requests.Requester_user_id).first()
        successfulbidder = User.query.filter_by(id=requester.RequestAcceptor_user_id).first()

        url = "https://rapidprod-sendgrid-v1.p.rapidapi.com/mail/send"

        payloadtobidder = {
            "personalizations": [
                {
                    "to": [{"email": successfulbidder.email}],
                    "subject": "A Bid Has Been Made On Your Request!"
                }
            ],
            "from": {"email": "from_address@example.com"},
            "content": [
                {
                    "type": "text/plain",
                    "value": f" Request #{requests.id} is FulFilled! User #{requester.id} and User #{successfulbidder.id} have completed the exchange of {requests.BaseCurrency} and {requests.NewCurrency}."
                }
            ]
        }

        payloadtorequester = {
            "personalizations": [
                {
                    "to": [{"email": requester.email}],
                    "subject": "A Bid Has Been Made On Your Request!"
                }
            ],
            "from": {"email": "from_address@example.com"},
            "content": [
                {
                    "type": "text/plain",
                     "value": f" Request #{requests.id} is FulFilled! User #{requester.id} and User #{successfulbidder.id} have completed the exchange of {requests.BaseCurrency} and {requests.NewCurrency}."
                }
            ]
        }
        headers = {
            "content-type": "application/json",
            "X-RapidAPI-Key": "a662b8b6d1mshbf604cd25a5bb8ap1d5915jsn0063bd6dd731",
            "X-RapidAPI-Host": "rapidprod-sendgrid-v1.p.rapidapi.com"
        }

        response1 = requests.request("POST", url, json=payloadtorequester, headers=headers)
        response2 = requests.request("POST", url, json=payloadtobidder, headers=headers)




def makebid_email_update(bid_occ):

    requester = Transaction.query.filter_by(id=bid_occ.request_id).first()
    user = User.query.filter_by(id=requester.Requester_user_id).first()
    email = user.email

    url = "https://rapidprod-sendgrid-v1.p.rapidapi.com/mail/send"

    payload = {
        "personalizations": [
            {
                "to": [{"email": email }],
                "subject": "A Bid Has Been Made On Your Request!"
            }
        ],
        "from": {"email": "from_address@example.com"},
        "content": [
            {
                "type": "text/plain",
                "value":f" User #{bid_occ.bidder_user_id} made a bid of {bid_occ.BidAmount} {bid_occ.BidCurrency} on your Request #{requester.id}! Please Login and progress your request by reviewing your bids and clicking 'Accept Bid' on the corresponding bid event in the 'My Transactions' Section "
            }
        ]
    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": "a662b8b6d1mshbf604cd25a5bb8ap1d5915jsn0063bd6dd731",
        "X-RapidAPI-Host": "rapidprod-sendgrid-v1.p.rapidapi.com"
    }

    response = requests.request("POST", url, json=payload, headers=headers)


def bid_email_update(bid_occ):
    user = User.query.filter_by(id=bid_occ.bidder_user_id).first()
    requester = Transaction.query.filter_by(id=bid_occ.request_id).first()
    email = user.email

    url = "https://rapidprod-sendgrid-v1.p.rapidapi.com/mail/send"

    payload = {
        "personalizations": [
            {
                "to": [{"email": email }],
                "subject": "Your Bid Has Been Accepted!"
            }
        ],
        "from": {"email": "from_address@example.com"},
        "content": [
            {
                "type": "text/plain",
                "value": f"Your Bid Of {bid_occ.BidAmount} {bid_occ.BidCurrency} Has Been Accepted By User #{requester.Requester_user_id} ! Please Login and progress your bid by clicking 'Intiate Chat' on the corresponding exchange event in the 'My Transaction' Section "
            }
        ]
    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": "a662b8b6d1mshbf604cd25a5bb8ap1d5915jsn0063bd6dd731",
        "X-RapidAPI-Host": "rapidprod-sendgrid-v1.p.rapidapi.com"
    }

    response = requests.request("POST", url, json=payload, headers=headers)


cache = []
results ={}

def job14():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=GHS&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['EURbaseGHSchange'] = most_recent_percent_change
    except:
        if 'EURbaseGHSchange' not in results:
            results['EURbaseGHSchange'] = 0

def job15():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GHS&to_symbol=EUR&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['GHSbaseEURchange'] = most_recent_percent_change
    except:
        if 'GHSbaseEURchange' not in results:
            results['GHSbaseEURchange'] = 0
def job16():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GHS&to_symbol=CAD&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date#
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['GHSbaseCADchange'] = most_recent_percent_change
    except:
        if 'GHSbaseCADchange' not in results:
            results['GHSbaseCADchange'] = 0
def job17():

        # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=CAD&to_symbol=GHS&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['CADbaseGHSchange'] = most_recent_percent_change
    except:
        if 'CADbaseGHSchange' not in results:
            results['CADbaseGHSchange'] = 0

def job18():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=JPY&to_symbol=GHS&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['JPYbaseGHSchange'] = most_recent_percent_change
    except:
        if 'JPYbaseGHSchange' not in results:
            results['JPYbaseGHSchange'] = 0

def job19():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GHS&to_symbol=JPY&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['GHSbaseJPYchange'] = most_recent_percent_change
    except:
        if 'GHSbaseJPYchange' not in results:
            results['GHSbaseJPYchange'] = 0


def job20():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GHS&to_symbol=ZAR&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['GHSbaseZARchange'] = most_recent_percent_change
    except:
        if 'GHSbaseZARchange' not in results:
            results['GHSbaseZARchange'] = 0

def job21():
    # replace the "demo" api key below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=CHF&to_symbol=GHS&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0

        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['CHFbaseGHSchange'] = most_recent_percent_change
    except:
        if 'CHFbaseGHSchange' not in results:
            results['CHFbaseGHSchange'] = 0

def job22():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GHS&to_symbol=NGN&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['GHSbaseNGNchange'] = most_recent_percent_change
    except:
        if 'GHSbaseNGNchange' not in results:
            results['GHSbaseNGNchange'] = 0
def job23():
    try:
        ts = td.price(
            symbol="GHS/USD"
        )
        result = ts.as_json()
        result = "{:.4f}".format(float(result['price']))
        results['GHSbaseUSDprice'] = result
    except:
        if 'GHSbaseUSDprice' not in results:
            results['GHSbaseUSDprice'] = 0

def job24():
    try:
        exchange_rate = td.quote(symbol='GHS/USD', interval="1day", timezone="Europe/London")
        exchange_rate = exchange_rate.as_json()
        price_change = float(exchange_rate['percent_change'])
        result = "{:.4f}".format(price_change)
        results['GHSbaseUSDchange'] = result
    except:
        if 'GHSbaseUSDchange' not in results:
            results['GHSbaseUSDchange'] = 0

def job25():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GHS&to_currency=GBP&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GHSbaseGBPprice'] = result
    except KeyError:
        if 'GHSbaseGBPprice' not in results:
            results['GHSbaseGBPprice'] = 0


def job26():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=GHS&to_symbol=GBP&apikey=8XWI3M5GUBYUJ295'
    try:
        r = requests.get(url)
        data = r.json()
        daily_data = data['Time Series FX (Daily)']
        # Initialize the prev_date and most_recent_percent_change variables to None
        prev_date = None
        most_recent_percent_change = None

        # You can loop through the daily data to calculate the percent change for each day
        for date, info in daily_data.items():
            # The closing price for the current day is stored in the '4. close' key
            close = float(info['4. close'])

            # If prev_date is not None, calculate the percent change
            if prev_date is not None:
                # The closing price for the previous day is stored in the '4. close' key of the previous day's data
                prev_close = float(daily_data[prev_date]['4. close'])

                # Calculate the percent change
                percent_change = (close - prev_close) / prev_close

                # Update the value of most_recent_percent_change with the current percent change
                most_recent_percent_change = percent_change

            # Update the value of prev_date to the current date
            prev_date = date
        if most_recent_percent_change == None:
            most_recent_percent_change = 0
        most_recent_percent_change = "{:.4f}".format(most_recent_percent_change)
        # Print the most recent percent change
        results['GHSbaseGBPchange'] = most_recent_percent_change
    except:
        if 'GHSbaseGBPchange' not in results:
            results['GHSbaseGBPchange'] = 0



def job8():


    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=JPY&to_currency=GHS&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['JPYtoGHSRate'] = result
    except KeyError:
        if 'JPYtoGHSRate' not in results:
            results['JPYtoGHSRate'] = 0

def job9():
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GHS&to_currency=JPY&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GHStoJPYRate'] = result
    except KeyError:
        if 'CHFtoGHSRate' not in results:
            results['CHFtoGHSRate'] = 0

def job10():
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=CHF&to_currency=GHS&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['CHFtoGHSRate'] = result
    except KeyError:
        if 'CHFtoGHSRate' not in results:
            results['CHFtoGHSRate'] = 0

def job11():
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=ZAR&to_currency=GHS&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['ZARtoGHSRate'] = result
    except KeyError:
        if 'ZARtoGHSRate' not in results:
            results['ZARtoGHSRate'] = 0

    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=CAD&to_currency=GHS&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['CADtoGHSRate'] = result
    except KeyError:
        if 'CADtoGHSRate' not in results:
            results['CADtoGHSRate'] = 0

def job12():
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GHS&to_currency=NGN&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GHStoNGNRate'] = result
    except KeyError:
        if 'GHStoNGNRate' not in results:
            results['GHStoNGNRate'] = 0

def job13():
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GHS&to_currency=ZAR&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GHStoZARRate'] = result
    except KeyError:
        if 'GHStoZARRate' not in results:
            results['GHStoZARRate'] = 0




def job():

    try:
        ts = td.exchange_rate(symbol="GHS/USD")
        result = ts.as_json()
        results['GHStoUSDRate'] = result['rate']
    except:
        if 'GHStoUSDRate' not in results:
            results['GHStoUSDRate'] = 0

def job1():

    try:
        ts = td.exchange_rate(symbol="USD/GHS")
        result = ts.as_json()
        results['USDtoGHSRate'] = result['rate']
    except:
        if 'USDtoGHSRate' not in results:
            results['USDtoGHSRate'] = 0

def job2():
    try:
        ts = td.exchange_rate(symbol="GBP/USD")
        result = ts.as_json()
        results['GBPtoUSDRate'] = result['rate']
    except:
        if 'GBPtoUSDRate' not in results:
            results['GBPtoUSDRate'] = 0

def job3():
    try:
        ts = td.exchange_rate(symbol="USD/GBP")
        result = ts.as_json()
        results['USDtoGBPRate'] = result['rate']
    except:
        if 'USDtoGBPRate' not in results:
            results['USDtoGBPRate'] = 0

def job4():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GHS&to_currency=EUR&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GHStoEURRate'] = result
    except KeyError:
        if 'GHStoEURRate' not in results:
            results['GHStoEURRate'] = 0

def job44():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=EUR&to_currency=GHS&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['EURtoGHSRate'] = result
    except KeyError:
        if 'EURtoGHSRate' not in results:
            results['EURtoGHSRate'] = 0

def job5():
    # replace the "demo" apikey below with your own key from https://www.alphavantage.co/support/#api-key
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GHS&to_currency=GBP&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GHStoGBPRate'] = result
    except KeyError:
        if 'GHStoGBPRate' not in results:
            results['GHStoGBPRate'] = 0

def job6():
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GBP&to_currency=GHS&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    try:
        data = r.json()
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GBPtoGHSRate'] = result
    except KeyError:
        if 'GBPtoGHSRate' not in results:
            results['GBPtoGHSRate'] = 0

def job7():
    url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=GHS&to_currency=CAD&apikey=8XWI3M5GUBYUJ295'
    r = requests.get(url)
    data = r.json()
    try:
        result = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
        result = "{:.4f}".format(float(result))
        results['GHStoCADRate'] = result
    except KeyError:
        if 'GHStoCADRate' not in results:
            results['GHStoCADRate'] = 0

def cachejob(cache):
    print(f"Job ran at:{datetime.utcnow()}")
    if cache:
        cache[0] = results
    else:
        cache.append(results)


import sys, socket

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 47200))
except socket.error:
    print("!!!scheduler already started, DO NOTHING")
else:
    print("scheduler started")
    # Start the scheduler in the background
    scheduler = BackgroundScheduler()
    scheduler.start()
    start_time = datetime.utcnow() + timedelta(seconds=30)  # add 30 seconds delay to start time

    scheduler.add_job(job, 'interval', minutes=60, next_run_time=start_time)
    scheduler.add_job(job4, 'interval', minutes=61, next_run_time=start_time + timedelta(minutes=1))
    scheduler.add_job(job44, 'interval', minutes=62, next_run_time=start_time + timedelta(minutes=2))
    scheduler.add_job(job5, 'interval', minutes=63, next_run_time=start_time + timedelta(minutes=3))
    scheduler.add_job(job6, 'interval', minutes=64, next_run_time=start_time + timedelta(minutes=4))
    scheduler.add_job(job7, 'interval', minutes=65, next_run_time=start_time + timedelta(minutes=5))
    scheduler.add_job(job8, 'interval', minutes=66, next_run_time=start_time + timedelta(minutes=6))
    scheduler.add_job(job9, 'interval', minutes=67, next_run_time=start_time + timedelta(minutes=7))
    scheduler.add_job(job10, 'interval', minutes=68, next_run_time=start_time + timedelta(minutes=8))
    scheduler.add_job(job11, 'interval', minutes=69, next_run_time=start_time + timedelta(minutes=9))
    scheduler.add_job(job12, 'interval', minutes=70, next_run_time=start_time + timedelta(minutes=10))
    scheduler.add_job(job13, 'interval', minutes=71, next_run_time=start_time + timedelta(minutes=11))
    scheduler.add_job(job14, 'interval', minutes=72, next_run_time=start_time + timedelta(minutes=12))
    scheduler.add_job(job15, 'interval', minutes=73, next_run_time=start_time + timedelta(minutes=13))
    scheduler.add_job(job16, 'interval', minutes=74, next_run_time=start_time + timedelta(minutes=14))
    scheduler.add_job(job17, 'interval', minutes=75, next_run_time=start_time + timedelta(minutes=15))
    scheduler.add_job(job18, 'interval', minutes=76, next_run_time=start_time + timedelta(minutes=16))
    scheduler.add_job(job19, 'interval', minutes=77, next_run_time=start_time + timedelta(minutes=17))
    scheduler.add_job(job20, 'interval', minutes=78, next_run_time=start_time + timedelta(minutes=18))
    scheduler.add_job(job21, 'interval', minutes=79, next_run_time=start_time + timedelta(minutes=19))
    scheduler.add_job(job22, 'interval', minutes=80, next_run_time=start_time + timedelta(minutes=20))
    scheduler.add_job(job23, 'interval', minutes=81, next_run_time=start_time + timedelta(minutes=21))
    scheduler.add_job(job24, 'interval', minutes=82, next_run_time=start_time + timedelta(minutes=22))
    scheduler.add_job(job25, 'interval', minutes=83, next_run_time=start_time + timedelta(minutes=23))
    scheduler.add_job(job26, 'interval', minutes=84, next_run_time=start_time + timedelta(minutes=24))
    scheduler.add_job(job2, 'interval', minutes=85, next_run_time=start_time + timedelta(minutes=25))
    scheduler.add_job(job3, 'interval', minutes=86, next_run_time=start_time + timedelta(minutes=26))
    scheduler.add_job(job1, 'interval', minutes=87, next_run_time=start_time + timedelta(minutes=27))



    scheduler.add_job(cachejob, 'interval', minutes=88, next_run_time=start_time + timedelta(minutes=28), args=[cache])


    # Add the third job to run 5 minutes after the second job



    # Stop the scheduler when the Flask application shuts down
@atexit.register
def shutdown():
    scheduler.shutdown()


class GHSbaseprices:

    def GHSbaseUSDprice():
        result = cache[0]['GHSbaseUSDprice']
        return result

    def GHSbaseUSDchange():
        result = cache[0]['GHSbaseUSDchange']
        return result

    def GHSbaseGBPprice():
        result = cache[0]['GHSbaseGBPprice']
        return result

    def GHSbaseGBPchange():
        result = cache[0]['GHSbaseGBPchange']
        return result

class Rates:
    def GHStoUSDRate():
        result = cache[0]['GHStoUSDRate']
        return result

    def USDtoGHSRate():
        result = cache[0]['USDtoGHSRate']
        return result

    def GBPtoUSDRate():
        result = cache[0]['GBPtoUSDRate']
        return result

    def USDtoGBPRate():
        result = cache[0]['USDtoGBPRate']
        return result

    def GHStoGBPRate():
        result = cache[0]['GHStoGBPRate']
        return result

    def GBPtoGHSRate():
        result = cache[0]['GBPtoGHSRate']
        return result

    def EURtoGHSRate():
        result = cache[0]['EURtoGHSRate']
        return result

    def GHStoEURRate():
        result = cache[0]['GHStoEURRate']
        return result

    def CADtoGHSRate():
        result = cache[0]['CADtoGHSRate']
        return result

    def GHStoCADRate():
        result = cache[0]['GHStoCADRate']
        return result

    def GHStoNGNRate():
        result = cache[0]['GHStoNGNRate']
        return result


    def CHFtoGHSRate():
        result = cache[0]['CHFtoGHSRate']
        return result

    def ZARtoGHSRate():
        result = cache[0]['ZARtoGHSRate']
        return result

    def GHStoZARRate():
        result = cache[0]['GHStoZARRate']
        return result

    def JPYtoGHSRate():
        result = cache[0]['JPYtoGHSRate']
        return result

    def GHStoJPYRate():
        result = cache[0]['GHStoJPYRate']
        return result

    def EURbaseGHSchange():
        result = cache[0]['EURbaseGHSchange']
        return result

    def GHSbaseEURchange():
        result = cache[0]['GHSbaseEURchange']
        return result

    def JPYbaseGHSchange():
        result = cache[0]['JPYbaseGHSchange']
        return result

    def GHSbaseJPYchange():
        result = cache[0]['GHSbaseJPYchange']
        return result

    def CADbaseGHSchange():
        result = cache[0]['CADbaseGHSchange']
        return result

    def GHSbaseCADchange():
        result = cache[0]['GHSbaseCADchange']
        return result

    def GHSbaseZARchange():
        result = cache[0]['GHSbaseZARchange']
        return result

    def GHSbaseNGNchange():
        result = cache[0]['GHSbaseNGNchange']
        return result

    def CHFbaseGHSchange():
        result = cache[0]['CHFbaseGHSchange']
        return result









def TrackBid(bid_occurence):
    request = Transaction.query.filter_by(id=bid_occurence.request_id).first()
    sent_to = request.Requester_user_id
    _user_idOfEvents = bid_occurence.bidder_user_id
    event_type1 = 'Bid_IN'
    event_type2 = 'Bid_REC'
    event_con1 = f'Sent bid to #{sent_to}'
    event_conRec = f'Bid recieved from {_user_idOfEvents}'
    corresponding_event_id = bid_occurence.id
    status = 'Pending'
    amount = bid_occurence.BidAmount
    attachment = 'Attach Payment Confirmation'
    proposed_rate = bid_occurence.BidRate
    eventTo = UserEvents(_user_idOfEvents=_user_idOfEvents, with_id=sent_to , corresponding_event_id=corresponding_event_id ,event_type=event_type1, event_content=event_con1, status=status, amount=amount, attachment = attachment, proposed_rate=proposed_rate )
    eventRecieved = UserEvents(_user_idOfEvents=sent_to, with_id=_user_idOfEvents ,corresponding_event_id=corresponding_event_id, event_type=event_type2, event_content=event_conRec, status=status, amount=amount, attachment = attachment, proposed_rate=proposed_rate )
    print(eventTo)
    db.session.add_all([eventTo, eventRecieved])
    db.session.commit()

def TrackExchange(bid_occurence):
    try:
        print('tracking ex')
        request = Transaction.query.filter_by(id=bid_occurence.request_id).first()
        print(request)
        sent_to = bid_occurence.bidder_user_id
        _user_idOfEvents = current_user.id
        print(sent_to)
        print(_user_idOfEvents)
        BaseCurrency = request.BaseCurrency
        NewCurrency = request.NewCurrency
        event_type = 'Exchange'
        event_con1 = f'Exchange from {BaseCurrency} to {NewCurrency}'
        corresponding_event_id = bid_occurence.id
        status = 'Pending'
        amount = bid_occurence.BidAmount
        attachment = 'Attach Payment Confirmation'
        proposed_rate = bid_occurence.BidRate
        eventTo = UserEvents(with_id=sent_to, _user_idOfEvents=_user_idOfEvents,exchangebasecurrency=BaseCurrency, exchangenewcurrency=NewCurrency, corresponding_event_id=corresponding_event_id , event_type=event_type, event_content=event_con1, status=status, amount=amount, attachment = attachment, proposed_rate=proposed_rate )
        db.session.add(eventTo)
        db.session.commit()
        print(UserEvents.query.filter_by(event_type='Exchange').all())
        print('changes committed successfully')
    except Exception as e:
        print('Error occurred while committing changes to the database: ', e)
        db.session.rollback()
        raise

@app.after_request
def add_header(response):
    response.cache_control.max_age = 300
    return response

@app.route("/")
@app.route("/home")
def home():
    GBPchange = GHSbaseprices.GHSbaseGBPchange()
    USDchange = GHSbaseprices.GHSbaseUSDchange()
    USDprice = GHSbaseprices.GHSbaseUSDprice()
    GBPprice = GHSbaseprices.GHSbaseGBPprice()
    CADtoGHS = Rates.GHStoCADRate()
    JPYtoGHS = Rates.JPYtoGHSRate()
    ZARtoGHS = Rates.ZARtoGHSRate()
    GHStoNGN = Rates.GHStoNGNRate()
    EURtoGHS = Rates.GHStoEURRate()
    CHFtoGHS = Rates.CHFtoGHSRate()
    EURchange = Rates.EURbaseGHSchange()
    ZARchange = Rates.GHSbaseZARchange()
    CADchange = Rates.CADbaseGHSchange()
    JPYchange = Rates.JPYbaseGHSchange()
    CHFchange = Rates.CHFbaseGHSchange()
    NGNchange = Rates.GHSbaseNGNchange()

    return render_template('home.html',CHFtoGHS=CHFtoGHS,CHFchange=CHFchange,NGNchange=NGNchange ,EURchange=EURchange,ZARchange=ZARchange,CADchange=CADchange,JPYchange=JPYchange ,EURtoGHS=EURtoGHS,GHStoNGN=GHStoNGN ,ZARtoGHS=ZARtoGHS ,JPYtoGHS=JPYtoGHS ,CADtoGHS=CADtoGHS,USDprice = USDprice, GBPprice = GBPprice, USDchange=USDchange, GBPchange=GBPchange)


@app.route("/inbox")
def inbox():
    return render_template('inbox.html', title='Inbox', user=current_user)

@app.route("/transactions", methods=['GET', 'POST'])
def transactions ():
    USDtoGBP = Rates.USDtoGBPRate()
    GBPtoUSD = Rates.GBPtoUSDRate()
    GHStoUSD = Rates.GHStoUSDRate()
    USDtoGHS = Rates.USDtoGHSRate()
    GHStoGBP = Rates.GHStoGBPRate()
    GBPtoGHS = Rates.GBPtoGHSRate()
    user= current_user
    events = []
    Intiated = []
    Recieved = []
    userevents = UserEvents.query.filter_by(_user_idOfEvents=user.id).all()
    exchangeevents = UserEvents.query.filter_by(event_type="Exchange").all()
    print(exchangeevents)
    print(userevents)

    for item in userevents:
        dt = item.date_occurred

        # convert to string
        dt_str2 = dt.strftime('%Y-%m-%d %H:%M:%S')
        bID = ActiveBid.query.filter_by(id=item.corresponding_event_id).first()
        requestID = bID.request_id

        event = {
            "id": item.id,
            "_user_idOfEvents": item._user_idOfEvents,
            "event_type": item.event_type,
            "event_content" : item.event_content,
            "corresponding_event_id" : item.corresponding_event_id,
            "requestID" : requestID,
            "with_id" : item.with_id,
            "amount" : item.amount,
            "status" : item.status,
            "proposed_rate" : item.proposed_rate,
            "attachment" : item.attachment,
            "date_posted" : dt_str2
        }
        events.append(event)
        if event['event_type'] == "Bid_IN":
            Intiated.append(event)
        elif event['event_type'] == "Bid_REC":
            Recieved.append(event)

    return render_template('exchangerates.html', title='Exchange Rates',events=events , user=user, Recieved=Recieved, Intiated=Intiated, GHStoGBP=GHStoGBP, GBPtoGHS=GBPtoGHS ,USDtoGBP=USDtoGBP, GBPtoUSD=GBPtoUSD, GHStoUSD=GHStoUSD, USDtoGHS=USDtoGHS)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('trading'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if email is already in use and has not been confirmed
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('This email address has already been registered. Please check your email for a confirmation link.', 'danger')
            return redirect(url_for('register'))


        # Create a dictionary of all country codes and their names
        country_codes = {}
        for country in pycountry.countries:
            country_codes[country.alpha_2] = country.name

        # Parse the phone number
        phone_number = form.phone.data
        parsed_number = phonenumbers.parse(phone_number)

        # Get the country code
        country_code = parsed_number.country_code

        # Look up the country name using the country code
        if country_code in country_codes:
            country_name = country_codes[country_code]
        else:
            country_name = "Unknown"

        print(country_name)

        # Create user object and commit to database
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data,location=country_name, email=form.email.data, phone=form.phone.data , password=hashed_password)
        db.session.add(user)
        db.session.commit()

        flash(f'Account created for {form.username.data}! Please check your email for a confirmation link.', 'success')
        return redirect(url_for('trading'))
    return render_template('register.html', title='Register', form=form)

@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        s = Serializer(app.config['SECRET_KEY'])
        data = s.loads(token)
        email = data.get('email')
        user = User.query.filter_by(email=email, email_confirmed=False).first()
        if user:
            user.email_confirmed = True
            db.session.commit()
            flash('Your email address has been confirmed! You may now log in.', 'success')
            return redirect(url_for('trading'))
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('trading'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)

            return redirect(url_for('trading'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)



@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    USDtoGBP = Rates.USDtoGBPRate()
    GBPtoUSD = Rates.GBPtoUSDRate()
    GHStoUSD = Rates.GHStoUSDRate()
    USDtoGHS = Rates.USDtoGHSRate()
    GHStoGBP = Rates.GHStoGBPRate()
    GBPtoGHS = Rates.GBPtoGHSRate()

    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        current_user.password = hashed_password
        current_user.location = form.location.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        form.location.data = current_user.location
    return render_template('account.html', title='Account', form=form, user=current_user, GHStoGBP=GHStoGBP, GBPtoGHS=GBPtoGHS ,USDtoGBP=USDtoGBP, GBPtoUSD=GBPtoUSD, GHStoUSD=GHStoUSD, USDtoGHS=USDtoGHS)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients=[user.email])
    msg.body = f''' To reset your password, visit the following link:
    {url_for('reset_token', token=token, _external=True)}
    
    If you did not make request then simply ignore this email and no changes will be made
    '''


@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password.', 'info')
        return redirect(url_for('login'))
    return render_template ('reset_request.html', title='Reset Password', form=form)

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash('The password has been updated! You may log in now', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form= form)

@app.route("/wallet")
@login_required
def wallet():
    return render_template('wallet.html', title='Wallet')



@app.route("/trading", methods=['GET', 'POST'])
@login_required
def trading():
    USDtoGBP = Rates.USDtoGBPRate()
    GBPtoUSD = Rates.GBPtoUSDRate()
    GHStoUSD = Rates.GHStoUSDRate()
    USDtoGHS = Rates.USDtoGHSRate()
    GHStoGBP = Rates.GHStoGBPRate()
    GBPtoGHS = Rates.GBPtoGHSRate()


    Request_list = []
    MoneyXchangeRequests = Transaction.query.order_by(desc(Transaction.id)).all()
    user = current_user
    for xchangerequest in MoneyXchangeRequests:
        bidcount = 0

        for indbid in xchangerequest.Active_bids:
            bidcount+=1

        # your datetime object
        dt = xchangerequest.date_posted

        # convert to string
        dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')

        # print the string
        request = {
            "id": xchangerequest.id,
            "Requester_user_id": xchangerequest.Requester_user_id,
            "RequestAmount" : xchangerequest.RequestAmount,
            "Rate" : xchangerequest.Rate,
            "BaseCurrency" : xchangerequest.BaseCurrency,
            "NewCurrency" : xchangerequest.NewCurrency,
            "date_posted" : dt_str,
            "ActiveBids" : bidcount,
            "Fulfilled": str(xchangerequest.Fufilled)
        }
        Request_list.append(request)
    MoneyXchangeRequests = Request_list
    return render_template('topup.html', title='Trading', Requests=MoneyXchangeRequests, user=user,GHStoGBP=GHStoGBP, GBPtoGHS=GBPtoGHS ,USDtoGBP=USDtoGBP, GBPtoUSD=GBPtoUSD, GHStoUSD=GHStoUSD, USDtoGHS=USDtoGHS )

@app.route("/transactions/<int:request_id>/", methods=['GET', 'POST'])
def bid_list(request_id):
    Active_bids= []
    USDtoGBP = Rates.USDtoGBPRate()
    GBPtoUSD = Rates.GBPtoUSDRate()
    GHStoUSD = Rates.GHStoUSDRate()
    USDtoGHS = Rates.USDtoGHSRate()
    GHStoGBP = Rates.GHStoGBPRate()
    GBPtoGHS = Rates.GBPtoGHSRate()
    request = Transaction.query.filter_by(id=request_id).first()
    for item in request.Active_bids:
        userevent = UserEvents.query.filter_by(corresponding_event_id=item.id).first()
        bid = {
            "request_id": item.request_id,
            "bidder_user_id": item.bidder_user_id,
            "status": item.status,
            "BidAmount": item.BidAmount,
            "userevent" : {
                "corresponding_event_id": userevent.id,
                "_user_idOfEvents": userevent._user_idOfEvents,
                "proposed_rate": userevent.proposed_rate

            }
        }
        Active_bids.append(bid)
    user = current_user
    return render_template('transfermoney.html', title='Active Bids', request=request,Active_bids=Active_bids ,user=user,GHStoGBP=GHStoGBP, GBPtoGHS=GBPtoGHS ,USDtoGBP=USDtoGBP, GBPtoUSD=GBPtoUSD, GHStoUSD=GHStoUSD, USDtoGHS=USDtoGHS)


@app.route("/api/create_request/", methods =['GET', 'POST'])
def create_request():
    if current_user.is_authenticated:
        if request.method == 'POST':
            amount = request.json['amount']
            pick2 = request.json['currencycreate2']
            pick1 = request.json['currencycreate1']
            pick3 = request.json['sr2boxid']
            newrequest = Transaction(RequestAmount=amount, NewCurrency=pick1, BaseCurrency=pick2, Requester_user_id=current_user.id, Fufilled=False, AcceptedRequest=False,RequesterAcceptorCompletion=False, RequesterCompletion=False,Rate=pick3)
            db.session.add(newrequest)
            db.session.commit()

    return jsonify({"value":"success"})

#send a email to requester
@app.route("/api/make_bid/", methods =['GET', 'POST'])
def make_bids():
    if current_user.is_authenticated:
        if request.method == 'POST':
            requestid = request.json['passrequestid']
            amount = request.json['compensation']
            bid_curr = request.json['currenci']
            bidder =current_user.id
            bid_rate = request.json['bidrate']
            newbid = ActiveBid(BidRate=bid_rate, BidAmount=amount, BidCurrency=bid_curr, request_id=requestid, bidder_user_id=bidder, still_active= True,  status= "Pending")
            db.session.add(newbid)
            db.session.commit()
            TrackBid(newbid)
            makebid_email_update(newbid)

    return jsonify({"value": "success"})

@app.route("/api/accept_bid/", methods =['GET', 'POST'])
def accept_bids():
    if current_user.is_authenticated:
        if request.method == 'POST':

            userevent = UserEvents.query.filter_by(id=request.json['id']).first()
            if userevent.status == 'Pending':
                userevent.status = 'Processing'

                bidtoturnoff = ActiveBid.query.filter_by(id=request.json['corresponding_event_id']).first()
                bidtoturnoff.still_active = False
                bidtoturnoff.status = "Processing"
                request_ = Transaction.query.filter_by(id=bidtoturnoff.request_id).first()
                request_.Rate = (1/float(request.json['proposed_rate']))
                request_.AcceptedRequest = True

                # Add checks for requester_acceptor_user_id field
                request_ = Transaction.query.filter_by(id=bidtoturnoff.request_id).first()
                print(request_)
                if request_.date_accepted != None:
                    print('ok')
                    time_elapsed = datetime.now() - request_.date_accepted
                    if time_elapsed > timedelta(days=2) or request_.Fufilled == True:
                        return flash("Another Bid Has Been Accepted", "warning")
                    if request_.RequestAcceptor_user_id is not None:
                        return flash("Another Bid Has Been Accepted", "warning")
                    print('made it 2')
                    request_.date_accepted = datetime.now()
                    request_.RequestAcceptor_user_id = bidtoturnoff.bidder_user_id
                    db.session.commit()
                    TrackExchange(bidtoturnoff)
                    print('winning again')
                    bid_email_update(bidtoturnoff)
                    return jsonify({"value": "success"})

                else:
                    print('made it')
                    time_elapsed = 172800
                    if timedelta(seconds=time_elapsed) < timedelta(days=2) or request_.Fufilled == True:
                        return flash("Another Bid Has Been Accepted", "warning")
                    if request_.RequestAcceptor_user_id is not None:
                        return flash("Another Bid Has Been Accepted", "warning")
                    print('made it 2')
                    request_.date_accepted = datetime.now()
                    request_.RequestAcceptor_user_id = bidtoturnoff.bidder_user_id
                    db.session.commit()

                    TrackExchange(bidtoturnoff)
                    print('winning again')
                    bid_email_update(bidtoturnoff)
                    return jsonify({"value": "success"})
            else:
                pass


@app.route("/api/cancel_bid/", methods =['GET', 'POST'])
def cancel_bids():
    if current_user.is_authenticated:
        if request.method == 'POST':

            userevent = UserEvents.query.filter_by(id=request.json['id']).first()
            userevent.status = 'Cancelled'

            bidtoturnoff = ActiveBid.query.filter_by(id=request.json['corresponding_event_id']).first()
            bidtoturnoff.still_active = False
            bidtoturnoff.status = "Cancelled"
            request_ = Transaction.query.filter_by(id=bidtoturnoff.request_id).first()
            request_.AcceptedRequest = False
            db.session.commit()
            bid_email_update(bidtoturnoff)
    return jsonify({"value": "success"})

@app.route("/api/intiate_chat/", methods =['GET', 'POST'])
def intiate_chat():
    if current_user.is_authenticated:
        if request.method == 'POST':
            requesting = Transaction.query.filter_by(id=request.json['id_of_request']).first()
            requestOwner = User.query.filter_by(id=requesting.Requester_user_id).first()
            bidder = User.query.filter_by(id=request.json['bidder_user_id']).first()
            if requesting.RequestAcceptor_user_id == bidder.id:
                url = "https://api.maytapi.com/api/abf38d08-9151-4a0a-b1e7-5a37e44829a9/27413/createGroup"

                payload = json.dumps({
                    "name": "Swapp group test",
                    "numbers": [
                        f"{requestOwner.phone}",
                        f"{bidder.phone}"
                    ]
                })
                headers = {
                    'x-maytapi-key': '04312fbb-da97-4c13-a9bb-ed3bb41df438',
                    'Content-Type': 'application/json'
                }

                response = requests.request("POST", url, headers=headers, data=payload)

            elif requesting.RequestAcceptor_user_id != bidder.id:
                flash("Bid Must Accepted First!", "warning")

    return jsonify({"value": "success"})

@app.route("/api/complete_exchange/", methods =['GET', 'POST'])
def complete_exchange():
    if current_user.is_authenticated:
        if request.method == 'POST':

            userevent = UserEvents.query.filter_by(id=request.json['id']).first()
            userevent.status = 'Complete'

            bidtoturnoff = ActiveBid.query.filter_by(id=request.json['corresponding_event_id']).first()
            bidtoturnoff.still_active = False
            bidtoturnoff.status = "Complete"
            request_ = Transaction.query.filter_by(id=bidtoturnoff.request_id).first()
            request_.Fufilled = True
            if current_user.id == userevent.with_id:
                request_.RequesterAcceptorCompletion = True
            elif current_user.id == userevent._user_idOfEvents:
                request_.RequesterCompletion = True

            if (request_.RequesterAcceptorCompletion == True) & (request_.RequesterCompletion == True):
                userevent.status = 'Complete'
            else:
                flash('Both Users Need To Complete', 'warning')
            Fulfilmentcheck(request_)
            db.session.commit()
    return jsonify({"value": "success"})


@app.route("/api/intiate_chatfromx/", methods =['GET', 'POST'])
def intiate_chatfromx():
    if current_user.is_authenticated:
        if request.method == 'POST':


            bid = ActiveBid.query.filter_by(id=request.json['corresponding_event_id']).first()
            bidder = User.query.filter_by(id=bid.bidder_user_id).first()
            requesting = Transaction.query.filter_by(id=bid.request_id).first()
            requestOwner = User.query.filter_by(id=requesting.Requester_user_id).first()
            exchangeevent = UserEvents.query.filter_by(id=request.json['id']).first()


            url = "https://api.maytapi.com/api/abf38d08-9151-4a0a-b1e7-5a37e44829a9/27413/createGroup"

            payload = json.dumps({
                "name": "Swapp group test",
                "numbers": [
                    f"{requestOwner.phone}",
                    f"{bidder.phone}"
                ]
            })
            headers = {
                'x-maytapi-key': '04312fbb-da97-4c13-a9bb-ed3bb41df438',
                'Content-Type': 'application/json'
            }

            response = requests.request("POST", url, headers=headers, data=payload)


            if exchangeevent.status != 'Processing':
                exchangeevent.status = 'Processing'
                db.session.commit()

    return jsonify({"value": "success"})

 
