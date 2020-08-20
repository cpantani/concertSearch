from flask import Flask, render_template, flash, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField , SubmitField, Form, TextField, PasswordField, validators
from wtforms.validators import DataRequired, ValidationError, EqualTo
import requests
from flask import request
from flask import render_template, flash, redirect, url_for, redirect, request, Flask
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
import sys
from sqlalchemy import desc
import os
import datetime
import random
import re

basedir = os.path.abspath(os.path.dirname(__file__))


app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

bootstrap = Bootstrap(app)
moment = Moment(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
db=SQLAlchemy(app)

#LOGIN
class LoginForm(FlaskForm):
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	submit = SubmitField('Sign In')

class addUserForm(FlaskForm):
	username =TextField('Username', validators =[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	submit = SubmitField('Submit')

#login

class Login(db.Model):
	__tablename__ = 'login'
	username = db.Column(db.String(64), primary_key=True)
	password = db.Column(db.String(64), unique=False)
	role = db.Column(db.String(64), unique=False)

	def __repr__(self):
		return self.username + ':' + self.password

class User(UserMixin):
	def __init__(self, username, password, role):
		self.id = username
		# hash the password and output it to stderr
		#self.pass_hash = generate_password_hash(password)
		self.password = password
		self.role = role


def is_admin():
	if current_user:
		if current_user.role == 'admin':
			return True
		else:
			return False
	else:
		print('User not authenticated.', file=sys.stderr)


@login_manager.user_loader
def load_user(username):
	login_obj = Login.query.filter_by(username=username).first()
	return User(login_obj.username, login_obj.password, login_obj.role)
#query id get back user object


def getUser():
	return current_user.id

@app.route('/')
@app.route('/start')
@login_required
def start():
	return redirect(url_for('login'))


@app.route('/admin_only')
@login_required
def admin_only():
    # determine if current user is admin
	if is_admin():
		return render_template('admin.html', message="I am admin.")
	else:
		return render_template('unauthorized.html')

@app.route('/success')
def success():
	return redirect(url_for('home'))


@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if current_user.is_authenticated:
		return redirect(url_for('home'))

# display the login form
	#form = LoginForm()
	if form.validate_on_submit():
		login_obj = Login.query.filter_by(username=form.username.data).first()


        #valid_password = check_password_hash(login_obj.password, form.password.data)
		valid_password = login_obj.password == form.password.data
		if login_obj is None or not valid_password:
			print('Invalid username or password', file=sys.stderr)
			return redirect(url_for('start'))
		else:
			user = User(login_obj.username, login_obj.password, login_obj.role)
			login_user(user)
			return redirect(url_for('success'))
	return render_template('login.html', title='Sign In', form=form)


@app.route('/adduser', methods=['GET', 'POST'] )
def adduser():
	form = addUserForm()
	if form.validate_on_submit():
		login_obj = Login.query.filter_by(username=form.username.data).first()
		if login_obj is None:
			u = Login(username=form.username.data, password=form.password.data, role='user')
			db.session.add(u)
			db.session.commit()
		form.username.data = ''
		form.password.data = ''
	return render_template('adduser.html', form=form)

@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('start'))


#end login







#db tables start here
class Trip(db.Model):
	trip_id=db.Column(db.Integer, primary_key=True)
	user_id=db.Column(db.String(64), db.ForeignKey('login.username'))
	trip_complete=db.Column(db.Boolean, default=False)
	starting_location=db.Column(db.String(120))
class Event(db.Model):
	relation_id=db.Column(db.Integer, primary_key=True)
	event_id=db.Column(db.String(64))
	trip_id=db.Column(db.Integer, db.ForeignKey('trip.trip_id'))
	date=db.Column(db.Date)
	address=db.Column(db.String(254))
	band=db.Column(db.String(120))
	time=db.Column(db.String(64))
	lat=db.Column(db.String(64))
	lng=db.Column(db.String(64))
	city=db.Column(db.String(120))
	displayName=db.Column(db.String(254))

#db functions

#placeholder for username
#def getUser():
#	return 'user1'

#creates new trip
def newTrip(starting_location):
	current_user=str(getUser())
	start_loc=str(starting_location)
	new_trip=Trip(user_id=current_user, starting_location=start_loc)
	db.session.add(new_trip)
	db.session.commit()

#returns trip id of current active trip
def getTrip():
	current_user=getUser()
	current_trip=db.session.query(Trip).filter(Trip.user_id==str(current_user), Trip.trip_complete==False).first()
	return current_trip.trip_id

def getStart():
	current_user=getUser()
	current_trip=db.session.query(Trip).filter(Trip.user_id==str(current_user), Trip.trip_complete==False).first()
	return current_trip.starting_location

#comptets current trip, sets trip_complete to true
def completeTrip():
	current_user=getUser()
	current_trip=db.session.query(Trip).filter(Trip.user_id==str(current_user), Trip.trip_complete==False).first()
	current_trip.trip_complete=True
	db.session.commit()

#adds new event, sonkick id is the input
def newEvent(songkick_id):
	current_trip=getTrip()
	event_toadd=songkick_id
	event_date_str=getEventInfo('date', songkick_id)
	event_date = datetime.datetime.strptime(event_date_str, '%Y-%m-%d')
	event_address= getEventInfo('address', songkick_id)
	event_band= getEventInfo('band', songkick_id)
	event_time=getEventInfo('time', songkick_id)
	event_lat=getEventInfo('lat', songkick_id)
	event_lng=getEventInfo('lng', songkick_id)
	event_city=getEventInfo('city', songkick_id)
	event_displayName=getEventInfo('name', songkick_id)
	new_event=Event(event_id=event_toadd, trip_id=current_trip, date=event_date, address=event_address, band=event_band, time=event_time, lat=event_lat, lng=event_lng, city=event_city, displayName=event_displayName )
	db.session.add(new_event)
	db.session.commit()

#returns list of songkick ids for current trip
def getEventList():
	current_trip=getTrip()
	event_query=db.session.query(Event).filter(Event.trip_id==current_trip).order_by(desc(Event.date)).all()
	event_list=[]
	for n in event_query:
		event_list.append(n.event_id)
	return event_list

def eventListSizeTest():
	event_list=getEventList()
	list_size=len(event_list)
	if list_size<3:
		return True
	else:
		return False

#get event info based on input
def getEventInfoDB(param, event_id):
	event_chosen=event_id
	event = db.session.query(Event).filter(Event.event_id==event_chosen).first()
	if param=="date":
		return event.date
	elif param=="address":
		return event.address
	elif param=="band":
		return event.band
	elif param=="time":
		return event.time
	elif param=="lat":
		return event.lat
	elif param=="lng":
		return event.lng
	elif param=="city":
		return event.city
	elif param=="name":
		return event.displayName
	else:
		return "null"


#delete event
def removeEvent(event_removed):
	current_trip=getTrip()
	event = db.session.query(Event).filter(Event.event_id==event_removed).first()
	db.session.delete(event)
	db.session.commit()

#check if there is already an active trip
def activeTrip():
	current_user=getUser()
	active_trip=db.session.query(Trip).filter(Trip.user_id==str(current_user), Trip.trip_complete==False).one_or_none()
	if active_trip is None:
		return False
	else:
		return True

def getCompletedTrips():
	current_user=getUser()
	trips=db.session.query(Trip).filter(Trip.user_id==str(current_user), Trip.trip_complete==True).all()
	trip_list=[]
	for n in trips:
		trip_list.append(n.trip_id)
	return trip_list

def getCompletedEventList(trip_id):
	trip=trip_id
	event_query=db.session.query(Event).filter(Event.trip_id==trip).order_by(desc(Event.date)).all()
	event_list=[]
	for n in event_query:
		event_list.append(n.event_id)
	return event_list

def getCompletedTripStart(trip_id):
	trip=trip_id
	current_trip=db.session.query(Trip).filter(Trip.trip_id==trip).first()
	return current_trip.starting_location

#test whether event already exists in trip
#if true it does
def eventExists(event):
	event_chosen=event
	events_existing=getEventList()
	if event_chosen in events_existing:
		return True
	else:
		return False

class NameForm(FlaskForm):
	name = StringField('Artist:', validators = [DataRequired()])
	submit = SubmitField('Submit')
class StartForm(FlaskForm):
	street = StringField('Street', validators = [DataRequired()])
	city = StringField('City', validators = [DataRequired()])
	state = StringField ('State', validators = [DataRequired()])
	submit = SubmitField('Submit')
class homeForm(FlaskForm):
	newTrip = SubmitField(label="New Trip")


def getEventInfo(param, event_id):
	event_chosen = event_id
	api_key = 'IIy9YxLaDIVEoFkm'
	search_url = str('https://api.songkick.com/api/3.0/events/'+event_chosen+'.json?apikey='+api_key)
	r=requests.get(search_url)
	single_event=r.json()
	if param=='address':
		state = str(single_event['resultsPage']['results']['event']['venue']['city']['displayName'])
		city = str(single_event['resultsPage']['results']['event']['venue']['city']['state']['displayName'])
		street = str(single_event['resultsPage']['results']['event']['venue']['street'])
		address = street +' '+ city +', ' + state
		return address
	elif param=='band':
		band = str(single_event['resultsPage']['results']['event']['performance'][0]['artist']['displayName'])
		return band
	elif param=='date':
		date = str(single_event['resultsPage']['results']['event']['start']['date'])
		return date
	elif param=='time':
		time = date = str(single_event['resultsPage']['results']['event']['start']['time'])
		return time
	elif param=='lat':
		venue_lat=single_event['resultsPage']['results']['event']['venue']['lat']
		return venue_lat
	elif param=='lng':
		venue_lng=single_event['resultsPage']['results']['event']['venue']['lng']
		return venue_lng
	elif param=="name":
		displayName=str(single_event['resultsPage']['results']['event']['displayName'])
		return displayName
	elif param=="city":
		state = str(single_event['resultsPage']['results']['event']['venue']['city']['displayName'])
		city = str(single_event['resultsPage']['results']['event']['venue']['city']['state']['displayName'])
		address = city +', ' + state
		return address
	else:
		return 'null'

def getLodgingInfo( param, place_id):
	lodging_id=place_id
	payload={'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM' , 'place_id': lodging_id}
	r=requests.get('https://maps.googleapis.com/maps/api/place/details/json', params=payload)
	place_info=r.json()
	place=dict()
	if param=='name':
		chosen_name=place_info['result']['name']
		return chosen_name
	elif param=='address':
		chosen_address=place_info['result']['formatted_address']
		return chosen_phone
	elif param=='phone':
		chosen_phone=place_info['result']['formatted_phone_number']
		return chosen_phone
	elif param=='map':
		chosen_maps_url=place_info['result']['url']
		return chosen_maps_url
	elif param=='website':
		chosen_website=place_info['result']['website']
		return chosen_website
	elif param=='dict':
		chosen_name=place_info['result']['name']
		chosen_address=place_info['result']['formatted_address']
		chosen_phone=place_info['result']['formatted_phone_number']
		chosen_maps_url=place_info['result']['url']
		try:
			chosen_website=place_info['result']['website']
		except:
			chosen_website="No Website Provided"
		place.update({'name': chosen_name, 'address': chosen_address, 'phone': chosen_phone, 'maps_url': chosen_maps_url, 'website': chosen_website})
		return place
	else:
		return 'error'


def get_lodging_dict(lat, lng):
	#return possible lodging options atm within roughly 5 miles
	location= str(lat)+','+str(lng)
	payload={'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM' , 'location': location, 'radius': "8000", 'type': "lodging"}
	r=requests.get('https://maps.googleapis.com/maps/api/place/nearbysearch/json', params=payload)
	response=r.json()
	lodging_dict=dict()
	i=1
	for lodging in response['results']:
		result_num='result '+str(i)
		name=lodging['name']
		address=lodging['vicinity']
		lat=lodging['geometry']['location']['lat']
		lng=lodging['geometry']['location']['lng']
		place_id=lodging['place_id']
		lodging_dict.update({result_num :{'name': name, 'address': address, 'lat': lat, 'lng': lng, 'place_id': place_id}})
		i=i+1
	return lodging_dict

#return list of bands in event list
def getEventListStr(event_list):
	event_str=" "
	for event in event_list:
		event_band=getEventInfoDB("band", event)
		event_str=event_str+" & "+event_band
	return event_str


@app.route('/', methods=['GET', 'POST'])
def default_page():
	return redirect(url_for('home'))

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
	form = homeForm()
	if form.validate_on_submit():
		if activeTrip():
			return render_template('trip_error.html')
		else:
			return redirect(url_for('new_trip'))
	return render_template('select_option.html', form=form)

@app.route('/new_trip', methods=['GET', 'POST'])
@login_required
def new_trip():
	street = None
	city = None
	state = None
	form = StartForm()
	if form.validate_on_submit():
		street = form.street.data
		form.street.data=""
		city = form.city.data
		form.street.data=""
		state = form.state.data
		form.state.data=""
		origin_address = street +' '+ street +', '+ state
		newTrip(starting_location=origin_address)
		return redirect(url_for('band_search'))
	return render_template("starting_location.html", start_form=form)

@app.route('/band_search', methods=['GET','POST'])
@login_required
def band_search():
	if not activeTrip():
		return render_template('trip_error2.html')
	name = None
	d=dict()
	form = NameForm()
	if form.validate_on_submit():
		name = form.name.data
		form.name.data = ""
		payload={'apikey': 'IIy9YxLaDIVEoFkm' , 'artist_name': name}
		r=requests.get('https://api.songkick.com/api/3.0/events.json', params=payload)
		response=r.json()
		i=1
		for events in response['resultsPage']['results']['event']:
			eventName= 'event '+str(i)
			displayName=events['displayName']
			eventID=events['id']
			location=events['location']['city']
			lat=events['location']['lat']
			lng=events['location']['lng']
			date=events['start']['date']
			time=events['start']['time']
			d.update({eventName :{'Display Name': displayName, "Event ID": eventID, "location": location, "lat": lat, "lng": lng, "date":date, "time": time}})
			i=i+1
	return render_template("index.html", d=d, form=form, name=name)

@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
	event_chosen=request.form.get('event')
	if eventExists(event_chosen):
		return render_template("event_error.html")
	elif eventListSizeTest()==False:
		return render_template("trip_size_error.html")
	newEvent(event_chosen)
	return render_template("event_success.html")


@app.route("/get_directions", methods=['GET', 'POST'])
@login_required
def get_directions():
	if not activeTrip():
		return render_template('trip_error2.html')
	waypoints= None
	origin_address= getStart()
	event_list= getEventList()
	if len(event_list)==1:
		address=getEventInfo('address', event_list[0])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving'}
	elif len(event_list)==2:
		waypoint=getEventInfo('address', event_list[0])
		address=getEventInfo('address', event_list[1])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}
	elif len(event_list)==3:
		waypoint=getEventInfo('address', event_list[0])+'|'+getEventInfo('address', event_list[1])
		address=getEventInfo('address', event_list[2])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}
	else:
		address=getEventInfo('address', event_list[len(event_list)-1])
		waypoints=getEventInfo('address', event_list[0])
		n=1
		while n<=(len(event_list)-2):
			waypoints=waypoints+'|'+getEventInfo('address', event_list[n])
			n=n+1
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}
	r = requests.get('https://maps.googleapis.com/maps/api/directions/json', params=payload)
	travel_response = r.json()
	travel_dict=dict()
	n=1
	step_order=[]
	for leg in travel_response['routes'][0]['legs'][0]['steps']:
		step_num='event'+str(n)
		directions_tofix = leg['html_instructions']
		directions = re.sub('<.*?>','', directions_tofix)
		time = leg['duration']['text']
		distance = leg['distance']['text']
		travel_dict.update({step_num :{'Distance': distance, "Time": time, "directions": directions}})
		n=n+1
		step_order.append(step_num)
	return render_template("travel.html", travel_dict=travel_dict, travel_step=step_order)

