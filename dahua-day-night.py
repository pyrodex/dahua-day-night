#!/usr/bin/python3

import argparse # Argument parsing
import requests # For API calls
from requests.auth import HTTPDigestAuth
import time # For time functions
import datetime # For time functions
import yaml # For parsing configuration and cameras
import os # File writing
import sys # System functions

# Get the sunset and sunrise EPOCH from OpenWeatherMap API
def get_times(api_key, city_name, sunset_adjustment, args):
    # API endpoint for current weather
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={api_key}"
    # Fetch weather data
    response = requests.get(url)
    data = response.json()
    # Adjust for sunset offset if desired
    sunset_epoch = data['sys']['sunset'] + sunset_adjustment
    # Extract sunrise and sunset times (in UTC)
    if args.verbose:
        print(f"{datetime.datetime.now()}: Sunrise EPOCH: {data['sys']['sunrise']}")
        print(f"{datetime.datetime.now()}: Original Sunset EPOCH: {data['sys']['sunset']}")
        print(f"{datetime.datetime.now()}: Adjusted Sunset EPOCH: {sunset_epoch}")
    sunrise = epoch_to_cron(data['sys']['sunrise'])
    sunset = epoch_to_cron(sunset_epoch)
    if args.verbose:
        print(f"{datetime.datetime.now()}: Sunrise cron time: {sunrise}")
        print(f"{datetime.datetime.now()}: Sunset cron time: {sunset}")
    return(sunrise, sunset)

# Convert EPOCH to Linux cron time format
def epoch_to_cron(epoch_time):
    # Convert epoch to a datetime object in local time
    dt = datetime.datetime.fromtimestamp(epoch_time)
    # Extract the components needed for a cron format
    minute = dt.minute
    hour = dt.hour  
    # Create a cron format string
    cron_format = f"{minute} {hour} * * *"
    return cron_format

# Create the daily refreshing cron task to create the daily sunrise and sunset cron tasks
def create_scheduling_cron(config, args):
    scheduling_command = config['scheduling_cron_time'] + " " + config['scheduling_cron_user'] + " " + os.path.realpath(__file__) + " " + config['log_file']
    if args.verbose:
        print(f"{datetime.datetime.now()}: Creating the {config['scheduling_cron_file']} scheduling file with the following contents: {scheduling_command}")
    try:
        with open(config['scheduling_cron_file'],"w") as file:
            try:
                file.write(scheduling_command + "\n")
            except IOError as e:
                print(f"{datetime.datetime.now()}: {e}")
    except IOError as e:
        print(f"{datetime.datetime.now()}: {e}")
  
# Create the daily sunrise and sunset cron task
def create_camera_cron(sunrise, sunset, config, camera, args):
    # Open the files
    sunrise_file = config['cron_directory'] + "/sunrise-" + camera['camera']
    sunset_file = config['cron_directory'] + "/sunset-" + camera['camera']
    sunrise_command = sunrise + " root " + os.path.realpath(__file__) + " -c " + camera['camera'] + " -t sunrise"
    sunset_command = sunset + " root " + os.path.realpath(__file__) + " -c " + camera['camera'] + " -t sunset"
    if args.verbose:
        print(f"{datetime.datetime.now()}: Sunrise file - {sunrise_file}")
        print(f"{datetime.datetime.now()}: Sunrise command:")
        print(f"{datetime.datetime.now()}: {sunrise_command}")
        print(f"{datetime.datetime.now()}: Sunset file - {sunset_file}")
        print(f"{datetime.datetime.now()}: Sunset command:")
        print(f"{datetime.datetime.now()}: {sunset_command}")
        print(f"{datetime.datetime.now()}: Writing files now...")
    # Sunrise
    try:
        with open(sunrise_file, "w") as file:
            try:
                file.write(sunrise_command + "\n")
            except IOError as e:
                print(f"{datetime.datetime.now()}: {e}")
    except IOError as e:
        print(f"{datetime.datetime.now()}: {e}")
    # Sunset
    try:
        with open(sunset_file, "w") as file:
            try:
                file.write(sunset_command + "\n")
            except IOError as e:
                print(f"{datetime.datetime.now()}: {e}")
    except IOError as e:
        print(f"{datetime.datetime.now()}: {e}")
    if args.verbose:
        print(f"{datetime.datetime.now()}: Completed writing sunrise and sunset files.")

