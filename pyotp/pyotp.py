"""
Uses otp API to preform network analysis.
"""

import json
import time
import zipfile
import io

from datetime import datetime

import requests
import tempfile

import pandas as pd
import geopandas as gpd
import shapely.geometry as geom

from pathlib import Path

#=====================general functions==========================
#decode an encoded string
def decode(encoded):
    """
    Returns a Decoded list of latitude,longitude coordinates.
    Parameters
    ----------
    encoded : Endcoded string

    Returns
    -------
    list
        Has the structure
        [(lon1, lat1), (lon2, lat2), ..., (lonn, latn)]
    """
    #six degrees of precision in valhalla
    inv = 1.0 / 1e6;
    
    decoded = []
    previous = [0,0]
    i = 0
    #for each byte
    while i < len(encoded):
        #for each coord (lat, lon)
        ll = [0,0]
        for j in [0, 1]:
            shift = 0
            byte = 0x20
            #keep decoding bytes until you have this coord
            while byte >= 0x20:
                byte = ord(encoded[i]) - 63
                i += 1
                ll[j] |= (byte & 0x1f) << shift
                shift += 5
            #get the final value adding the previous offset and remember it for the next
            ll[j] = previous[j] + (~(ll[j] >> 1) if ll[j] & 1 else (ll[j] >> 1))
            previous[j] = ll[j]
        #scale by the precision and chop off long coords also flip the positions so
        #its the far more standard lon,lat instead of lat,lon
        decoded.append([float('%.6f' % (ll[1] * inv)), float('%.6f' % (ll[0] * inv))])
        #hand back the list of coordinates
    return decoded

#=====================api functions====================================
def route(
    locations_gdf, #a pair of locations in geodataframe fromat
    mode='TRANSIT,WALK',
    trip_name = '',
    date_time = datetime.now(),
    control_vars = dict()): # a dictionary of control variables
    """
    Return a GeoDataFrame with detailed trip information for the best option.
    Parameters
    ----------
    locations_gdf : GeoDataFrame
        It should only contain two records, first record is origina and
        the second record is destination. If more than two records only
        the first two records are considered.
    mode : string
        Modes that can be used include CAR, BUS, FERRY, RAIL, TRANSIT, 
        WALK, BICYCLE, MULTIMODAL
    trip_name : string
        gives the trip a name which is stored in the trip_name in output
        GeoDataFrame.
    date_time : datetime object
        Sets the start time of a trip. Only important if the mode is 
        transit or a subset of transit. 
    control_vars : dictionanry
        If you want to add more control variables to the route add them as
        dictionary. An examples is {"maxWalkDistance":"1000", "arriveBy":"false",
        "wheelchair":"false", "locale":"en"}
    Returns
    -------
    GeoDataFrame
        Has the structure
        trip_name -> the name given as an input to the trip.
        leg_id -> A counter for each trip leg
        mode -> returns the mode for each trip leg
        from -> the shaply point data in WSG84 for the origin location
        from_name -> the interim stop id on the network or 'Origin'
        to -> the shaply point data in WSG84 for the destination location
        to_name -> the interim stop id on the network or 'Destination'
        route_id -> the route id for the trip leg if the mode is transit
        trip_id -> the trip id for the trip leg if the mode is transit
        distance -> Distance traveled in meters for the trip leg
        duration -> Travel time for the trip leg in seconds
        startTime -> time stamp for the start time of the trip leg
        endTime -> time stamp for the end time of the trip leg
        waitTime -> Wait time for the trip leg in seconds
        geometry -> The goemetry of the trip leg in shaply object and WGS84
    """
    
    #convert the geometry into a list of dictinoaries
    if not locations_gdf.crs:
        print('please define projection for the input gdfs')
        sys.exit()
    
    locations_gdf = locations_gdf.to_crs({'init': 'epsg:4326'})
    
    #convert time into text
    t = date_time.strftime("%H:%M%p")
    d = date_time.strftime("%m-%d-%Y")
    
    #get from and to location from locations_gdf
    orig = locations_gdf['geometry'].iat[0]
    dest = locations_gdf['geometry'].iat[-1]
    
    orig_text = "{0}, {1}".format(orig.y, orig.x)
    dest_text = "{0}, {1}".format(dest.y, dest.x)
    
    #send query to api
    url = 'http://localhost:8080/otp/routers/default/plan'
    query = {
        "fromPlace":orig_text,
        "toPlace":dest_text,
        "time":t,
        "date":d,
        "mode":mode}
    
    query = {**query, **control_vars}

