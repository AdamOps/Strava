# Strava

*Purpose*
- Load athlete data
  - Name
  - Gender
  - City
  - Amount of equipment
- Load gear data
  - All shoes and bikes
  - Names/distance/description of gear
- Load activity data
  - Provide summary statistics of activities
    - Length
    - Duration
    - Elevation gain
    - Speed distribution
    - Heart rate distribution
  - Perform statistical analysis based on past activities
    - Generate prediction of race time
      - Deep neural network might be an option. Every 1km can be a data point, so that there's plenty of training/validation/test data
