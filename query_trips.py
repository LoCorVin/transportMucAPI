import sys, time
import json, requests
from datetime import date, datetime
from .cssinfo import get_css_style

trips_url = 'https://www.mvg.de/fahrinfo/api/routing'
locations_url = 'https://www.mvg.de/fahrinfo/api/location/queryWeb'

lang_en = dict(
        footway='Footway'
    )

lang_de = dict(
        footway='Fußweg'
    )

lang = lang_de


mvg_authorization_key='5af1beca494712ed38d313714d4caff6'
fromString="Innstraße"
toString="Garching-Forschungszentrum"

locations = {}



def printToFile(filename, content):
    with open(filename, 'wb') as out:
        out.write(content)
        out.close()
        exit()


def get_now_timestamp():
    return int(time.time() * 1000)

def get_headers():
    return {'X-MVG-Authorization-Key': mvg_authorization_key}

def get_location(loc_string):
    if loc_string not in locations:
        locations[loc_string] = query_locations(loc_string)[0]
    return locations[loc_string]

def query_locations(query_string):
    url = locations_url
    locations = send_request(url, dict(q=query_string), get_headers())['locations']
    return locations

def format_location(direction, location):
    if location['type'] == 'address':
        return {direction + 'Latitude':location['latitude'], direction+'Longitude':location['longitude']}
    elif  location['type'] == 'station':
        return {direction+'Station':location['id']}
    return None

def send_request(url, params, headers):
    resp = requests.get(url=url, headers=headers, params=params)
    if resp.status_code != 200 or 'application/json' not in resp.headers['content-type']:
        return None
    return json.loads(resp.text)

def get_trips(from_location, to_location, time=get_now_timestamp()):
    start_location = get_location(from_location)
    end_location = get_location(to_location)
    params = format_location("from", start_location)
    params.update(format_location("to", end_location))
    params['time'] = time
    headers = get_headers()

    resp = requests.get(url=trips_url, headers=headers, params=params)
    if resp.status_code != 200:
        print("Stopping, status code (" + str(resp.status_code) + ") instead of (200) returned")
    if 'application/json' not in resp.headers['content-type']:
        print("Wrong format, application/json expected but " + resp.headers['content-type'] + " was returned")
    return json.loads(resp.text)

def get_date_time(timestamp):
    return datetime.fromtimestamp(timestamp/1000)

def get_dt(timestamp):
    date = datetime.fromtimestamp(timestamp/1000)
    formated_string = date.strftime("%d.%m.%y %H:%M").split(' ')
    return {'date': formated_string[0], 'time': formated_string[1]}

def load_trips_from_file(filename):
    with open(filename) as file:
        tripString = file.read()
        return json.loads(tripString)
    return None

def get_transportation_string(trip_part):
    if trip_part['connectionPartType'] == 'FOOTWAY':
        return lang['footway']
    elif trip_part['connectionPartType'] == 'TRANSPORTATION':
        trans_type = None
        if 'trainType' in trip_part:
            trans_type = trip_part['trainType'] + ' '
        if 'product' in trip_part and 'label' in trip_part:
            return ((trip_part['product'] if trans_type is None else trans_type) + trip_part['label']).upper()
    raise Exception('ConnectionPartType has no predefined formating')

def get_transportation(trip_part):
    if trip_part['connectionPartType'] == 'FOOTWAY':
        return {'type': 'walk', 'line':''}
    elif trip_part['connectionPartType'] == 'TRANSPORTATION':
        trans_type = ''
        if 'product' in trip_part and 'label' in trip_part:
            return {'type': trip_part['product'], 'line':trip_part['label']}
    raise Exception('ConnectionPartType has no predefined formating')

def get_duration(trip_or_part):
    t = (trip_or_part["arrival"] - trip_or_part["departure"])/60000
    return str(int(t/60)) + ":" + ("0" if t % 60 < 10 else "") + str(int(t % 60))


def format_output(obj, nested_level=0):
    spacing = '   '
    formated = ''
    if type(obj) == dict:
        formated += '{}'.format((nested_level) * spacing) + "{\n"
        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                formated += '{}{}: '.format((nested_level + 1) * spacing, k)
                formated += format_output(v, nested_level + 1) + "\n"
            else:
                formated += '{}{}: {}\n'.format((nested_level + 1) * spacing, k, v)
        formated += '{}'.format(nested_level * spacing) + '}\n'
    elif type(obj) == list:
        formated += '{}[\n'.format((nested_level) * spacing)
        for v in obj:
            if hasattr(v, '__iter__'):
                formated += format_output(v, nested_level + 1) + "\n"
            else:
                formated += '{}\n'.format((nested_level + 1) * spacing, v) + "\n"
        formated += '{}]\n'.format((nested_level) * spacing)
    else:
        formated += '{}'.format(obj)
    return formated

