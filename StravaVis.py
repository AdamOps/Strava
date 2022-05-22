import datetime

import stravalib
import pandas as pd
from flask import request, session
import stravalib.model
from os.path import exists
import classesStravaVis
import streamlit

client = stravalib.client.Client()
STRAVA_CLIENT_ID, STRAVA_SECRET, STRAVA_REFRESH = open('client.secret').read().strip().split(',')

strava_oauth = classesStravaVis.StravaOAUTH(STRAVA_CLIENT_ID,
                            STRAVA_SECRET,
                            'http://localhost:8051/',
                            ['read_all', 'profile:read_all', 'activity:read_all'])

authorize_url = client.authorization_url(client_id=STRAVA_CLIENT_ID,
                                             redirect_uri='http://localhost:5000/authorize',
                                             approval_prompt='auto',
                                             scope=['read_all', 'profile:read_all', 'activity:read_all'])

authorization_code = request.args.get('code')

token_response = client.exchange_code_for_token(client_id=STRAVA_CLIENT_ID,
                                                    client_secret=STRAVA_SECRET,
                                                    code=authorization_code)
session["token_info"] = token_response['access_token']
session["refresh_token"] = token_response['refresh_token']
session["expires_at"] = token_response['expires_at']
activitiesAlreadyStored = exists("localStrava.csv")

activityDF = pd.DataFrame()

if activitiesAlreadyStored:
    print("Local data file found.")
    activityDF = pd.read_csv("localStrava.csv", sep=';', encoding='utf-8')
    if activityDF.empty:
        print("Loaded dataframe was empty")

curr_athlete = client.get_athlete()
print("Athlete name is ", curr_athlete.firstname, curr_athlete.lastname, "\nGender: ", curr_athlete.sex, "\nCity: ",
        curr_athlete.city, ", ", curr_athlete.country)
allShoes = curr_athlete.shoes
print("Number of shoes: ", len(allShoes))
data = []
dataColumns = ['id', 'name', 'distance', 'primary', 'brand_name', 'model_name', 'description', 'resource_state']
for equipment in allShoes:
    equipDict = equipment.to_dict()
    newData = [equipDict.get(x) for x in dataColumns]
    data.append(newData)
equipDF = pd.DataFrame(data, columns=dataColumns)
print(equipDF.head())

activityCols = ['id',
                'name',
                'description',
                'athlete_count',
                'type',
                'distance',
                'moving_time',
                'total_elevation_gain',
                'elev_high',
                'elev_low',
                'average_speed',
                'max_speed',
                'gear_id',
                'has_heartrate',
                'workout_type',
                'calories']

if not activitiesAlreadyStored:
    activities = client.get_activities(limit=25)
    print(type(activities))
    activityData = []
    for activity in activities:
        activityDict = activity.to_dict()
        newData = [activityDict.get(x) for x in activityCols]
        activityData.append(newData)
    activityDF = pd.DataFrame(activityData, columns=activityCols)
    activityDF['distance'] = activityDF['distance']/1000
    activityDF.to_csv("localStrava.csv", sep=';', encoding='utf-8')
    print("No existing strava file found. Created a new one.")

streamlit.table(activityDF)