@app.route("/view_events", methods=['GET', 'POST'])
@login_required
def view_events():
	if not activeTrip():
		return render_template('trip_error2.html')
	event_dict=dict()
	event_order=[]
	event_list=getEventList()
	i=1
	for event in event_list:
		eventNum=i
		displayName=getEventInfoDB('name', event)
		eventID=event
		location=getEventInfoDB('city', event)
		date=getEventInfoDB('date', event)
		time=getEventInfoDB('time', event)
		event_dict.update({eventNum :{'Display Name': displayName, "Event ID": eventID, "location": location, "date":date, "time": time}})
		event_order.append(i)
		i=i+1
	return render_template("events.html", event_dict=event_dict, event_order=event_order)

@app.route('/remove_event', methods=['GET', 'POST'])
@login_required
def remove_event():
	event_rem = request.form.get('remEvent')
	removeEvent(event_rem)
	return redirect(url_for('view_events'))


@app.route("/get_lodging", methods=['GET', 'POST'])
@login_required
def get_lodging():
	event = request.form.get('event')
	lat= getEventInfo('lat', event)
	lng= getEventInfo('lng', event)
	lodging_dict= get_lodging_dict(lat, lng)
	return render_template("lodging.html", lodging_dict=lodging_dict, event=event )

@app.route("/view_lodging_info", methods=['GET', 'POST'])
@login_required
def view_lodging_info():
	place_id=request.form.get('lodging')
	event = request.form.get('event')
	specific_lodging=getLodgingInfo('dict', place_id)
	return render_template('lodging_info.html', specific_lodging=specific_lodging, event=event)

