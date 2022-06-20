#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create GeoJSON tile of S1 burst map at ZL=1 for GSIMaps from kmz files.

"""


# %% Import
import argparse
import sys
import os
import time
import datetime
import glob
import json
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
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
    tolerance = 0.05


    # %% Read arg
    start = time.time()
    prog = os.path.basename(sys.argv[0])
    description = 'Create GeoJSON tile of S1 burst map at ZL=1 for ' \
                    'GSIMaps from kmz files.'
    print(f"\n{prog} ver1.0.0 20220620 Y. Morishita")
    print(f"{prog} {' '.join(sys.argv[1:])}\n")

    parser = argparse.ArgumentParser(description=description)
    addarg = parser.add_argument
    addarg('-k', '--kmz_dir', type=str, default='kmz',
            help='Directory containing kmz files')
    args = parser.parse_args()

    kmz_dir = args.kmz_dir


    # %% Output geojson tile dirs
    bname = 'S1burst'
    for i in range(1, 5):
        for AD in ['A', 'D']:
            bdir = bname+f'{AD}{i}'
            if os.path.exists(bdir):
                subprocess.run(['rm', '-rf', bdir])
            zl1dir = os.path.join(bdir, '1', '1') # For low ZL
            os.makedirs(zl1dir, exist_ok=True)


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
        polygonsA = [] # For dissolved geojson
        polygonsD = []

        for feature in features_list:
            geometry = feature['geometry']
            lat = geometry['coordinates'][0][0][1]
            if lat > 84 or lat < -84: # cannot display on web map
                continue

            descr = feature['properties']['description']
            orb = descr.split('>')[11].split('<')[0]
            if orb == 'ASCENDING':
                AD = 'A'
                color = colorA
                polygonsA.append(Polygon(
                    feature['geometry']['coordinates'][0]))
            elif orb == 'DESCENDING':
                AD = 'D'
                color = colorD
                polygonsD.append(Polygon(
                    feature['geometry']['coordinates'][0]))
            else:
                raise ValueError(f'orb {orb} is not ASCENDING or DESCENDING!')


        # %% Make dissolved geojson
        for AD, polygons in zip(['A', 'D'], [polygonsA, polygonsD]):
            dissolved_poly = unary_union(MultiPolygon(polygons))
            if dissolved_poly.type == 'Polygon': # 1 segment
                dissolved_poly = [dissolved_poly]
            for _poly in dissolved_poly:
                poly2 = _poly.simplify(tolerance)
                poly2_list = [list(i) for i in poly2.exterior.coords[:]]
                print(f'Number of nodes: {len(poly2_list)}')
                name2 = f'{path}{AD}'
                geometry2 = {'type': 'Polygon', 'coordinates': [poly2_list]}
                properties2 = {"name": name2,
                              "_color": color, "_opacity": line_opacity,
                                "_weight": line_width, "_fillColor": color,
                                "_fillOpacity": fill_opacity}
                out_feature = {'type': 'Feature', 'properties': properties2,
                               'geometry': geometry2}

                # Add feature
                out_jsonfile = os.path.join(bname+f'{AD}{i}', '1', '1',
                                            '0.geojson')
                add_feature(out_feature, out_jsonfile)


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
