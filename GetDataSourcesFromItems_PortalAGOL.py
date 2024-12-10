
"""
This script creates a csv of items from AGOl or Portal. It gets the iteminfo from the
GIS content search and then looks at each data url within each item - intending to 
identify old data sources etc.

Can also be run in cmd line with the following:

    GetItems_PortalAgol.py --site agol --out_dir "C:\directory..." --out_name "Filename.csv"

    note - --site accepts strings "portal" or "agol" only

"""

## TODO: add item type paramenter ie webmap, application etc

import Authenticate_ArcGISServer  # custom script
import click
import os
import arcpy
from arcgis.gis import GIS
import pandas as pd
import datetime

def find_urls(data):
    urls = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'url':
                urls.append(value)
            elif isinstance(value, (dict, list)):
                urls.extend(find_urls(value))
    elif isinstance(data, list):
        for item in data:
            urls.extend(find_urls(item))
    return urls

def extract_relevant_info(content):
    item_list = []
    for item in content:
        try:
            url_list = []

            # Use function to find all URLs in item.get_data
            data = item.get_data()
            urls = find_urls(data)

            # Convert Unix time to 'dd/mm/yyyy' format
            created_date = datetime.datetime.fromtimestamp(item.created / 1000).strftime('%d/%m/%Y')
            modified_date = datetime.datetime.fromtimestamp(item.modified / 1000).strftime('%d/%m/%Y')

            # Append all info to a list
            item_info = {
                'title': item.title,
                'id': item.id,
                'type': item.type,
                'owner': item.owner,
                'created': created_date,
                'modified': modified_date,
                # 'last_viewed_unix': item.lastViewed, # Added to AGOL Nov 2022 
                'views': item.numViews,
                'item_url': item.url,
                'data_urls': urls
            }
            item_list.append(item_info)
            print(fr'{item} ADDED TO LIST...')
        except Exception as e:
            print(f"Error processing item '{item.title}': {str(e)}")
    return item_list

@click.command()
@click.option('--site', required=True, type=str, help='Specify the site: agol or portal.')
@click.option('--out_dir', type=click.Path(exists=True), default=None, help='Output directory for the CSV file.')
@click.option('--out_name', default=None, help='Output filename for the CSV file. Please specify extension')

def main(site, out_dir, out_name):
    # Determine site URL based on user input
    if site == 'agol':
        site_url = r"..."
    elif site == 'portal':
        site_url = r"..."
    else:
        arcpy.AddError("Invalid input! Please enter either 'agol' or 'portal'.")
        return

    default_dir = r'...'
    out_dir = out_dir if out_dir else default_dir

    date_now = pd.Timestamp.today().strftime('%Y%m%d')
    default_name = f"{site}_items_{date_now}.csv"
    out_name = out_name if out_name else default_name

    username, password = Authenticate_ArcGISServer.get_creds(site_url)

    # Log in to GIS site
    gis = GIS(site_url, username, password, verify_cert=False)

    # Get web maps
    content = gis.content.search('*', item_type='Web Map', max_items=-1)

    # Extracting relevant information
    item_list = extract_relevant_info(content)

    # List to pandas df
    df = pd.DataFrame(item_list)
    # Explode data URLs
    df_explode = df.explode('data_urls')

    # Save
    outfile = os.path.join(out_dir, out_name)
    df_explode.to_csv(outfile, index=False)
    print(f"\nScript finished. Saved: {outfile}")

if __name__ == '__main__':
    main()
