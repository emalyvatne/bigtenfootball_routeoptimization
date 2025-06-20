import pandas as pd
from bs4 import BeautifulSoup
import requests
pd.options.display.max_columns = None
import os

# set main and output directory
main_dir = os.getcwd()
output_dir = f"{main_dir}\outputs"
 
# get URL
page = requests.get("https://www.sports-reference.com/cfb/conferences/big-ten/2024-schedule.html")
 
# scrape webpage
soup = BeautifulSoup(page.content, 'html.parser')
 
# grab table values
table = soup.find('table', id="schedule")
tbody = table.find('tbody')
data = []
for i, row in enumerate(tbody.findAll('tr')):
    if row.find('th').getText().strip() == 'Rk':
        continue
    data.append([row.find('th').getText().strip(), *[col.getText().strip() for col in row.findAll('td')]])
df = pd.DataFrame(data, columns = ['Rk', 'Date', 'Time', 'Day', 'Winner', 'Pts', '', 'Loser', 'Pts', 'Notes'])

# preview and save to csv
print(f'There were {df.shape[0]} Big Ten football games this season')
# df.to_csv(f"{output_dir}/schedule.csv")