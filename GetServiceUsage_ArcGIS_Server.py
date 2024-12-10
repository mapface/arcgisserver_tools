#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# This script gets quick reports for Requests to a Service at the directory level, the script will get the site details from gis_sites.json and requires an administration account to successfully run.
# Can also be run in cmd line with the following:

#     GetServiceUsage_ArcGIS_Server.py --out_dir "C:\directory..." --out_name "Filename.csv" --gis_sites_json "C:\...\test_json.json" --server_type "map"


import pandas as pd
import os
import collections
import click
import json
from arcgis.gis.server import Server
import Authenticate_ArcGISServer  # custom script

# Get Quick Reports from Server
def get_quick_reports(admin_url, key, username, password):
    temp_list = []

    # Create a Server instance (stand-alone/unfederated ArcGIS Server site)
    server = Server(admin_url, username=username, password=password)

    directories = server.services.folders
    dir_ignore = ['System', 'Utilities', r'/']

    for dir in directories:
        if dir not in dir_ignore:
            try:
                for service in server.services.list(folder=dir):
                    temp_dict = collections.OrderedDict()
                    query = fr'services/{dir}/{service.properties.serviceName}.{service.properties.type}'
                    data = server.usage.quick_report(since="LAST_YEAR", queries=query, metrics="RequestCount")
                    temp_dict['Site'] = key
                    temp_dict['Directory'] = 'Root' if dir == r'/' else dir
                    temp_dict['Service'] = service.properties.serviceName
                    temp_dict['Service_Type'] = service.properties.type
                    temp_dict['Time_Slice'] = pd.to_datetime(data['report']['time-slices'], unit='ms').strftime('%Y-%m-%d')
                    temp_dict['Request_Count'] = data['report']['report-data'][0][0]['data']
                    temp_list.append(temp_dict)
                    print(fr'{key}: {query} quick report generated...')

            except Exception as e:
                print(e)

    return temp_list

# CLICK cmds
@click.command()
@click.option('--out_dir', type=click.Path(exists=True), default=None, help='Output directory for the CSV file.')
@click.option('--out_name', default=None, help='Output filename for the CSV file. Please specify extension')
@click.option('--gis_sites_json', type=click.Path(exists=True), default=None, help='Path to the JSON file containing GIS site data.')
@click.option('--server_type', type=click.Choice(['map', 'image']), default='map', help='Choose between ArcGIS or ArcGIS ImageServer.')

def main(out_dir, out_name, gis_sites_json, server_type):
    default_dir = r"..."
    out_dir = out_dir if out_dir else default_dir

    date_now = pd.Timestamp.today().strftime('%Y%m%d_%H%M%S')
    default_name = f"GIS_Services_{server_type}_Usage_{date_now}.csv"
    out_name = out_name if out_name else default_name

    outfile = os.path.join(out_dir, out_name)

    default_json = r"..."
    gis_sites_json = gis_sites_json if gis_sites_json else default_json

    with open(gis_sites_json, 'r') as json_file:
        server_data = json.load(json_file)

    # Select the correct server type: ArcGIS Servers or ArcGIS Image Servers
    selected_servers = server_data['arcgis_servers'] if server_type == 'map' else server_data['arcgis_image_servers']

    service_usage_list = []

    username, password = Authenticate_ArcGISServer.get_creds()

    for site, server_info in selected_servers.items():
        admin_url = server_info['admin']
        service_usage_list.extend(get_quick_reports(admin_url, site, username, password))

    # Create DataFrame and output to screen for review
    df = pd.DataFrame(service_usage_list)
    df1 = df.explode(['Time_Slice', 'Request_Count']).reset_index(drop=True)
    df1.to_csv(outfile, index=False)
    print(f'\nCSV saved as: {outfile}')

    print("\nScript complete.")

if __name__ == '__main__':
    main()
