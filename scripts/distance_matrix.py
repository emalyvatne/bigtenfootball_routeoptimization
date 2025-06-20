import pandas as pd
from geopy.distance import geodesic
import os

# set main and output directory
main_dir = os.getcwd()
output_dir = f"{main_dir}/outputs"

# join each team name with abbreviations table to get tricode
df = pd.read_csv(f"{output_dir}/arena_info.csv")
TEAMS = sorted(df['Institution'].to_list())


# group latitude and longitude info into coordinate tuples
df['Coords'] = df.apply(lambda x: (x['Latitude'], x['Longitude']), axis=1)

# manipulate object type from dataframe -> dictionary
coords_dict = df.set_index('Institution')[['Coords']].to_dict(orient='index')

# compute distance between each arena
miles = []
for t in TEAMS:
    for tt in TEAMS:
        distance = geodesic(coords_dict[t]['Coords'], coords_dict[tt]['Coords']).miles
        miles.append([t, tt, distance])
mile_df = pd.DataFrame(miles, columns = ['src', 'dest', 'miles'])
mile_df.to_csv(f"{output_dir}/mile_matrix.csv", index=False)

# compute distance between each arena
miles = []
for t in TEAMS:
    distance = [geodesic(coords_dict[t]['Coords'], coords_dict[tt]['Coords']).miles for tt in TEAMS]
    miles.append([t, *distance])
mile_df = pd.DataFrame(miles, columns = ['', *TEAMS])
mile_df

# export mile matrix
mile_df.to_csv(f"{output_dir}/mile_matrix_wide.csv", index=False)