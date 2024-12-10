import requests
from xml.etree import ElementTree as ET
import pandas as pd
import json
import click
import os
import re
from Authenticate_ArcGISServer import get_token  # Using the provided get_token script
from arcgis.gis.server import Server

def get_manifest(username, password, admin_url, rest_url, token):
    server = Server(url=admin_url, username=username, password=password)
    directories = server.services.folders
    dir_ignore = ['System', 'Utilities', r'/']

    combined_manifest = ET.Element('CombinedManifest')

    for dir in directories:
        if dir not in dir_ignore:
            try:
                for service in server.services.list(folder=dir):
                    endpoint = rest_url.rsplit('/', 3)[-3]
                    service_url = f"{rest_url}/{dir}/{service.properties.serviceName}/{service.properties.type}"
                    manifest_url = f"{service.url}/iteminfo/manifest/manifest.xml?&token={token}"
                    response = requests.get(manifest_url)
                    if response.status_code == 200:
                        service_manifest = ET.fromstring(response.content)
                        service_manifest.set('Endpoint', endpoint)
                        service_manifest.set('serviceDir', dir)
                        service_manifest.set('serviceName', service.properties.serviceName)
                        service_manifest.set('serviceType', service.properties.type)
                        service_manifest.set('serviceURL', service_url)
                        combined_manifest.append(service_manifest)
                    else:
                        click.echo(f"Failed to retrieve XML from URL for service {service.properties.serviceName}")
            except Exception as e:
                click.echo(f"Error: {e}")

    return combined_manifest

def parse_xml_to_df(xml):
    data = []

    for child in xml.findall('.//SVCManifest'):
        endpoint = child.attrib.get('Endpoint')
        service_dir = child.attrib.get('serviceDir')
        service_name = child.attrib.get('serviceName')
        service_type = child.attrib.get('serviceType')
        service_url = child.attrib.get('serviceURL')
        resource_path = [resource.find('OnPremisePath').text if resource.find('OnPremisePath') is not None else "N/A" for resource in child.findall('.//SVCResource')]
        
        # Check for SVCDatabase elements
        databases = child.findall('.//SVCDatabase')
        if not databases:  # If no SVCDatabase elements are found
            # Append row with "N/A" for database-specific fields
            data.append([
                endpoint, service_dir, service_name, service_type, service_url,
                "N/A", "N/A", "N/A", resource_path
            ])
        else:
            # Parse SVCDatabase elements if they exist
            for db in databases:
                for dataset in db.findall('.//SVCDataset'):
                    dataset_name = dataset.find('Name').text if dataset.find('Name') is not None else "N/A"
                    dataset_type = dataset.find('DatasetType').text if dataset.find('DatasetType') is not None else "N/A"
                    dataset_path = dataset.find('OnPremisePath').text if dataset.find('OnPremisePath') is not None else "N/A"
                    
                    # Append dataset details
                    data.append([
                        endpoint, service_dir, service_name, service_type, service_url,
                        dataset_name, dataset_type, dataset_path, resource_path  
                    ])
                
    # Define column names
    columns = [
        'Endpoint', 'ServiceDir', 'ServiceName', 'ServiceType', 'Service_URL',
        'DatasetName', 'DatasetType', 'DatasetPath', 'ResourcePath'
    ]
    df = pd.DataFrame(data, columns=columns)
    return df

@click.command()
@click.option('--gis_sites_json', type=click.Path(exists=True), default=None, help='Path to the JSON file containing GIS site data.')
@click.option('--out_dir', type=click.Path(), default=None, help='Output directory for the CSV file.')
@click.option('--out_name', default=None, help='Output filename for the CSV file. Please specify extension')
@click.option('--server_type', type=click.Choice(['map', 'image']), default='map', help='Choose between ArcGIS (map) or ArcGIS ImageServer (image).')

def main(gis_sites_json, out_dir, out_name, server_type):
    # Set default paths and filenames
    default_json = r"..."
    gis_sites_json = gis_sites_json if gis_sites_json else default_json

    default_dir = r'...'
    out_dir = out_dir if out_dir else default_dir

    # Ensure the output directory exists
    os.makedirs(out_dir, exist_ok=True)

    date_now = pd.Timestamp.today().strftime('%Y%m%d')
    default_name = f"ServicesManifest_XML_{date_now}.csv"
    out_name = out_name if out_name else default_name
    outfile = os.path.join(out_dir, out_name)

    all_dfs = []

    try:
        with open(gis_sites_json, 'r') as json_file:
            server_data = json.load(json_file)

        # Choose server list based on the server type argument
        if server_type == "map":
            available_servers = server_data["arcgis_servers"]
        else:
            available_servers = server_data["arcgis_image_servers"]

        # Loop through all selected servers and process each one
        for server_name, server_info in available_servers.items():
            # Extract admin and rest URLs
            admin_url = server_info['admin']
            rest_url = server_info['rest']
            token_url = f"{admin_url}/generateToken"

            # Authenticate and retrieve token
            username, password, token = get_token(server_name, token_url)

            if token:
                combined_manifest = get_manifest(username, password, admin_url, rest_url, token)
                df = parse_xml_to_df(combined_manifest)
                click.echo(f'\nAcquired service manifest: {server_name}')
                all_dfs.append(df)
            else:
                click.echo(f"\nFailed to authenticate with server '{server_name}'.")

    except Exception as e:
        click.echo(f"\nError: {e}")

    # Combine dataframes and save to CSV
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)

        combined_df[['DatasetPart1', 'DatasetPart2']] = combined_df['DatasetPath'].apply(
        lambda x: re.search(r'([^\\]+)\\([^\\]+)$', x).groups() if pd.notna(x) else ("N/A", "N/A")
    ).apply(pd.Series)
        
        combined_df['ResourcePath'] = combined_df['ResourcePath'].apply(
        lambda x: re.sub(r"^\[\'\\\\|\'\]$", '', str(x)).replace('\\\\', '\\') if isinstance(x, list) else "N/A"
    )
        #click.echo(combined_df)
        combined_df.to_csv(outfile, index=False)
        click.echo(f'\nCSV saved to {outfile}')
    else:
        click.echo("\nNo data retrieved. CSV file not saved.")

    click.echo("\nScript complete.")

if __name__ == "__main__":
    main()
