import pandas as pd
from os.path import exists
import streamlit

activitiesAlreadyStored = exists("localStrava.csv")

activityDF = pd.DataFrame()

if activitiesAlreadyStored:
    print("Local data file found.")
    activityDF = pd.read_csv("localStrava.csv", sep=';', encoding='utf-8')

streamlit.table(activityDF)