@app.route("/trip_summary", methods=['GET', 'POST'])
@login_required
def trip_summary():
	if not activeTrip():
		return render_template('trip_error2.html')
	#directions
	waypoints= None
	origin_address= getStart()
	event_list= getEventList()
	if len(event_list)==1:
		address=getEventInfo('address', event_list[0])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving'}
	elif len(event_list)==2:
		waypoint=getEventInfo('address', event_list[0])
		address=getEventInfo('address', event_list[1])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}
	elif len(event_list)==3:
		waypoint=getEventInfo('address', event_list[0])+'|'+getEventInfo('address', event_list[1])
		address=getEventInfo('address', event_list[2])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}
	else:
		address=getEventInfo('address', event_list[len(event_list)-1])
		for event in range(len(event_list)-2):
			waypoints=waypoints+'|'+getEventInfo('address', event_list[event])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}

	r = requests.get('https://maps.googleapis.com/maps/api/directions/json', params=payload)
	travel_response = r.json()
	travel_dict=dict()
	n=1
	step_order=[]
	for leg in travel_response['routes'][0]['legs'][0]['steps']:
		step_num='event'+str(n)
		directions_tofix = leg['html_instructions']
		directions = re.sub('<.*?>','', directions_tofix)
		time = leg['duration']['text']
		distance = leg['distance']['text']
		travel_dict.update({step_num :{'Distance': distance, "Time": time, "directions": directions}})
		n=n+1
		step_order.append(step_num)

	#events
	event_dict=dict()
	event_order=[]
	event_list=getEventList()
	i=1
	for event in event_list:
		eventNum=i
		displayName=getEventInfoDB('name', event)
		eventID=event
		location=getEventInfoDB('city', event)
		date=getEventInfoDB('date', event)
		time=getEventInfoDB('time', event)
		event_dict.update({eventNum :{'Display Name': displayName, "Event ID": eventID, "location": location, "date":date, "time": time}})
		event_order.append(i)
		i=i+1
	return render_template("summary.html", travel_dict=travel_dict, travel_step=step_order, event_dict=event_dict, event_order=event_order)

