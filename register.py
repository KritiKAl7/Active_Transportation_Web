from __future__ import print_function
import httplib2
import os
import pyrebase
import argparse
import string
import random
import smtplib
import textwrap

from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart

import configfile

# try:
#     import argparse
#     flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
# except ImportError:
#     flags = None
flags = None
# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'


def get_credentials():
	"""Gets valid user credentials from storage.

	If nothing has been stored, or if the stored credentials are invalid,
	the OAuth2 flow is completed to obtain the new credentials.

	Returns:
		Credentials, the obtained credential.
	"""
	home_dir = os.path.expanduser('~')
	credential_dir = os.path.join(home_dir, '.credentials')
	if not os.path.exists(credential_dir):
		os.makedirs(credential_dir)
	credential_path = os.path.join(credential_dir,
								   'sheets.googleapis.com-python-quickstart.json')

	store = oauth2client.file.Storage(credential_path)
	credentials = store.get()
	if not credentials or credentials.invalid:
		flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
		flow.user_agent = APPLICATION_NAME
		if flags:
			credentials = tools.run_flow(flow, store, flags)
		else: # Needed only for compatibility with Python 2.6
			#credentials = tools.run(flow, store)
			credentials = tools.run_flow(flow, store, flags)
		print('Storing credentials to ' + credential_path)
	return credentials


#Generate password from upper class letters and numbers
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.SystemRandom().choice(chars) for _ in range(size))

#Read raw user data from the google sheet with sheetId in configfile.py
def readFromSheet(credentials):
	http = credentials.authorize(httplib2.Http())
	discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
					'version=v4')
	service = discovery.build('sheets', 'v4', http=http,
							  discoveryServiceUrl=discoveryUrl)

	spreadsheetId = configfile.sheetId
	rangeName = 'Form Responses 1!A1:V'
	result = service.spreadsheets().values().get(
		spreadsheetId=spreadsheetId, range=rangeName).execute()
	values = result.get('values', [])
	res = []
	if not values:
		print('No data found.')
	else:
		for row in values[1:]:
			"""
			User structure:
			{name: "", email: "", phone:""
			address:"", children: [{name:"", grade:"", school:"" }, ...]}
			"""
			user = {}
			user["name"] = str(row[1])
			user["email"] = str(row[2])
			user["phone"] = str(row[3])
			user["address"] = str(row[4])
			user["children"] = []
			for i in range(5, len(row) - 2, 3):
				if row[i]:
					child = {}
					child["name"] = str(row[i])
					child["school"] = str(row[i+1])
					child["grade"] = str(row[i+2].split(" ")[-1])
					user["children"].append(child)
			res.append(user)
	return res 

def registerUser(userData, firebase, noEmail):
	userInfo = open('parentInfo.dat', 'w+')
	auth = firebase.auth()
	finishedUsers = []
	registeredUsers = []
	for user in userData:
		password = id_generator()
		try:
			result = auth.create_user_with_email_and_password(user["email"], password)
		except Exception , e:
			errorMessage = e[1].split(" ")
			error = "UNKNOWN_ERROR"
			for i in range(len(errorMessage)):
				if str(errorMessage[i]) == '"message":':
					error = str(errorMessage[i+1])
			userInfo.write(user["email"] + "   " + error + '\n')
			print ("An error happened during registering user with email: " + \
				user["email"] + ", check output file for details")
		else:
			finishedUsers.append([user["name"], user["email"], password])
			user["uID"] = result["localId"]
			registeredUsers.append(user)
			userInfo.write(user["email"] + "   " + password + "   " + user["uID"] + '\n')
	userInfo.close()
	print ("Finished! see parentInfo.dat for results")
	if not noEmail and finishedUsers:
		sendEmails(finishedUsers)
	return registeredUsers

def sendEmails(userEmails):
	print ("sending emails to users...")
	sender = "walkingschoolbusclaremont@gmail.com"
	count = 0
	for user in userEmails:
		message = \
"""From: Walking School Bus team <walkingschoolbusclaremont@gmail.com>
To: %s <%s>
Subject: Welcome to Walking School Bus!

Hello Dear %s:

	Thank you for your interest in the walking school bus! Here is your temporary password for the mobile application:
	%s
	Please use the password to login and change the password immediatly.
	(For Android phones, push the button on right top corner and choose settings; For iPhones, push the settings button on left bottom corner.)
	Thank you again for your help creating a cleaner and safer environment for kids in Claremont!

Best,
Walking School Bus Team
		""" % (user[0], user[1], user[0], user[2],)
		
		try:
			""" Use the walkingschoolbusclaremont@gmail.com to send emails
			"""
			smtpObj = smtplib.SMTP('smtp.gmail.com:587')
			smtpObj.ehlo()
			smtpObj.starttls()
			smtpObj.login(configfile.projectEmail, configfile.projectPassword)
			smtpObj.sendmail(sender, user[1], message)
			#Python debugging smtp server: python -m smtpd -n -c DebuggingServer localhost:1025
			# smtpObj = smtplib.SMTP("localhost:1025")
			# smtpObj.sendmail(sender, user[1], message)
			smtpObj.quit()
			print ("Successfully sent email to %s" % (user[1]))
			count += 1
		except Exception, e:
			print ("Error while sending email to %s" % (user[1]), e)
	print ("Finished sending email to %s users!" % (count))


#Store the user infomation to firebase
def updateDatabase(registeredUsers, firebase):
	db = firebase.database()
	auth = firebase.auth()
	userCount = 0
	for user in registeredUsers:
		userData = {}
		userData["name"] = user["name"]
		userData["email"] = user["email"]
		userData["contactInfo"] = user["phone"]
		userData["address"] = user["address"]
		userData["isStaff"] = False
		try:
			db.child("users").child(user["uID"]).set(userData)
		except Exception, e:
			print ("Error when adding user %s to database" % (user["email"]), e)
		else:
			userCount += 1
		childrenIDs = {}
		for child in user["children"]:
			childData = {}
			childData["name"] = child["name"]
			childData["school"] = child["school"]
			childData["parentID"] = user["uID"]
			childData["grade"] = child["grade"]
			childData["routeID"] = "not assigned yet"
			db.child("students").push(childData)
			for kid in db.child("students").get().each():
				if kid.val()["name"] == child["name"] and kid.val()["parentID"] == user["uID"]:
					childID = kid.key()
			childrenIDs[childID] = child["name"]
		try:
			db.child("users").child(user["uID"]).child("childrenIDs").set(childrenIDs)
		except Exception, e:
			print ("Error when adding user %s's kids to database" % (user["email"]), e)
	return userCount



def main(noemail):
	"""
	IMPORTANT: Pleas don't add the configfile.py and the json credential
	files to gitHub
	"""
	firebase = pyrebase.initialize_app(configfile.config)

	print ("Getting credentials...")
	credentials = get_credentials()
	print("Done")
	print ("Reading user data from spread sheet...")
	userData = readFromSheet(credentials)
	print ("Done")
	if not noemail:
		print ("Register user and send email...")
		registeredUsers = registerUser(userData, firebase, False)
	else:
		print ("Register user and do not send email...")
		registeredUsers = registerUser(userData, firebase, True)
	if registeredUsers:
		print ("Adding user infomation to the database...")
		count = updateDatabase(registeredUsers, firebase)
		print ("Finished! Successfully added %s users to the database" % (str(count)))
	else:
		print ("No new user added")

	


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("--noemail", help="Don't send emails to users", action="store_true", default=False)
	args = parser.parse_args()
	print (parser.parse_args())
	main(args.noemail)

