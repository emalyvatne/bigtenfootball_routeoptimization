import os
import pandas as pd
# pd.options.display.max_rows = None
from pulp import *

main_dir = os.getcwd()
output_dir = f"{main_dir}/outputs"

schedule = pd.read_csv(f"{output_dir}/schedule.csv")
schedule = schedule.rename(columns={"Unnamed: 7": "LocationDesignation"})
date_df = schedule.set_index('Date')
mile_matrix_wide = pd.read_csv(f"{output_dir}/mile_matrix_wide.csv")

mile_matrix_wide = mile_matrix_wide.rename(columns={"Unnamed: 0": "source"})
mile_matrix_long = mile_matrix_wide.melt(id_vars="source", var_name="destination", value_name="miles")

# ----- map mile matrix school names to the college football schedule -----
matrixlist_to_team = {
    'University of Illinois Urbana-Champaign': 'Illinois',
    'Indiana University Bloomington': 'Indiana',
    'University of Iowa': 'Iowa',
    'University of Maryland, College Park': 'Maryland',
    'University of Michigan': 'Michigan',
    'Michigan State University': 'MichiganState',
    'University of Minnesota Twin Cities': 'Minnesota',
    'University of Nebraska-Lincoln': 'Nebraska',
    'Northwestern University': 'Northwestern',
    'The Ohio State University': 'OhioState',
    'University of Oregon': 'Oregon',
    'Pennsylvania State University': 'PennState',
    'Purdue University': 'Purdue',
    'Rutgers, The State University of New Jersey, New Brunswick': 'Rutgers',
    'University of Southern California': 'SouthernCalifornia',
    'University of California, Los Angeles': 'UCLA',
    'University of Washington': 'Washington',
    'University of Wisconsin-Madison': 'Wisconsin'
}
mile_matrix_long['source'] = mile_matrix_long['source'].map(matrixlist_to_team)
mile_matrix_long['destination'] = mile_matrix_long['destination'].map(matrixlist_to_team)

# ----- clean the schedule -----
# rename columns
schedule.columns = ['Unnamed', 'Rk', 'Date', 'Time', 'Day', 'Winner', 'Pts', 'LocationDesignation', 'Loser', 'Pts.1', 'Notes']
# create home/away assignment
schedule['Home'] = schedule.apply(
    lambda row: row['Loser'] if row['LocationDesignation'] == '@' else row['Winner'],
    axis=1
)
schedule['Away'] = schedule.apply(
    lambda row: row['Winner'] if row['LocationDesignation'] == '@' else row['Loser'],
    axis=1
)

# assign points
schedule['HomePts'] = schedule.apply(
    lambda row: row['Pts.1'] if row['LocationDesignation'] == '@' else row['Pts'],
    axis=1
)
schedule['AwayPts'] = schedule.apply(
    lambda row: row['Pts'] if row['LocationDesignation'] == '@' else row['Pts.1'],
    axis=1
)

# select and order desired columns
schedule = schedule[['Rk', 'Date', 'Time', 'Day', 'Home', 'HomePts', 'Away', 'AwayPts', 'Notes']]
# clean the Home and Away column to remove rankings
schedule['Home'] = schedule['Home'].str.replace('\xa0', '', regex=False).str.replace(r"[ ()\d]", "", regex=True)
schedule['Away'] = schedule['Away'].str.replace('\xa0', '', regex=False).str.replace(r"[ ()\d]", "", regex=True)

# There are 17 Big Ten teams and 17 locations to visit
TEAMS = ['Home', *sorted(list(schedule['Home'].unique()))]

# There are 25 game dates [len(schedule['Date'].unique())] in the 2024 season
DATES = [0, *list(schedule['Date'].unique())]

# Define Problem  

prob = LpProblem("Matrix Problem",LpMinimize)
# Creating a Set of Variables
# date, source, desetination
choices = LpVariable.dicts("Interview",(DATES,TEAMS,TEAMS), cat='Binary')

# Added arbitrary objective function
prob += 0, "Arbitrary Objective Function"

# ---------------- CONSTRAINTS ------------------------

# ensure each arena is departed from exactly 1 time
for t2 in TEAMS:
    prob += lpSum([choices[d][t1][t2] for d in DATES[1:] for t1 in TEAMS]) == 1, ""

# ensure each arena is visited exactly 1 time
for t1 in TEAMS:
    prob += lpSum([choices[d][t1][t2] for d in DATES[1:] for t2 in TEAMS]) == 1, ""

