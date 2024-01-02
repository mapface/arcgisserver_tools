#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# This script gets quick reports for Requests to a Service at the directory level, the script will get the site details from gis_sites.json and requires an administration account to successfully run. 
# Can also be run in cmd line with the following:

#     GetServiceUsage_ArcGIS_Server.py --out_dir "C:\directory..." --out_name "Filename.csv" --gis_sites_json "C:\...\test_json.json"

# Requirements: Python 3+, Pandas 1.3+ (not part of standard ArcPro python env as of 2.9.5)
# Date: 1/11/2023 

import getpass
import pandas as pd
import os
import collections
import click
import json
from arcgis.gis.server import Server

#ArcGIS Admin Credentials
def get_creds():
    print("\nEnter GIS Admin Credentials - right mouse click to paste :)")
    username = getpass.getpass(prompt="User account: ")
    password = getpass.getpass(prompt='Account password: ')
    return username, password

#Get Quick Reports from Server
def get_quick_reports(admin_url, key, username, password):
    temp_list = []

    # Create a Server instance (stand-alone/unfederated ArcGIS Server site)
    server = Server(admin_url, username=username, password=password)

    directories = server.services.folders
    dir_ignore = ['System', 'Utilities', r'/']

    #This loop was for getting stats at the service levels, but didn't seem to return any values for return count
    # for dir in directories:
    #     if dir not in dir_ignore:
    #         try:
    #             for service in server.services.list(folder=dir):
    #                 temp_dict = collections.OrderedDict()
    #                 #query = fr'services/{dir}/{service}.{service.properties.type}' 

    for dir in directories:
        if dir not in dir_ignore:
            try:
                temp_dict = collections.OrderedDict()
                query = fr'services/{dir}'
                data = server.usage.quick_report(since="LAST_YEAR", queries = query, metrics="RequestCount")
                temp_dict['Site'] = key
                temp_dict['Directory'] = 'Root' if dir == r'/' else dir
                temp_dict['Time_Slice'] = pd.to_datetime(data['report']['time-slices'], unit='ms').strftime('%Y-%m-%d')
                temp_dict['Request_Count'] = data['report']['report-data'][0][0]['data']
                temp_list.append(temp_dict)
                print(fr'{key}: {query} quick report generated...')     

            except Exception as e:
                print(e)
    
    return temp_list

#CLICK cmds
@click.command()
@click.option('--out_dir', type=click.Path(exists=True), default=None, help='Output directory for the CSV file.')
@click.option('--out_name', default=None, help='Output filename for the CSV file. Please specify extension')
@click.option('--gis_sites_json', type=click.Path(exists=True), default=None, help='Path to the JSON file containing GIS site data.')

def main(out_dir, out_name, gis_sites_json):
    default_dir = r"C:\Users\...\Outputs"
    out_dir = out_dir if out_dir else default_dir

    date_now = pd.Timestamp.today().strftime('%Y%m%d')
    default_name = f"GIS_Services_Usage_{date_now}.csv"
    out_name = out_name if out_name else default_name

    outfile = os.path.join(out_dir, out_name)

    default_json = r"C:\Users\...\gis_sites.json"
    gis_sites_json = gis_sites_json if gis_sites_json else default_json

    with open(gis_sites_json, 'r') as json_file:
        server_data = json.load(json_file)

    service_usage_list = []
    username, password = get_creds()

    for site, server_info in server_data.items():
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






