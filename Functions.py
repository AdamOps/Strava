import stravalib
import pandas as pd
import folium
import webbrowser
import random


def getStream(client, typeList, activityID):
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
                             width='100%', tiles='Stamen Terrain')
    folium.TileLayer('cartodbpositron').add_to(activityMap)
    folium.TileLayer('cartodbdark_matter').add_to(activityMap)
    folium.TileLayer('Stamen Toner').add_to(activityMap)

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