import stravalib
from flask import Flask, url_for, session, request, redirect, render_template, send_file
import pandas as pd
import stravalib.model
from os.path import exists
import os
import Functions as fun
import pathlib
import json

# Parameters
numToRetrieve = 20

client = stravalib.client.Client()
STRAVA_CLIENT_ID, STRAVA_SECRET, STRAVA_REFRESH = open('client.secret').read().strip().split(',')

# Instantiate app
app = Flask(__name__, instance_relative_config=True)
app.secret_key = 'secret'
app.config['SESSION_COOKIE_NAME'] = 'StravaVis'


# Home page is the OAUTH2 page.
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


# Doesn't really serve a purpose anymore, I suppose.
@app.route('/redirected')
def redirect_page():
    print("Redirect successful.")
    return redirect(url_for('authorize'))


# Saves all the authorisation tokens (access, refresh and expiry time)
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


# Main lump of code
# 1. Fetches the athlete and basic athlete data
# 2. Checks whether there is already a local file with activity data.
#   - If so, it loads it.
#   - If something's wrong with that data, it remakes it from scratch.
# 3. Once the data have been loaded, it fetches the activity streams.
#   - This should just be done with the activity load right away, and stored in the same DF rather than fetching it again..
# 4. The activity streams include data on polylines, which are used to make the activity map.
#
@app.route('/index')
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
# Create an empty dataframe to store all activity data in later on.
    activityDF = pd.DataFrame(columns=activityCols)

# Fetch the athlete and their data.
    curr_athlete = client.get_athlete()
    # print("Athlete name is ", curr_athlete.firstname, curr_athlete.lastname,
    #      "\nGender: ", curr_athlete.sex, "\nCity: ",
    #      curr_athlete.city, ", ", curr_athlete.country)
    allShoes = curr_athlete.shoes


# Displays some basic info for the equipment.
    # data = []
    # dataColumns = ['id', 'name', 'distance', 'primary', 'brand_name', 'model_name', 'description', 'resource_state']
    # for equipment in allShoes:
    #     equipDict = equipment.to_dict()
    #     newData = [equipDict.get(x) for x in dataColumns]
    #     data.append(newData)
    # equipDF = pd.DataFrame(data, columns=dataColumns)
    # print(equipDF.head())

    csvPath = pathlib.Path(__file__).parent / "/data/localStrava.csv"

# Check if there's already a local csv with all the relevant data in it.
    if exists(csvPath):
        print("Local data file found.")
        activityDF = pd.read_csv(csvPath, sep=';', encoding='utf-8')
        statsDict = curr_athlete.stats.to_dict()
        numRuns = statsDict['all_run_totals']['count']
        print("Total number of runs found: ", numRuns)
        if activityDF.empty:
            print("Loaded dataframe was empty")
    if exists(csvPath):
        latestActivity = activityDF.loc[activityDF.shape[0]-1, 'start_date'].rstrip("+00:00") + "Z"
        if len(latestActivity) != 20 and activityDF.columns == activityCols:
            print("You messed up the spreadsheet. Re-importing all data.")
            latestActivity = "2010-01-01T00:00:00Z"
            os.remove(csvPath)
    else:
        latestActivity = "2010-01-01T00:00:00Z"

# If there are too few activities in the loaded data, it fetches some new activities.
    if activityDF.shape[0] < numToRetrieve:
        print("Retrieving activities since: ", latestActivity)
        activities = client.get_activities(after=latestActivity, limit=numToRetrieve)
        activityData = []
        for activity in activities:
            activityDict = activity.to_dict()
            newData = [activityDict.get(x) for x in activityCols]
            activityData.append(newData)
        latestDF = pd.DataFrame(activityData, columns=activityCols)
        activityDF = pd.concat([activityDF, latestDF], axis=0)
        activityDF['distance'] = activityDF['distance'] / 1000
        activityDF.to_csv(csvPath, sep=';', encoding='utf-8')

    typeList = ['distance', 'time', 'latlng', 'altitude']

    activityDF = activityDF.loc[:, ~activityDF.columns.str.contains('^Unnamed')]

    counter = 0
    polyLineList = []
    distanceList = []
    for x in activityDF['id']:
        counter += 1
        print("Making the map for activity # %d" % counter)
        activityStream = fun.getStream(client, typeList, x)
        streamDF = fun.storeStream(typeList, activityStream)
        if streamDF.shape[0] != 0:
            streamPoly = fun.makePolyLine(streamDF)
            polyLineList.append(streamPoly)
            distanceList.append(activityDF.loc[counter-1, 'distance'])

    activityMap = fun.plotMap(polyLineList, 0, distanceList)
    indexPath = pathlib.Path(__file__).parent / "/templates/index.html"

    activityJSON = activityDF.to_json(orient='index')
    parsed = json.loads(activityJSON)

    return render_template('index.html', activityData=parsed)


@app.route('/example0.html')
def show_map():
    return send_file('./templates/example0.html')


class StravaOAUTH:
    def __init__(self, passed_id, passed_secret, passed_uri, passed_scope):
        self.client_id = passed_id
        self.client_secret = passed_secret
        self.redirect_uri = passed_uri
        self.scope = []
