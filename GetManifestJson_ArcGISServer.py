
"""
This script gets the manifest.json from ArcGIS Server admin directory and outputs the data to a CSV file.

To run the script, use the following command format in your terminal or command prompt:

    python GetManifestJson_ArcGISServer.py --gis_sites_json path/to/gis_sites.json --out_dir path/to/output/directory --out_name output_filename.csv --server_name specific_server_name

Options:
    --gis_sites_json: Path to the JSON file containing GIS site data. (optional, default: ....gis_sites.json)
    --out_dir: Output directory for the CSV file. (optional, default: ...Outputs)
    --out_name: Output filename for the CSV file. Please specify the extension. (optional, default: ServicesManifest_JSON_YYYYMMDD.csv.csv)
    --server_name: The name of the ArcGIS Server to process. If not provided, all servers in the config file will be processed. (optional)
"""

## TODO need to explode the dicts for datasets and connection strings for the csv
## TODO update to use the new gis server json format

import json
import pandas as pd
import click
import os
from arcgis.gis.server import Server
import Authenticate_ArcGISServer  # custom script

@click.command()
@click.option('--gis_sites_json', type=click.Path(exists=True), default=None, help='Path to the JSON file containing GIS site data.')
@click.option('--out_dir', type=click.Path(exists=True), default=None, help='Output directory for the CSV file.')
@click.option('--out_name', default=None, help='Output filename for the CSV file. Please specify extension')
@click.option('--server_name', default=None, help='The name of the ArcGIS Server to process. If not provided, all servers in the config file will be processed.')

def main(gis_sites_json, out_dir, out_name, server_name):
    # Set default paths and filenames
    default_json = r"...arcgis_servers.json"
    gis_sites_json = gis_sites_json if gis_sites_json else default_json

    default_dir = r'...'
    out_dir = out_dir if out_dir else default_dir

    date_now = pd.Timestamp.today().strftime('%Y%m%d')
    default_name = f"ServicesManifest_JSON_{date_now}.csv"
    out_name = out_name if out_name else default_name

    # Read the config file
    try:
        with open(gis_sites_json, 'r') as file:
            config = json.load(file)
        print(f"Config file '{gis_sites_json}' loaded successfully.")
    except Exception as e:
        print(f"Failed to load config file '{gis_sites_json}': {e}")
        return

    all_formatted_data = []

    # Function to process a single server
    def process_server(server_url, server_name):
        try:
            # Authenticate and create a Server instance
            username, password = Authenticate_ArcGISServer.get_creds(server_url)
            server = Server(url=server_url, username=username, password=password)
            print(f"\nAuthenticated to server '{server_url}' successfully.")
        except Exception as e:
            print(f"\nFailed to authenticate to server '{server_url}': {e}")
            return

        directories = server.services.folders
        dir_ignore = ['System', 'Utilities', r'/']

        dict_list = []

        # List and process services in other directories
        print(f"\nIdentifying Services on server '{server_url}':\n")
        for dir in directories:
            if dir not in dir_ignore:
                try:
                    for service in server.services.list(folder=dir):
                        service_name = service.properties.serviceName
                        print(f"Processing service: {service_name}")
                        manifest = service.iteminformation.manifest
                        manifest['server_name'] = server_name  # Add server_name to manifest
                        manifest['directory'] = dir  # Add service folder
                        manifest['service_name'] = service_name  # Add service_name to manifest
                        dict_list.append(manifest)
                except Exception as e:
                    print(f"Failed to list services in directory '{dir}' on server '{server_url}': {e}")

        # Format data
        formatted_data = []
        for data_dict in dict_list:
            formatted_dict = {}
            for key, value in data_dict.items():
                if isinstance(value, list):
                    for index, item in enumerate(value):
                        if isinstance(item, dict):  # Check if item is a dictionary
                            for sub_key, sub_value in item.items():
                                formatted_dict[f"{key}_{index}_{sub_key}"] = sub_value
                        else:
                            formatted_dict[f"{key}_{index}"] = item  # Handle non-dict items in the list
                else:
                    formatted_dict[key] = value
            formatted_data.append(formatted_dict)

        all_formatted_data.extend(formatted_data)

    # Process either a single server or all servers
    if server_name:
        if server_name in config:
            site = config[server_name]
            print(f"\nProcessing server: {server_name}")
            process_server(site['admin'], server_name)
        else:
            print(f"Server name '{server_name}' not found in the config file.")
    else:
        for name, site in config.items():
            print(f"Processing server: {name}")
            process_server(site['admin'], name)

    # Create a DataFrame from the list of formatted dictionaries
    if all_formatted_data:
        df = pd.DataFrame(all_formatted_data)
        # Ensure 'server_name' and 'service_name' are the first columns
        columns = ['server_name', 'directory', 'service_name'] + [col for col in df.columns if col not in ['server_name', 'directory', 'service_name']]
        df = df[columns]

        # Save the DataFrame to a CSV file
        try:
            outfile = os.path.join(out_dir, out_name)
            df.to_csv(outfile, index=False)
            print(f"\nData saved to {outfile}")
        except Exception as e:
            print(f"\nFailed to save data to CSV file '{outfile}': {e}")
    else:
        print("No data to save.")

if __name__ == '__main__':
    main()
