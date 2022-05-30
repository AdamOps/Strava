import stravalib
from flask import Flask, url_for, session, request, redirect
import pandas as pd
import stravalib.model
from os.path import exists
import os
import ast
import folium
import webbrowser
import random

# Parameters
numToRetrieve = 10

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
    # print("Athlete name is ", curr_athlete.firstname, curr_athlete.lastname,
    #      "\nGender: ", curr_athlete.sex, "\nCity: ",
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




    typeList = ['distance', 'time', 'latlng', 'altitude']

    counter = 0
    polyLineList = []
    distanceList = []
    for x in activityDF['id']:
        counter += 1
        print("Making the map for activity # %d" % counter)
        activityStream = getStream(typeList, x)
        streamDF = storeStream(typeList, activityStream)
        streamPoly = makePolyLine(streamDF)
        polyLineList.append(streamPoly)
        distanceList.append(activityDF.loc[counter-1, 'distance'])

    plotMap(polyLineList, 0, distanceList)

    return 'All done!'


def getStream(typeList, activityID):
    activityStream = client.get_activity_streams(activityID, types=typeList, resolution='medium', series_type='distance')
    return activityStream


def storeStream(typeList, activityStream):
    df = pd.DataFrame()
    # Write each row to a dataframe
    for item in typeList:
        if item in activityStream.keys():
            df[item] = pd.Series(activityStream[item].data, index=None)
    return df


def makePolyLine(df):
    latLongList = []
    for x in df['latlng']:
        latLongList.append(tuple(x))
    return latLongList


def plotMap(activityPolyLine, num, distanceList):
    activityMap = folium.Map(location=[activityPolyLine[0][0][0], activityPolyLine[0][0][1]], zoom_start=14,
                             width='100%')
    folium.TileLayer('cartodbpositron').add_to(activityMap)
    folium.TileLayer('cartodbdark_matter').add_to(activityMap)
    if len(activityPolyLine) == 1:
        folium.PolyLine(activityPolyLine).add_to(activityMap)
        activityMap.save(r'example' + str(num) + '.html')
        webbrowser.open(r'example' + str(num) + '.html')
    else:
        baseColor = "#FF0000"
        counter = 1
        for poly in activityPolyLine:
            folium.PolyLine(poly, color=baseColor).add_to(folium.FeatureGroup(name="Run #" + str(counter) + ", Distance: " + str(distanceList[counter-1])).add_to(activityMap))
            baseColor = "#" + "%06x" % random.randint(0, 0x888888)
            counter += 1

        folium.LayerControl(collapsed=False).add_to(activityMap)
        activityMap.save(r'example' + str(num) + '.html')
        webbrowser.open(r'example' + str(num) + '.html')
    return


class StravaOAUTH:
    def __init__(self, passed_id, passed_secret, passed_uri, passed_scope):
        self.client_id = passed_id
        self.client_secret = passed_secret
        self.redirect_uri = passed_uri
        self.scope = []
