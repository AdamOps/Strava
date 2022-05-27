import datetime

import stravalib
from flask import Flask, url_for, session, request, redirect
import pandas as pd
import stravalib.model
from os.path import exists
import os
import ast
import streamlit
import folium
import webbrowser
import polyline

## Parameters
numToRetrieve = 5

client = stravalib.client.Client()
STRAVA_CLIENT_ID, STRAVA_SECRET, STRAVA_REFRESH = open('client.secret').read().strip().split(',')

app = Flask(__name__, instance_relative_config=True)
app.secret_key = 'secret'
app.config['SESSION_COOKIE_NAME'] = 'StravaVis'


@app.route('/')
def login():
    strava_oauth = StravaOAUTH(STRAVA_CLIENT_ID,
                               STRAVA_SECRET,
                               'http://localhost:5000/',
                               ['read_all', 'profile:read_all', 'activity:read_all'])

    authorize_url = client.authorization_url(client_id=STRAVA_CLIENT_ID,
                                             redirect_uri='http://localhost:5000/authorize',
                                             approval_prompt='auto',
                                             scope=['read_all', 'profile:read_all', 'activity:read_all'])

    # print(authorize_url)
    return redirect(authorize_url)


@app.route('/redirected')
def redirect_page():
    print("Redirect successful.")
    return redirect(url_for('authorize'))


@app.route('/authorize')
def authorize():
    authorization_code = request.args.get('code')

    token_response = client.exchange_code_for_token(client_id=STRAVA_CLIENT_ID,
                                                    client_secret=STRAVA_SECRET,
                                                    code=authorization_code)
    session["token_info"] = token_response['access_token']
    session["refresh_token"] = token_response['refresh_token']
    session["expires_at"] = token_response['expires_at']

    return redirect(url_for('get_all_activities'))


@app.route('/get_activities')
def get_all_activities():
    localFileComplete = False

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
                    'calories',
                    'start_date',
                    "segment_efforts",
                    "gear",
                    "map",
                    'start_latlng',
                    'end_latlng'
                    ]

    activityDF = pd.DataFrame(columns=activityCols)


    curr_athlete = client.get_athlete()
    # print("Athlete name is ", curr_athlete.firstname, curr_athlete.lastname, "\nGender: ", curr_athlete.sex, "\nCity: ",
    #      curr_athlete.city, ", ", curr_athlete.country)
    allShoes = curr_athlete.shoes

    # data = []
    # dataColumns = ['id', 'name', 'distance', 'primary', 'brand_name', 'model_name', 'description', 'resource_state']
    # for equipment in allShoes:
    #     equipDict = equipment.to_dict()
    #     newData = [equipDict.get(x) for x in dataColumns]
    #     data.append(newData)
    # equipDF = pd.DataFrame(data, columns=dataColumns)
    # print(equipDF.head())

    if exists("localStrava.csv"):
        print("Local data file found.")
        activityDF = pd.read_csv("localStrava.csv", sep=';', encoding='utf-8')
        statsDict = curr_athlete.stats.to_dict()
        numRuns = statsDict['all_run_totals']['count']
        print("Total number of runs found: ", numRuns)
        if activityDF.empty:
            print("Loaded dataframe was empty")
    latestActivity = ""
    if exists("localStrava.csv"):
        latestActivity = activityDF.loc[activityDF.shape[0]-1, 'start_date'].rstrip("+00:00") + "Z"
        if len(latestActivity) != 20 and activityDF.columns == activityCols:
            print("You messed up the spreadsheet. Re-importing all data.")
            latestActivity = "2010-01-01T00:00:00Z"
            os.remove("localStrava.csv")
    else:
        latestActivity = "2010-01-01T00:00:00Z"

    if activityDF.shape[0] < numToRetrieve:
        print("Retrieving activities since: ", latestActivity)
        activities = client.get_activities(after=latestActivity, limit=5)
        activityData = []
        for activity in activities:
            activityDict = activity.to_dict()
            newData = [activityDict.get(x) for x in activityCols]
            activityData.append(newData)
        latestDF = pd.DataFrame(activityData, columns=activityCols)
        activityDF = pd.concat([activityDF, latestDF], axis=0)
        activityDF['distance'] = activityDF['distance'] / 1000
        activityDF.to_csv("localStrava.csv", sep=';', encoding='utf-8')

    # print(activityDF.head())
    # print(activityDF['id'][0])

    # DUPA = client.get_activity_streams(898909762, types=['distance', 'time', 'latlng', 'altitude'], resolution='medium')

    start_latlng = ast.literal_eval(activityDF['start_latlng'][0])
    end_latlng = ast.literal_eval(activityDF['end_latlng'][0])
    print("Start lat: ", start_latlng[0], ", start long: ", start_latlng[1])

    mapDict = ast.literal_eval(activityDF['map'][0])
    newPolyLine = polyline.decode(mapDict['summary_polyline'])

    activityMap = folium.Map(location=[start_latlng[0], start_latlng[1]], zoom_start=14, width='100%')

    folium.PolyLine(newPolyLine).add_to(activityMap)
    activityMap.save(r'c:\temp\example.html')
    webbrowser.open(r'c:\temp\example.html')

    return 'Got the athlete and retrieved the activities.'


class StravaOAUTH:
    def __init__(self, passed_id, passed_secret, passed_uri, passed_scope):
        self.client_id = passed_id
        self.client_secret = passed_secret
        self.redirect_uri = passed_uri
        self.scope = []