def extend_style(obj):
    if type(obj) == dict:
        dictionary = dict([(k, extend_style(v)) for k, v in obj.items()])
        if 'type' in dictionary and 'line' in dictionary:
            dictionary['style'] = get_css_style(dictionary['type'], dictionary['line'])
        return dictionary
    elif type(obj) == list:
        return [extend_style(subobj) for subobj in obj]
    else:
        return obj


def printTrips(trips):
    for trip in trips['connectionList']:
        print("-----------------------")
        print("     " + get_dt(trip["departure"])['time'] + " bis " + get_dt(trip["arrival"])['time'] + " (" + get_duration(trip) + ") " )
        print("-----------------------")
        for partTrip in trip['connectionPartList']:
            departure = get_dt(partTrip['departure'])['time']
            arrival = get_dt(partTrip['arrival'])['time']
            print(get_transportation(partTrip) + " -> " + get_stop(partTrip["from"]) + "(" + departure + ") - " + get_stop(partTrip["to"]) + "(" + arrival + ")")


def shorten_trips(trips):
    tps = []
    for trip in trips['connectionList']:
        tp = {}
        tp['departure'] = trip["departure"]
        tp['arrival'] = trip['arrival']
        tp['trip_parts'] = []
        for partTrip in trip['connectionPartList']:
            tpp = {}
            tpp['departure'] = partTrip['departure']
            tpp['arrival'] = partTrip["arrival"]
            set_value(tpp, 'predictedDeparture', get_val(partTrip, 'predictedDeparture'))
            set_value(tpp, 'predictedArrival', get_val(partTrip, 'predictedArrival'))
            #tpp['duration'] = #get_duration(partTrip)
            tpp['transportation'] = get_transportation_string(partTrip)
            tpp.update(get_transportation(partTrip))
            tpp['from'] = get_stop(partTrip["from"])
            tpp['to'] = get_stop(partTrip["to"])
            tp['trip_parts'].append(tpp)
        tps.append(tp)
    return tps

def set_duration(dictionary):
    departure = dictionary['departure']
    arrival = dictionary['arrival']
    if 'predictedDeparture' in dictionary:
        departure = dictionary['predictedDeparture']
    if 'predictedArrival' in dictionary:
        arrival = dictionary['predictedArrival']
    dictionary['duration'] = arrival - departure
    return dictionary

def custom_format(obj, keywords, form_func):
    if type(obj) == dict:
        obj = dict([(k, form_func(custom_format(v)) if k in keywords else custom_format(v)) for k, v in obj.items()])
        return obj
    elif type(obj) == list:
        return [enhance_times(subobj) for subobj in obj]
    else:
        return obj

def enhance_times(obj):
    if type(obj) == dict:
        if 'departure' in obj and 'arrival' in obj:
            obj = set_duration(obj)
        obj = dict([(k, enhance_times(v)) for k, v in obj.items()])
        return obj
    elif type(obj) == list:
        return [enhance_times(subobj) for subobj in obj]
    else:
        return obj

def get_time(timestamp):
    return get_dt(time)['time']

    
def short_distance(timediff):
    timediff = int(timediff/1000/60)
    return str(int(timediff/60)) + ":" + ("0" if timediff % 60 < 10 else "") + str(int(timediff - 60*int(timediff/60)))

def distance(timediff):
    time_str = ""
    timediff = int(timediff/1000/60)
    if int(timediff/60) > 0:
        time_str += str(int(timediff/60)) + " H "
    time_str += str(int(timediff - 60*int(timediff/60))) + " Min"
    return time_str

def get_val(dictionary, key):
    if key in dictionary:
        return dictionary[key]
    return None


def set_value(dictionary, key, value):
    if value is None:
        return
    dictionary[key] = value

def get_stop(location):
    if 'name' in location:
        return location['name']
    if 'latitude' in location:
        return str(location['latitude']) + ", " + str(location['longitude'])

def main(argv):
    if(len(argv) < 3):
        trips = get_trips(fromString, toString)
    else:
        trips = get_trips(argv[1], argv[2])

    selected_trip_info = shorten_trips(trips)

    style_ext_trips = extend_style(selected_trip_info)

    time_enhanced_tf = enhance_times(style_ext_trips)

    #trips = load_trips_from_file("crawled.json")
    print(format_output(time_enhanced_tf))

if __name__ == "__main__":
    main(sys.argv)