# Switch the requested camera to the requested time
def switch_camera(camera, args):
    # Sunset first
    if args.time.lower() == "sunrise":
        if args.verbose:
            print(f"{datetime.datetime.now()}: Switching {camera['camera']} to sunrise...")
            print(f"{datetime.datetime.now()}: Performing GET on {camera['sunrise_url']}")
        if camera['auth'].lower() == 'digest':
            response = requests.get(camera['sunrise_url'], auth=HTTPDigestAuth(camera['login'], camera['password']))
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
            # Did not return 200
                return "Error: " + str(e)
            print(f"{datetime.datetime.now()}: Received {response.status_code} status code and camera responded with {response.text.strip()}")
    if args.time.lower() == "sunset":
        if args.verbose:
            print(f"{datetime.datetime.now()}: Switching {camera['camera']} to sunset...")
            print(f"{datetime.datetime.now()}: Performing GET on {camera['sunset_url']}")
        if camera['auth'].lower() == 'digest':
            response = requests.get(camera['sunset_url'], auth=HTTPDigestAuth(camera['login'], camera['password']))
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
            # Did not return 200
                return "Error: " + str(e)
            print(f"{datetime.datetime.now()}: Received {response.status_code} status code and camera responded with {response.text.strip()}")
#def notify_pushover(camera,)

## Main
def main():
    # Argument parsing
    parser = argparse.ArgumentParser(description="Utility script to help detect sunrise/sunset based on OpenWeatherMap API and setup daily jobs for cameras to toggle automatically between them")
    # Debug
    parser.add_argument("-v","--verbose", help="Enable verbose output", action="store_true")
    # Setup
    parser.add_argument("-s","--setup", help="Setup the cron.d script for daily runs", action="store_true")
    # Run the switching for camera
    parser.add_argument("-c","--camera",help="Run the script against the desired camera")
    # Detemrine what switching URL to consume for the camera
    parser.add_argument("-t","--time",help="Run the script for the desired time frame, currently supports sunrise or sunset")
    args = parser.parse_args()
    # Files
    config_file = os.path.dirname(__file__) + "/config.yaml"
    cameras_file = os.path.dirname(__file__) + "/cameras.yaml"
    # Verbose mode
    if args.verbose:
        print(f"{datetime.datetime.now()}: Verbose output enabled")
    # Parse configuration file
    if args.verbose:
        print(f"{datetime.datetime.now()}: Parsing config.yaml file...")
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
        if args.verbose:
            for key, value in config.items():
                print(f"{datetime.datetime.now()}: Config key: {key}, value: {value}")
    # Check if no arguments are passed, then check if the scheduling file exists
    if not len(sys.argv) > 1:
        # Check if the default scheduling cron exists
        if not os.path.isfile(config['scheduling_cron_file']):
            print(f"{datetime.datetime.now()}: Scheduling cron does NOT exist, please run \"{os.path.realpath(__file__)} -s\" to setup the script!")
    if args.setup:
        if args.verbose:
            print(f"{datetime.datetime.now()}: Running setup process")
        create_scheduling_cron(config, args)
    if args.camera and args.time:
        if args.verbose:
            print(f"{datetime.datetime.now()}: Switching {args.camera} to {args.time}")
        if args.verbose:
            print(f"{datetime.datetime.now()}: Parsing cameras.yaml file...")
        with open(cameras_file, 'r') as camera_file:
            # Load cameras.yaml data
            cameras = yaml.safe_load_all(camera_file)
            for camera in cameras:
                if camera['camera'].lower() == args.camera.lower():
                    print(f"{datetime.datetime.now()}: Found {camera['camera']} in {cameras_file}.")  
                    switch_camera(camera,args)
    if not args.camera and not args.time:
        # Get the current sunrise and sunset times from OpenWeatherMap
        (sunrise,sunset) = get_times(config['api_key'], config['city_name'], config['sunset_adjustment'], args)
        # Parse cameras.yaml
        if args.verbose:
            print(f"{datetime.datetime.now()}: Parsing cameras.yaml file...")
        with open(cameras_file, 'r') as camera_file:
            # Load cameras.yaml data
            cameras = yaml.safe_load_all(camera_file)
            # For each camera configured create the sunrise and sunset cron task
            for camera in cameras:
                if args.verbose:
                    print(f"{datetime.datetime.now()}: Camera: {camera['camera']}")
                    print(f"{datetime.datetime.now()}:  IP: {camera['ip']}")
                    print(f"{datetime.datetime.now()}:  Login: {camera['login']}")
                    print(f"{datetime.datetime.now()}:  Password: {camera['password']}")
                    print(f"{datetime.datetime.now()}:  Auth Method: {camera['auth']}")
                    print(f"{datetime.datetime.now()}:  Day URL: {camera['sunrise_url']}")
                    print(f"{datetime.datetime.now()}:  Night URL: {camera['sunset_url']}")
                    print(f"{datetime.datetime.now()}:  Notify: {camera['notify']}")
                if args.verbose:
                    print(f"{datetime.datetime.now()}: Beginning to build out cron file for {camera['camera']}")
                create_camera_cron(sunrise, sunset, config, camera, args)
    if args.verbose:
        print(f"{datetime.datetime.now()}: Finished, goodbye...")
if __name__ == "__main__":
    main()
## End of Main