# minimize total number of visits
prob += lpSum([choices[d][t1][t2] for d in DATES[1:] for t1 in TEAMS for t2 in TEAMS if t1 != t2]) <= 33

# start from home and end at home
prob +=lpSum([choices[d]['Home'][t2] for t2 in TEAMS[1:] for d in DATES[1:4]]) == 1
prob +=lpSum([choices[d][t1]['Home'] for t1 in TEAMS[1:] for d in DATES[-1:]]) == 1

# make sure visits are played on home team dates
for d in DATES[1:]:
    for t2 in TEAMS[1:]:
        for t1 in TEAMS:
            if schedule[(schedule['Date'] == d) & (schedule['Home'] == t2)].shape[0] == 0:
                prob += choices[d][t1][t2] == 0, ""

    prob += lpSum([choices[d][t1][t2] for t1 in TEAMS for t2 in TEAMS]) <= 1, ""

for d in DATES:
    for t1 in TEAMS[1:]:
        for t2 in TEAMS[1:]:
            if t1 == t2:
                prob += choices[d][t1][t2] == 0, ""

# Ensure that visits are sequential by dates
for i, d in enumerate(DATES[1:-1]):
    for t1 in TEAMS:
        for t2 in TEAMS[1:]:
            if t1 != t2:
                prob += choices[DATES[i]][t1][t2] <= lpSum([choices[d2][t2][t3] for d2 in DATES[i+1:i+4] for t3 in TEAMS if t3 != t2]), f""

for i, d in enumerate(DATES[2:]):
    for t1 in TEAMS[1:]:
        for t2 in TEAMS:
            if t1 != t2:
                prob += choices[DATES[i]][t1][t2] <= lpSum([choices[d2][t3][t1] for d2 in DATES[i-4:i] for t3 in TEAMS if t3 != t1]), f""

# Minimize travel distance for each segment
if (t1, t2) in mile_matrix_long.index:
    miles = mile_matrix_long.loc[(t1, t2), 'miles']  
    if isinstance(miles, pd.Series):
        miles = miles.iloc[0]
        
    prob += choices[d][t1][t2] * miles <= 1100

    # 1.  Build a truly unique MultiIndex (strip stray spaces/ \xa0 first)
mile_matrix_long = (
    mile_matrix_long
        .assign(source=lambda d: d["source"].str.strip(),      # <- kills \xa0 & spaces
                destination=lambda d: d["destination"].str.strip())
        .drop_duplicates(["source", "destination"])            # guarantee uniqueness
        .set_index(["source", "destination"])
        .sort_index()
)

# 2.  Convert the miles column to a plain Python dict for O(1) scalar lookup
distance_lookup = mile_matrix_long["miles"].to_dict()

# 3.  Build the algebraic expression once so you can re-use it
total_distance = lpSum(
    choices[d][t1][t2] * distance_lookup[(t1, t2)]
    for d  in DATES[1:]            # skip dummy element 0
    for t1 in TEAMS[1:]            # "
    for t2 in TEAMS[1:] if t1 != t2
)

# 4.  Tell PuLP what you actually want
prob += total_distance, "MinimizeTravelDistance"   # <- the objective
prob += total_distance <= 14_000, "TravelDistanceLimit"  # <- optional hard cap

# 5.  Solve
prob.solve()
print("Status:", LpStatus[prob.status])
print("Best total miles:", value(total_distance))

debug = ""
if LpStatus[prob.status] == 'Optimal':
    print('solved problem')
    matrix = []
    for t2 in TEAMS:
        row = []
        for t1 in TEAMS:
            value = 0
            for d in DATES:
                if choices[d][t1][t2].varValue == 1:
                    value = d
            row.append(value)

        matrix.append(row)

    matrix_df = pd.DataFrame(matrix, columns=TEAMS)
    matrix_df.index = TEAMS

else:
    print('Fail')

# ----- clean the final schedule up a little bit -----

data = []
df = matrix_df.copy()
solution_long = df.melt(id_vars="destination", var_name="source", value_name="date")
solution_long = solution_long[solution_long['date'] != '0']
solution_long['date'] = (
    pd.to_datetime(
        solution_long['date'].str.strip(),
        format='%b %d, %Y',
        errors='coerce'
    )
)
solution_long = solution_long.sort_values('date', ascending=True)
solution_long = solution_long[["source", "destination", "date"]]
