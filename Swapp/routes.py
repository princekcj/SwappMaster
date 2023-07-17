from flask import jsonify, render_template, url_for, flash, redirect, request
from Swapp.horizonforms import RegistrationForm, LoginForm, TransferForm, UpdateAccountForm, RequestResetForm, ResetPasswordForm, TopUpForm, UpdatePasswordForm
from urllib.request import urlopen
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from flask_mail import Message
import phonenumbers
import pycountry
import time
from Swapp import db, app, bcrypt, mail, cacheen
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
td = TDClient(apikey="0267d29afa8547a19bb4bbbb24dcac27")

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


cached = []
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

def make_cache_key(*args, **kwargs):
    with app.app_context():
        return request.url

@cacheen.memoize(3600)
def cachejob(cached):
    print(f"Job ran at:{datetime.utcnow()}")
    if cached:
        cached[0] = results
        print(cached[0])
        cacheen.set("cache", cached[0])
    else:
        cached.append(results)
        cacheen.set("cache", cached[0])


import sys, socket

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 8000))
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



    scheduler.add_job(cachejob, 'interval', minutes=88, next_run_time=start_time + timedelta(minutes=28), args=[cached])


    # Add the third job to run 5 minutes after the second job



    # Stop the scheduler when the Flask application shuts down
    @atexit.register
    def shutdown():
        scheduler.shutdown()


class GHSbaseprices:
    @cacheen.memoize(3600)
    def GHSbaseUSDprice():
        cache = cacheen.get("cache")
        print(cache)
        result = cache['GHSbaseUSDprice']
        return result


                                                  c c                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              