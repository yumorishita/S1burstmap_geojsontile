#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create GeoJSON tile of S1 burst map for GSIMaps from kmz files.

"""


# %% Import
import argparse
import sys
import os
import time
import datetime
import glob
import shutil
import json
import subprocess
import numpy as np

class Usage(Exception):
    """Usage context manager"""
    def __init__(self, msg):
        self.msg = msg


# %% latlon2tileid
def latlon2tileid(lat, lon, zl):
    # https://www.trail-note.net/tech/coordinate/
    # https://note.sngklab.jp/?p=72

    x = int((lon/180+1)*2**zl/2)
    y = int(((-np.log(np.tan(np.deg2rad(45+lat/2)))+np.pi)*2**zl/(2*np.pi)))

    return x, y


# %% add_feature
def add_feature(feature, geojson):
    if not os.path.exists(geojson):
        os.makedirs(os.path.dirname(geojson), exist_ok=True)
        with open(geojson, 'x') as f:
            json.dump({'type': 'FeatureCollection', 'features': []}, f)

    with open(geojson, 'r') as f:
        json_dict = json.load(f)
        features_list = json_dict['features']

    features_list.append(feature)

    with open(geojson, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': features_list}, f)


# %% Main
def main(argv=None):

    # %% Settings
    colorA = "#0000ff"
    colorD = "#ff0000"
    line_opacity = 0.4
    line_width = 1
    fill_opacity = 0.1


    # %% Read arg
    start = time.time()
    prog = os.path.basename(sys.argv[0])
    description = 'Create GeoJSON tile of S1 burst map for ' \
                    'GSIMaps from kmz files.'
    print(f"\n{prog} ver1.0.0 20220615 Y. Morishita")
    print(f"{prog} {' '.join(sys.argv[1:])}\n")

    parser = argparse.ArgumentParser(description=description)
    addarg = parser.add_argument
    addarg('-k', '--kmz_dir', type=str, default='kmz',
            help='Directory containing kmz files')
    addarg('-z', '--zoomlevel', type=int, default=6,
            help='Output zoom level')
    args = parser.parse_args()

    kmz_dir = args.kmz_dir
    zl = args.zoomlevel


    # %% Output geojson tile dirs
    bname = 'S1burst'
    for i in range(1, 5):
        for AD in ['A', 'D']:
            bdir = bname+f'{AD}{i}'
            if os.path.exists(bdir):
#                shutil.rmtree(bdir)
                subprocess.run(['rm', '-rf', bdir])
            zldir = os.path.join(bdir, str(zl))
            os.makedirs(zldir)
#            zl1dir = os.path.join(bdir, '1', '1') # For low ZL
#            os.makedirs(zl1dir)


    # %% For each input kmz files
    for kmz in glob.glob(os.path.join(kmz_dir, '*.kmz')):
        print(f'{kmz}')
        start1 = time.time()

        # %% Convert kmz to geosjon
        geojson = os.path.basename(kmz).replace('.kmz', '.geojson')
        if os.path.exists(geojson): os.remove(geojson)
        subprocess.run(['ogr2ogr', geojson, kmz])
        path = geojson[0:3]
        i = np.mod(int(path), 5) #1-5
        if i == 0: i = 5


        # %% Read json
        with open(geojson, 'r') as f:
            json_dict = json.load(f)

        features_list = json_dict['features']
        print(f'n_feature: {len(features_list)}')


        # %% For each burst
        for feature in features_list:
            descr = feature['properties']['description']
            orb = descr.split('>')[11].split('<')[0]
            bid = descr.split('>')[17].split('<')[0]
            swath = descr.split('>')[23].split('<')[0]
#            tanx = descr.split('>')[29].split('<')[0]
            if orb == 'ASCENDING':
                AD = 'A'
                color = colorA
            elif orb == 'DESCENDING':
                AD = 'D'
                color = colorD
            else:
                raise ValueError(f'orb {orb} is not ASCENDING or DESCENDING!')

            name = f'{path}{AD} {swath} {bid}'
            geometry = feature['geometry']
            lat = geometry['coordinates'][0][0][1]
            lon = geometry['coordinates'][0][0][0]

            if lat > 84 or lat < -84: # cannot display on web map
                continue

#            properties = {"name": name, "Burst ID": bid,
#                          "Time from ANX [s]": tanx,
            properties = {"name": name,
                          "_color": color, "_opacity": line_opacity,
                           "_weight": line_width, "_fillColor": color,
                           "_fillOpacity": fill_opacity}
            out_feature = {'type': 'Feature', 'properties': properties,
                           'geometry': geometry}

            # Identify tile ID
            x, y = latlon2tileid(lat, lon, zl)

            # Add feature
            out_jsonfile = os.path.join(bname+f'{AD}{i}', str(zl), str(x),
                                        str(y)+'.geojson')
            add_feature(out_feature, out_jsonfile)


        # %% Make dissolved geojson
        # Need to exclude poles

        # %% Remove geojson
        os.remove(geojson)
        elapsed_time1 = datetime.timedelta(seconds=(time.time()-start1))
        print(f"  Elapsed time: {elapsed_time1}")


    # %% Finish
    elapsed_time = datetime.timedelta(seconds=(time.time()-start))
    print(f"\nElapsed time: {elapsed_time}")
    print(f'\n{prog} Successfully finished!!\n')

    print(f"Output: {bname}[AD][1-5]\n")


# %% main
if __name__ == "__main__":
    sys.exit(main())