@app.route("/old_trips", methods=['GET', 'POST'])
@login_required
def old_trips():
	completed_trips=getCompletedTrips()
	trip_dict=dict()
	i=1
	for trip in completed_trips:
		tripNum=i
		trip_id=trip
		event_list=getCompletedEventList(trip_id)
		events_str=getEventListStr(event_list)
		trip_dict.update({tripNum:{'trip id': trip_id, 'string': events_str}})
		i=i+1
	return render_template('chose_trip.html', trip_dict=trip_dict)


@app.route("/finish_trip", methods=['GET', 'POST'])
@login_required
def finish_trip():
	completeTrip()
	return redirect(url_for('home'))


@app.route("/view_old_trip", methods=['GET', 'POST'])
@login_required
def view_old_trip():
	#directions
	trip=request.form.get('trip')
	waypoints= None
	origin_address= getCompletedTripStart(trip)
	event_list= getCompletedEventList(trip)
	if len(event_list)==1:
		address=getEventInfo('address', event_list[0])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving'}
	elif len(event_list)==2:
		waypoint=getEventInfo('address', event_list[0])
		address=getEventInfo('address', event_list[1])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}
	elif len(event_list)==3:
		waypoint=getEventInfo('address', event_list[0])+'|'+getEventInfo('address', event_list[1])
		address=getEventInfo('address', event_list[2])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}
	else:
		address=getEventInfo('address', event_list[len(event_list)-1])
		for event in range(len(event_list)-2):
			waypoints=waypoints+'|'+getEventInfo('address', event_list[event])
		payload = {'key': 'AIzaSyAUw27jBgT6l9Dg-8Y9L6vzbjznmxBOSXM', 'origin': origin_address, 'destination': address, 'mode':'driving', 'waypoints':waypoints}

	r = requests.get('https://maps.googleapis.com/maps/api/directions/json', params=payload)
	travel_response = r.json()
	travel_dict=dict()
	n=1
	step_order=[]
	for leg in travel_response['routes'][0]['legs'][0]['steps']:
		step_num='event'+str(n)
		directions_tofix = leg['html_instructions']
		directions = re.sub('<.*?>','', directions_tofix)
		time = leg['duration']['text']
		distance = leg['distance']['text']
		travel_dict.update({step_num :{'Distance': distance, "Time": time, "directions": directions}})
		n=n+1
		step_order.append(step_num)

	#events
	event_dict=dict()
	event_order=[]
	event_list=getCompletedEventList(trip)
	i=1
	for event in event_list:
		eventNum=i
		displayName=getEventInfoDB('name', event)
		eventID=event
		location=getEventInfoDB('city', event)
		date=getEventInfoDB('date', event)
		time=getEventInfoDB('time', event)
		event_dict.update({eventNum :{'Display Name': displayName, "Event ID": eventID, "location": location, "date":date, "time": time}})
		event_order.append(i)
		i=i+1
	return render_template("old_summary.html", travel_dict=travel_dict, travel_step=step_order, event_dict=event_dict, event_order=event_order)