#         some other controls
#         "maxWalkDistance":"1000",
#         "arriveBy":"false",
#         "wheelchair":"false",
#         "locale":"en"

    r = requests.get(url, params=query)
    
    #check for request error
    r.raise_for_status()

    #if error then return emptly GeoDataFrame
    if 'error' in r.json():
        return gpd.GeoDataFrame()
    
    #convert request output ot a GeoDataFrame
    legs = r.json()['plan']['itineraries'][0]['legs']
    legs_list = list()
    for i, leg in enumerate(legs):
        items = [
            'from',
            'to',
            'distance',
            'duration',
            'startTime',
            'endTime',
            'mode',
            'legGeometry']
        #select only necessary items
        l = {k: leg[k] for k in items}

        #add leg id
        l['leg_id'] = i


        #add leg geometry
        l['geometry'] = geom.LineString(decode(leg['legGeometry']['points']))
        l.pop('legGeometry', None)

        #add origin and destination stops
        if 'stopId' in l['from']:
            l['from_name']=l['from']['stopId']
        else:
            l['from_name'] = l['from']['name']

        if 'stopId' in l['to']:
            l['to_name']=l['to']['stopId']
        else:
            l['to_name'] = l['to']['name']
            
        if 'tripId' in leg:
            l['trip_id']= leg['tripId']
        else:
            l['trip_id'] = ''
            
        if 'routeId' in leg:
            l['route_id']= leg['routeId']
        else:
            l['route_id'] = ''

        #fix from and to to theri locations
        l['from'] = geom.Point(l['from']['lon'], l['from']['lat'])
        l['to'] = geom.Point(l['to']['lon'], l['to']['lat'])


        #convert to dataframe
        l_df = pd.Series(l).to_frame().T

        legs_list.append(l_df)

    legs_df = pd.concat(legs_list).reset_index(drop=True)
    legs_df['trip_name'] = trip_name

    #calculate wait time
    legs_df['waitTime'] = legs_df['startTime'].shift(-1)
    legs_df['waitTime'] = legs_df['waitTime']-legs_df['endTime']
    
    #fix the field order
    field_order = [
        'trip_name',
        'leg_id',
        'mode',
        'from',
        'from_name',
        'to',
        'to_name',
        'route_id',
        'trip_id',
        'distance',
        'duration',
        'startTime',
        'endTime',
        'waitTime',
        'geometry']
    legs_df = legs_df[field_order]
    legs_gdf = gpd.GeoDataFrame(legs_df, crs = {'init': 'epsg:4326'})
    

    return legs_gdf

def service_area(
    in_gdf, 
    id_field = '',
    mode = "TRANSIT,WALK", 
    breaks = [10, 20], #in minutes
    date_time = datetime.now(),
    control_vars = dict()): # a dictionary of control variables
    
    """
    Return a GeoDataFrame of catchments for each point in 'in_gdf'.
    Parameters
    ----------
    in_gdf : GeoDataFrame
        Contains a series of points and optionally a name for each point
        as the origins of the catchment analysis.
    id_field : string
        id_field is the name of the field in 'in_gdf' that contains
        the ids for each origin. Each point has to have a unique id.
    mode : string
        Similar to the ``route`` function.
    breaks : list
        A list of time breaks in minutes. A catchment for each time break
        will be created for each origin.
    date_time : datetime object
        Similar to the ``route`` function. 
    control_vars : dictionanry
        Similar to the ``route`` function.
    Returns
    -------
    GeoDataFrame
        Has the structure
        time -> time break for the isochrone in seconds.
        geometry -> Shaply polygon geometry
        name -> name of the origin from the input 'id_field'.
    """
    
    #convert the geometry into a list of dictinoaries
    if not in_gdf.crs:
        print('please define projection for the input gdfs')
        sys.exit()
    
    in_gdf = in_gdf.to_crs({'init': 'epsg:4326'})
    
    #convert time into text
    t = date_time.strftime("%H:%M%p")
    d = date_time.strftime("%Y/%m/%d")
    
    #run for each single point in GeoDataFrame
    url = 'http://localhost:8080/otp/routers/default/isochrone'
    iso_list = list()
    for row in in_gdf.iterrows():
        try:
            indx = row[0]
            orig = row[1]['geometry']


            #convert origin from shapely to text
            orig_text = "{0}, {1}".format(orig.y, orig.x)

            #send query to api
            query = {
                "fromPlace":orig_text,
                "date":d,
                "time":t,
                "mode":mode,
                "cutoffSec":[x*60 for x in breaks]}
            
            query = {**query, **control_vars}

            r = requests.get(url, params=query)
            print(r.headers)
            
            if 'zip' in r.headers['Content-Type']:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                tmp_dir = tempfile.TemporaryDirectory()
                z.extractall(tmp_dir.name)
                shapefiles = list()
                for f in Path(tmp_dir.name).glob("*.shp"):
                    shapefiles.append(f)
                iso_gdf = gpd.read_file(str(shapefiles[0]))
                tmp_dir.cleanup()
            else:
                iso_gdf = gpd.GeoDataFrame.from_features(r.json()['features'])
                
            if id_field:
                iso_gdf['name'] = row[1][id_field]
            
            iso_list.append(iso_gdf)
        except Exception as e: print(e)
    if iso_list:
        out_gdf = pd.concat(iso_list)   
        out_gdf = out_gdf[out_gdf['geometry'].notnull()].copy()
        out_gdf = gpd.GeoDataFrame(out_gdf, crs = {'init': 'epsg:4326'}).copy()
    else:
        out_gdf = gpd.GeoDataFrame(crs = {'init': 'epsg:4326'})
    
    return out_gdf.reset_index(drop = True)

