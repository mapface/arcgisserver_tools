'''
This script gets information about web services for reporting, the script will get the site details from gis_sites.json and requires an administration account to successfully run. 
Can also be run in cmd line with the following:

    GetServiceDetails_ArcGIS_Server.py --out_dir "C:\directory..." --out_name "Filename.csv" --gis_sites_json "C:\...\test_json.json" --server_type "map"

'''

import Authenticate_ArcGISServer  # custom script
import click
import pandas as pd
import collections
import os
import json
import requests
import xml.etree.ElementTree as ET
from arcgis.gis.server import Server

# Helper function to check enabled capabilities
def enabled_capabilities(extensions_list):
    capabilities = {
        'FeatureServer': False,
        'KmlServer': False,
        'WFSServer': False,
        'WMSServer': False
    }

    for item in extensions_list:
        typeName = item['typeName']
        enabled = item['enabled'].lower()
        if typeName in capabilities:
            capabilities[typeName] = (enabled == 'true')

    return capabilities

# Function to get service details for a given server
def get_service_details(site, access, server_type, admin_url, rest_url, username, password):
    temp_list = []
    
    # Create a Server instance (stand-alone/unfederated ArcGIS Server site)
    server = Server(admin_url, username=username, password=password)

    # Find directories
    directories = server.services.folders
    dir_ignore = ['System', 'Utilities', r'/']

    # Print services
    for dir in directories:
        if dir not in dir_ignore:
            try:
                for service in server.services.list(folder=dir):
                    capabilities = enabled_capabilities(service.properties.extensions)

                    temp_dict = collections.OrderedDict()
                    temp_dict['Site'] = site
                    temp_dict['Directory'] = 'Root' if dir == r'/' else dir
                    temp_dict['Service_Name'] = service.properties.serviceName
                    temp_dict['Service_Type'] = service.properties.type
                    temp_dict['Access'] = access
                    temp_dict['Server_Type'] = server_type
                    temp_dict['Is_Private'] = service.properties.private
                    temp_dict['Feature_Server'] = capabilities['FeatureServer']
                    temp_dict['Kml_Server'] = capabilities['KmlServer']
                    temp_dict['WFS_Server'] = capabilities['WFSServer']
                    temp_dict['WMS_Server'] = capabilities['WMSServer']
                    metadata_url = f"{rest_url}/{dir}/{service.properties.serviceName}/{service.properties.type}/info/metadata"
                    create_date = get_create_date(metadata_url)
                    temp_dict['Create_Date'] = create_date
                    temp_dict['Service_URL'] = f"{rest_url}/{dir}/{service.properties.serviceName}/{service.properties.type}"
                    temp_list.append(temp_dict)

            except Exception as e:
                print(e)

    return temp_list

# Function to get the creation date of the service from its metadata
def get_create_date(service_metadata_url):
    try:
        response = requests.get(service_metadata_url)
        if response.status_code == 200:
            metadata_xml = response.text
            root = ET.fromstring(metadata_xml)
            esri_element = root.find(".//Esri")
            create_date_element = esri_element.find("CreaDate")
            create_date = create_date_element.text if create_date_element is not None else ''
            return create_date
        else:
            return ''
    except Exception as e:
        return ''

# Function to export data to a CSV
def export_to_csv(data, outdir, outname):
    # Create DataFrame and output to screen for review
    df = pd.DataFrame(data=data)
    outfile = os.path.join(outdir, outname)
    df.to_csv(outfile, index=False)
    print(f'CSV saved as: {outfile}')

# CLICK commands for handling command-line inputs
@click.command()
@click.option('--out_dir', type=click.Path(exists=True), default=None, help='Output directory for the CSV file.')
@click.option('--out_name', default=None, help='Output filename for the CSV file. Please specify extension')
@click.option('--gis_sites_json', type=click.Path(exists=True), default=None, help='Path to the JSON file containing GIS site data.')
@click.option('--server_type', type=click.Choice(['map', 'image']), default='map', help='Choose between ArcGIS or ArcGIS ImageServer.')

def main(out_dir, out_name, gis_sites_json, server_type):
    
    default_dir = r'...'
    out_dir = out_dir if out_dir else default_dir

    date_now = pd.Timestamp.today().strftime('%Y%m%d')
    default_name = f"GIS_Services_{server_type}_{date_now}.csv"
    out_name = out_name if out_name else default_name

    default_json = r"..."
    gis_sites_json = gis_sites_json if gis_sites_json else default_json

    with open(gis_sites_json, 'r') as json_file:
        server_data = json.load(json_file)

    service_list = []

    username, password = Authenticate_ArcGISServer.get_creds()

    # Select correct server data based on user input (ArcGIS or ImageServer)
    selected_servers = server_data['arcgis_servers'] if server_type == 'map' else server_data['arcgis_image_servers']
    
    for site, server_info in selected_servers.items():
        admin_url = server_info['admin']
        rest_url = server_info['rest']
        access = server_info['access']
        service_list.extend(get_service_details(site, access, server_type, admin_url, rest_url, username, password))
        print(f'Acquired service details: {site}')

    export_to_csv(service_list, out_dir, out_name)
    print("Script complete.")

if __name__ == '__main__':
    main()