def od_matrix(
    origins,
    destinations,
    mode,
    origins_name,
    destinations_name,
    max_travel_time = 60,
    date_time = datetime.now(),
    control_vars = dict()): # a dictionary of control variables
    """
    Return a GeoDataFrame with detailed trip information for the best option.
    Parameters
    ----------
    origins : GeoDataFrame
        It should only contain a series of points.
    destinations : GeoDataFrame
        It should only contain a series of points.
    mode : string
        Similar to the ``route`` function.
    origins_name : string
        gives the origin a name which is stored in the ``trip_name`` in output
        GeoDataFrame.
    max_travel_time : integer
        maximum travel time from each origin in minutes. Use ``None`` to disable
        it.
    date_time : datetime object
        Similar to the ``route`` function. 
    control_vars : dictionanry
        Similar to the ``route`` function.
    Returns
    -------
    GeoDataFrame
        Has the structure
        trip_name -> contains ``origins_name`` for each origin.
        The rest are similar to the ``route`` function. 
    """    
       
    if not origins.crs or not destinations.crs:
        print('please define projection for the input gdfs')
        sys.exit()
    
    #convert the geometry into a list of dictinoaries
    origins = origins.to_crs({'init': 'epsg:4326'})
    destinations = destinations.to_crs({'init': 'epsg:4326'})
    
    od_list = list()
    cnt = 0
    #mark time before start
    t1 = datetime.now()
    print('Analysis started at: {0}'.format(t1))
    
    if max_travel_time:
        iso  = service_area(
            origins, 
            id_field = origins_name,
            mode = mode, 
            breaks = [max_travel_time], #in seconds
            date_time = date_time,
            control_vars = control_vars,
        )
    
    poly_destinations = destinations.copy()
    poly_destinations['geometry']= poly_destinations.buffer(0.00001)
    
    for o in origins[['geometry', origins_name]].itertuples():
        o_name = o[2]
        selected_iso = iso[iso['name']==o_name].copy()
        selected_iso = gpd.GeoDataFrame(selected_iso)
        
        res_intersection = gpd.overlay(poly_destinations, selected_iso, how='intersection')
        
        selected_destinations = destinations[destinations[destinations_name].isin(res_intersection[destinations_name])].copy()

        #selected_destinations
        for d in selected_destinations[['geometry', destinations_name]].itertuples():
            od = pd.DataFrame(
                [[o[1], o[2]],
                 [d[1], d[2]]],
                columns = ['geometry', 'location Name'])
            od = gpd.GeoDataFrame(od, crs = {'init': 'epsg:4326'})
            r = route(
                locations_gdf = od, #a pair of locations in geodataframe fromat
                mode = mode,
                trip_name = 'from {0} to {1}'.format(o[2], d[2]),
                date_time = date_time,
                control_vars = control_vars)
            od_list.append(r)
            
        cnt += 1
        t_delta = datetime.now() - t1
        eta = t_delta * origins.shape[0] / cnt
        print("calculating {0} ODs, remaining origins {1}, estimated remaining time: {2}".format(selected_destinations.shape[0], origins.shape[0] - cnt, eta - t_delta))

    od_df = pd.concat(od_list).reset_index(drop = True)
    od_gdf = gpd.GeoDataFrame(od_df, crs = {'init': 'epsg:4326'})
    print("Elapsed time was {0} seconds".format(datetime.now() - t1))
    
    return od_gdf

    
    
    
    
    
    
    
    
    
    
    
    