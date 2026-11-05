import pandas as pd, streamlit as st, re, datetime
from datetime import datetime, timedelta
import json
from theme import inject_theme
from email_tab import render_email_formatter

with open('json/classMap.json', 'r') as f:
	CABIN_CLASS_MAPPING = json.load(f)

with open('json/airlines.json', 'r') as f:
	airlines = json.load(f)

with open('json/airport_codes.json', 'r') as f:
	airport_codes = json.load(f)

current_year = datetime.now().year

#append year based on derived date from df - needed for sked from air dept
def adjust_date(x):
	current_date = datetime.now()
	
	# Convert the DDMMM part into a date with current year
	date_with_current_year = pd.to_datetime(f"{x}{current_year}", format='%d%b%Y')
	
	# If the date is already past the current date, append next year
	if date_with_current_year < current_date:
		return f"{x}{current_year + 1}"
	else:
		return f"{x}{current_year}"

def get_cabin_class(airline_code, booking_class):
	airline_code = airline_code.upper()
	booking_class = booking_class.upper()

	# Default to Economy if airline not found
	if airline_code not in CABIN_CLASS_MAPPING:
		return "AIRLINE NOT FOUND"
	
	airline_mapping = CABIN_CLASS_MAPPING[airline_code]
	
	for cabin_class, booking_classes in airline_mapping.items():
		class_list = [cls.strip() for cls in booking_classes.split(',') if cls.strip()]
		if booking_class in class_list:
			return cabin_class
	
	return "NOT FOUND"

def convert_ampm_to_24hr(time_str):
	"""
	Convert Amadeus AM/PM format to 24-hour HH:MM format
	Examples: '210P' -> '14:10', '920A' -> '09:20', '1235P' -> '12:35'
	"""
	period = time_str[-1]  # 'A' or 'P'
	time_digits = time_str[:-1]  # Remove the A/P
	
	# Pad with leading zeros to make it 4 digits (HHMM)
	time_digits = time_digits.zfill(4)
	
	hour = int(time_digits[:2])
	minute = time_digits[2:]
	
	# Convert to 24-hour format
	if period == 'P' and hour != 12:
		hour += 12
	elif period == 'A' and hour == 12:
		hour = 0
	
	return f"{hour:02d}:{minute}"

SCHEDULE_SOURCES = [
	'Tropics',
	'Air Department',
	'AMADEUS',
	'AMADEUS - UNCONFIRMED',
	'AMADEUS - HELD FLIGHTS (RTIM)',
	'AMADEUS - FXD FARE DISPLAY',
	'GOLD MEDAL - ITINERARY PAGE',
	'GOLD MEDAL - QUOTE SCREEN',
]

def format_airdept_flights(text):
	air_dept_pattern = r'^\s*([A-Za-z]{2}\d{1,5})\s+([A-Za-z])\s+([A-Za-z]+(?:\s[A-Za-z]+)*)\s+([A-Za-z]{3})\s+([A-Za-z]{3})\s+([0-9]{2}[A-Za-z]{3})\s+([0-9]{4})\s+([0-9]{2}[A-Za-z]{3})\s+([0-9]{4})\s+([A-Za-z]{2})\s+(?:0\s+)?([A-Za-z\s]+)\s*$'
	flights = text.replace(",",'').strip().split("\n")
	schedule = []

	for index, item in enumerate(flights):
		match = re.match(air_dept_pattern, item)
		if match:
			flight_info = match.groups()
			schedule.append(flight_info)
		
	df = pd.DataFrame(schedule, columns=[
		'Flight No', 
		'Bkg Class',
		'Cabin Class',
		'From',
		'To',
		'Dep Date',
		'Dep Time',
		'Arr Date',
		'Arr Time',
		'CODE',
		'Operating Airlines'])
	
	if df.empty:
		raise ValueError("No flights were recognised. Check the schedule source selected matches the text pasted.")
	df['Airline'] = df['Flight No'].astype(str).str[:2]
	df['Flight Number'] = df['Flight No'].astype(str).str[2:]
	# Convert to datetime, add current year if no year is provided
	df['Dep Date'] = pd.to_datetime(df['Dep Date'].apply(lambda x: adjust_date(x) if len(x) == 5 else x), format='%d%b%Y')
	df['Dep Date'] = df['Dep Date'].dt.strftime('%d-%b-%Y')
	df['Arr Date'] = pd.to_datetime(df['Arr Date'].apply(lambda x: adjust_date(x) if len(x) == 5 else x), format='%d%b%Y')
	df['Arr Date'] = df['Arr Date'].dt.strftime('%d-%b-%Y')
	df['Dep Time'] = df['Dep Time'].apply(lambda x: f"{str(x).zfill(4)[:2]}:{str(x).zfill(4)[2:]}")
	df['Arr Time'] = df['Arr Time'].apply(lambda x: f"{str(x).zfill(4)[:2]}:{str(x).zfill(4)[2:]}")
		
	column_order = [
		'Flight No',
		'Airline',
		'Flight Number',
		'From',
		'Dep Date',
		'Dep Time',
		'To',
		'Arr Date',
		'Arr Time',
		'Cabin Class', 
		'Operating Airlines']
	
	df = df[column_order]
	df['Operating Airlines'] = df['Operating Airlines'].apply(lambda x: airlines.get(x, x))
	return df

def format_tropics_flights(text):
	tropics_pattern = r'^\s*([A-Za-z]{2}\d{1,5})\s+([A-Za-z])\s+([A-Za-z]{3})\s+([A-Za-z]{3})\s+(\d{2}-[A-Za-z]{3}-\d{4})\s+(\d{2}:\d{2})\s+(\d{2}-[A-Za-z]{3}-\d{4})\s+(\d{2}:\d{2})\s+([A-Za-z]+(?:\s(?!non\s)[A-Za-z]+)?)\s+((?:non\s+stop|[A-Za-z\s]+))\s+(\d{1,2}[hH]\s*\d{1,2}[mM]|\d{1,2}[mM])\s+([A-Za-z\s\-]+)\s*$'
	flights = text.strip().split("\n")
	schedule = []
	for index, item in enumerate(flights):
		# Check if the current item is the first (index 0)
		if index == 0:
			# Split the item based on spaces
			parts = item.split()
			parts = parts[:-3]
			item = ' '.join(parts)

		match = re.match(tropics_pattern, item)
		if match:
			flight_info = match.groups()
			schedule.append(flight_info)
			
	df = pd.DataFrame(schedule, columns=[
		'Flight No',
		'Bkg Class',
		'From',
		'To',
		'Dep Date',
		'Dep Time',
		'Arr Date',
		'Arr Time',
		'Cabin Class', 
		'Transit Stops',
		'Layover Time',
		'Operating Airlines'])
	
	df['Airline'] = df['Flight No'].astype(str).str[:2]
	df['Flight Number'] = df['Flight No'].astype(str).str[2:]
	df['DepDate'] = pd.to_datetime(df['Dep Date'], format='%d-%b-%Y')
	df['ArrDate'] = pd.to_datetime(df['Arr Date'], format='%d-%b-%Y')

	# Iterate through rows and compare with previous row
	for index in range(len(df) - 1):
		# Calculate the time difference between the current row's 'Arr Date' and the previous row's 'Arr Date'
		date_diff = (df.at[index+1, 'ArrDate'] - df.at[index, 'ArrDate'])
		date_diff = abs(date_diff)
		if date_diff > pd.Timedelta(days=1):
			df.at[index, 'Layover Time'] = ''  # or np.nan
	if df.empty:
		raise ValueError("No flights were recognised. Check the schedule source selected matches the text pasted.")
	df.at[df.index[-1], 'Layover Time'] = ''  # or np.nan
		
	column_order = [
		'Flight No',
		'Airline',
		'Flight Number',
		'From',
		'Dep Date',
		'Dep Time',
		'To',
		'Arr Date',
		'Arr Time',
		'Cabin Class', 
		'Transit Stops',
		'Layover Time',
		'Operating Airlines']
	df = df[column_order]
	return df

def format_amadeus(text, get_flag):
	if get_flag:
		# regex pattern for GET Schedules
		amadeus_pattern = r'^\s*(\d{1,2})\s+([A-Za-z]{2}\s?\d{1,5})\s+([A-Za-z])\s+(\d{2}[A-Z]{3})\s+(\d\*)?([A-Z]{6})\s+([A-Z]{2}\d)\s+(\d{1,4}[AP])\s?(\d{1,4}[AP])\s+(\d{2}[A-Z]{3})\s+([A-Z])\s+([A-Z]{2})/([A-Z0-9]+)\s*$'
	else:
		amadeus_pattern = r'^\s*(\d{1,2})\s+([A-Za-z]{2}\s?\d{1,5})\s+([A-Za-z])\s+(\d{2}[A-Z]{3})\s+(\d[ *])?([A-Z]{6})\s+([A-Z]{2}\d)\s+(\d{4})\s+(\d{4})\s+(\d{2}[A-Z]{3})\s+([A-Z])\s+([A-Z]{2})/([A-Z0-9]+)\s*$'
	
	lines = text.strip().split("\n")
	schedule = []
	operating_airline = None
	
	for line in lines:
		# Check if this is an "OPERATED BY" line
		if "OPERATED BY" in line:
			operating_airline = line.strip().replace("OPERATED BY ", "")
			# Apply to the last flight added to schedule
			if schedule:
				# Update the last flight's operating airline
				last_flight = list(schedule[-1])
				last_flight[11] = operating_airline  # Index 11 is Operating Airlines
				schedule[-1] = tuple(last_flight)
			continue
		
		match = re.match(amadeus_pattern, line)
		if match:
			segment_num, flight_no, bkg_class, dep_date, day_indicator, route, status, dep_time, arr_time, arr_date, airline, eticket, fare_basis = match.groups()
			
			# Remove whitespace from flight number
			flight_no = flight_no.replace(' ','')
			
			# Extract origin and destination from the 6-letter route code
			origin = route[:3]
			destination = route[3:]
			
			current_year = datetime.now().year
			dep_date_obj = datetime.strptime(f"{dep_date}{current_year + 1}", "%d%b%Y")
			arr_date_obj = datetime.strptime(f"{arr_date}{current_year + 1}", "%d%b%Y")
			
			# Format dates
			dep_date_formatted = dep_date_obj.strftime("%d-%b-%Y")
			arr_date_formatted = arr_date_obj.strftime("%d-%b-%Y")
			
			if get_flag:
				# Convert AM/PM format to 24-hour HH:MM
				dep_time_formatted = convert_ampm_to_24hr(dep_time)
				arr_time_formatted = convert_ampm_to_24hr(arr_time)
			else:
				# Format times from HHMM to HH:MM
				dep_time_formatted = f"{dep_time[:2]}:{dep_time[2:]}"
				arr_time_formatted = f"{arr_time[:2]}:{arr_time[2:]}"
			
			# Determine cabin class from booking class (you may need to adjust this logic)
			cabin_class = get_cabin_class(flight_no[:2], bkg_class)
			
			flight_info = (
				flight_no,
				bkg_class,
				origin,
				destination,
				dep_date_formatted,
				dep_time_formatted,
				arr_date_formatted,
				arr_time_formatted,
				cabin_class,
				"non stop",
				"",
				flight_no[:2]  # Default to airline code
			)
			schedule.append(flight_info)
			operating_airline = None  # Reset after use
	
	df = pd.DataFrame(schedule, columns=[
		'Flight No',
		'Bkg Class',
		'From',
		'To',
		'Dep Date',
		'Dep Time',
		'Arr Date',
		'Arr Time',
		'Cabin Class', 
		'Transit Stops',
		'Layover Time',
		'Operating Airlines'])
	
	df['Airline'] = df['Flight No'].astype(str).str[:2]
	df['Flight Number'] = df['Flight No'].astype(str).str[2:]
	df['DepDate'] = pd.to_datetime(df['Dep Date'], format='%d-%b-%Y')
	df['ArrDate'] = pd.to_datetime(df['Arr Date'], format='%d-%b-%Y')
	
	# Calculate layover times between consecutive flights
	for index in range(len(df) - 1):
		current_arrival = pd.to_datetime(df.at[index, 'Arr Date'] + ' ' + df.at[index, 'Arr Time'])
		next_departure = pd.to_datetime(df.at[index + 1, 'Dep Date'] + ' ' + df.at[index + 1, 'Dep Time'])
		
		time_diff = next_departure - current_arrival
		
		# If layover is more than 24 hours, it's likely a separate trip segment
		if time_diff > pd.Timedelta(days=1):
			df.at[index, 'Layover Time'] = ''
		else:
			# Format layover time as "Xh Ym"
			hours = int(time_diff.total_seconds() // 3600)
			minutes = int((time_diff.total_seconds() % 3600) // 60)
			if hours > 0:
				df.at[index, 'Layover Time'] = f"{hours}h {minutes}m"
			else:
				df.at[index, 'Layover Time'] = f"{minutes}m"
	
	if df.empty:
		raise ValueError("No flights were recognised. Check the schedule source selected matches the text pasted.")
	df.at[df.index[-1], 'Layover Time'] = ''  # Last flight has no layover
	
	column_order = [
		'Flight No',
		'Airline',
		'Flight Number',
		'From',
		'Dep Date',
		'Dep Time',
		'To',
		'Arr Date',
		'Arr Time',
		'Cabin Class', 
		'Transit Stops',
		'Layover Time',
		'Operating Airlines']
	df = df[column_order]
	df['Operating Airlines'] = df['Operating Airlines'].apply(lambda x: airlines.get(x, x))
	return df

def format_amadeus_unconfirmed(text):
	amadeus_pattern = r"^\s*(\d{1,2})\s+([A-Z]{2}\s?\d{1,5})\s+([A-Z])\s+(\d{2}[A-Z]{3})\s+(\d+\*?)?\s*([A-Z0-9]{6})\s+([A-Z]{2}\d)\s+(\d{4})\s+(\d{4})\s+(\d{2}[A-Z]{3})\s+([A-Z])\s+([A-Z0-9]+)\s+([A-Z0-9]{2,3})?\s*([A-Z]{1,2})?\s*$"
	
	lines = text.strip().split("\n")

	filtered_lines = []
	for line in lines:
		# Check if line matches the pattern
		if re.match(amadeus_pattern, line):
			filtered_lines.append(line)
		# Or if it starts with "OPERATED BY" and doesn't contain "SUBSIDIARY/FRANCHISE"
		elif line.strip().startswith("OPERATED BY") and "SUBSIDIARY/FRANCHISE" not in line:
			filtered_lines.append(line)
		
	schedule = []
	operating_airline = None

	for line in filtered_lines:
		if "OPERATED BY" in line:
			operating_airline = line.strip().replace("OPERATED BY ", "")
			# Apply to the last flight added to schedule
			if schedule:
				# Update the last flight's operating airline
				last_flight = list(schedule[-1])
				last_flight[11] = operating_airline  # Index 11 is Operating Airlines
				schedule[-1] = tuple(last_flight)
			continue
		
		match = re.match(amadeus_pattern, line)
		if match:
			segment_num, flight_no, bkg_class, dep_date, day_indicator, route, status, dep_time, arr_time, arr_date, eticket, zero, fare_basis, letters = match.groups()
			
			# Remove whitespace from flight number
			flight_no = flight_no.replace(' ','')
			
			# Extract origin and destination from the 6-letter route code
			origin = route[:3]
			destination = route[3:]
			
			current_date = datetime.now()
			current_year = datetime.now().year

			# Try with current year first
			dep_date_obj = datetime.strptime(f"{dep_date}{current_year}", "%d%b%Y")
			
			if dep_date_obj < current_date:
				dep_date_obj = datetime.strptime(f"{dep_date}{current_year + 1}", "%d%b%Y")
			
			arr_date_obj = datetime.strptime(f"{arr_date}{current_year}", "%d%b%Y")
			
			if arr_date_obj < current_date:
				arr_date_obj = datetime.strptime(f"{arr_date}{current_year + 1}", "%d%b%Y")

			# Format dates
			dep_date_formatted = dep_date_obj.strftime("%d-%b-%Y")
			arr_date_formatted = arr_date_obj.strftime("%d-%b-%Y")

			# Format times from HHMM to HH:MM
			dep_time_formatted = f"{dep_time[:2]}:{dep_time[2:]}"
			arr_time_formatted = f"{arr_time[:2]}:{arr_time[2:]}" 
			
			# Determine cabin class from booking class (you may need to adjust this logic)
			cabin_class = get_cabin_class(flight_no[:2], bkg_class)
			
			flight_info = (
				flight_no,
				bkg_class,
				origin,
				destination,
				dep_date_formatted,
				dep_time_formatted,
				arr_date_formatted,
				arr_time_formatted,
				cabin_class,
				"non stop",
				"",
				flight_no[:2]  # Default to airline code
			)
			schedule.append(flight_info)
			operating_airline = None  # Reset after use
	
	df = pd.DataFrame(schedule, columns=[
		'Flight No',
		'Bkg Class',
		'From',
		'To',
		'Dep Date',
		'Dep Time',
		'Arr Date',
		'Arr Time',
		'Cabin Class', 
		'Transit Stops',
		'Layover Time',
		'Operating Airlines'])
	
	df['Airline'] = df['Flight No'].astype(str).str[:2]
	df['Flight Number'] = df['Flight No'].astype(str).str[2:]
	df['DepDate'] = pd.to_datetime(df['Dep Date'], format='%d-%b-%Y')
	df['ArrDate'] = pd.to_datetime(df['Arr Date'], format='%d-%b-%Y')
	
	# Calculate layover times between consecutive flights
	for index in range(len(df) - 1):
		current_arrival = pd.to_datetime(df.at[index, 'Arr Date'] + ' ' + df.at[index, 'Arr Time'])
		next_departure = pd.to_datetime(df.at[index + 1, 'Dep Date'] + ' ' + df.at[index + 1, 'Dep Time'])
		
		time_diff = next_departure - current_arrival
		
		# If layover is more than 24 hours, it's likely a separate trip segment
		if time_diff > pd.Timedelta(days=1):
			df.at[index, 'Layover Time'] = ''
		else:
			# Format layover time as "Xh Ym"
			hours = int(time_diff.total_seconds() // 3600)
			minutes = int((time_diff.total_seconds() % 3600) // 60)
			if hours > 0:
				df.at[index, 'Layover Time'] = f"{hours}h {minutes}m"
			else:
				df.at[index, 'Layover Time'] = f"{minutes}m"
	
	if df.empty:
		raise ValueError("No flights were recognised. Check the schedule source selected matches the text pasted.")
	df.at[df.index[-1], 'Layover Time'] = ''  # Last flight has no layover
	
	column_order = [
		'Flight No',
		'Airline',
		'Flight Number',
		'From',
		'Dep Date',
		'Dep Time',
		'To',
		'Arr Date',
		'Arr Time',
		'Cabin Class', 
		'Transit Stops',
		'Layover Time',
		'Operating Airlines']
	df = df[column_order]
	df['Operating Airlines'] = df['Operating Airlines'].apply(lambda x: airlines.get(x, x))
	return df

# ---------------------------------------------------------------------------
# Shared helpers for the newer parsers (Amadeus RTIM / FXD, Gold Medal)
# ---------------------------------------------------------------------------
SCHEDULE_COLUMNS = [
	'Flight No',
	'Bkg Class',
	'From',
	'To',
	'Dep Date',
	'Dep Time',
	'Arr Date',
	'Arr Time',
	'Cabin Class',
	'Transit Stops',
	'Layover Time',
	'Operating Airlines']

OUTPUT_COLUMN_ORDER = [
	'Flight No',
	'Airline',
	'Flight Number',
	'From',
	'Dep Date',
	'Dep Time',
	'To',
	'Arr Date',
	'Arr Time',
	'Cabin Class',
	'Transit Stops',
	'Layover Time',
	'Operating Airlines']

DATE_FMT = '%d-%b-%Y'

def format_duration(delta):
	"""timedelta -> 'Xh Ym' (or 'Ym' when under an hour), matching the other parsers."""
	total_minutes = int(delta.total_seconds() // 60)
	hours, minutes = divmod(total_minutes, 60)
	return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

def resolve_ddmmm_dates(ddmmm_list):
	"""
	Resolve year-less dates (e.g. '19FEB') into datetimes.
	The first date is the next occurrence on/after today; each later date is the next
	occurrence on/after the previous one, so itineraries crossing New Year roll correctly.
	"""
	floor = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
	resolved = []
	for ddmmm in ddmmm_list:
		for year in range(floor.year, floor.year + 5):
			try:
				candidate = datetime.strptime(f"{ddmmm.title()}{year}", "%d%b%Y")
			except ValueError:
				continue  # e.g. 29FEB in a non-leap year
			if candidate >= floor:
				break
		else:
			raise ValueError(f"Could not work out a valid date for '{ddmmm}'")
		resolved.append(candidate)
		floor = candidate
	return resolved

def build_schedule_df(rows, stopovers=None):
	"""
	Turn a list of 12-tuples (see SCHEDULE_COLUMNS) into the standard output DataFrame.
	stopovers: optional list of layover strings supplied by the source (blank = none).
	When omitted, layovers are calculated from the arrival/next departure times.
	"""
	if not rows:
		raise ValueError("No flights were recognised. Check the schedule source selected matches the text pasted.")

	df = pd.DataFrame(rows, columns=SCHEDULE_COLUMNS)
	df['Airline'] = df['Flight No'].astype(str).str[:2]
	df['Flight Number'] = df['Flight No'].astype(str).str[2:]

	if stopovers is not None:
		layovers = list(stopovers)
	else:
		arrivals = pd.to_datetime(df['Arr Date'] + ' ' + df['Arr Time'], format=f'{DATE_FMT} %H:%M')
		departures = pd.to_datetime(df['Dep Date'] + ' ' + df['Dep Time'], format=f'{DATE_FMT} %H:%M')
		layovers = [''] * len(df)
		for i in range(len(df) - 1):
			gap = departures[i + 1] - arrivals[i]
			# Only a connection if the next flight leaves from where the last one landed, within 24h.
			# Anything else is a separate trip segment (e.g. the return, or a surface gap).
			if df.at[i, 'To'] == df.at[i + 1, 'From'] and timedelta(0) <= gap <= timedelta(days=1):
				layovers[i] = format_duration(gap)
	df['Layover Time'] = layovers
	df['Operating Airlines'] = df['Operating Airlines'].apply(lambda x: airlines.get(x, x))
	return df[OUTPUT_COLUMN_ORDER]

def clean_pasted_text(text):
	"""Normalise line endings and non-breaking spaces (common when copying from web pages / Word)."""
	return text.replace('\r', '').replace('\xa0', ' ')

def hhmm_to_colon(t):
	return f"{t[:2]}:{t[2:]}"

# ---------------------------------------------------------------------------
# Amadeus - held / sold flights (RTIM)
# ---------------------------------------------------------------------------
# e.g.  "  1  SQ 202 N 19FEB 5 WSISIN HK1          2355 0505+1 *1A/E*"
#       "  2  SQ 308 N 20FEB 6 SINLHR HK1       3  0900 1520   *1A/E*"   (3 = terminal)
AMADEUS_RTIM_PATTERN = re.compile(
	r'^\s*\d{1,2}\s+'                      # segment number
	r'([A-Z0-9]{2})\s?(\d{1,4})\s+'        # airline, flight number
	r'([A-Z])\s+'                          # booking class
	r'(\d{2}[A-Z]{3})\s+'                  # departure date
	r'(?:\d\s+)?'                          # day of week
	r'([A-Z]{3})([A-Z]{3})\s+'             # origin + destination
	r'[A-Z]{2}\d+\s+'                      # status (HK1)
	r'(?:[A-Z0-9]{1,2}\s+)?'               # optional terminal
	r'(\d{4})\s+(\d{4})(?:\+(\d))?'        # dep time, arr time, +N days
)

def format_amadeus_rtim(text):
	rows = []
	for line in clean_pasted_text(text).split('\n'):
		m = AMADEUS_RTIM_PATTERN.match(line)
		if m:
			rows.append(m.groups())
	if not rows:
		return build_schedule_df([])

	dep_dates = resolve_ddmmm_dates([r[3] for r in rows])
	schedule = []
	for (airline, number, bkg_class, _, origin, dest, dep_time, arr_time, plus_days), dep_date in zip(rows, dep_dates):
		arr_date = dep_date + timedelta(days=int(plus_days or 0))
		schedule.append((
			f"{airline}{number}",
			bkg_class,
			origin,
			dest,
			dep_date.strftime(DATE_FMT),
			hhmm_to_colon(dep_time),
			arr_date.strftime(DATE_FMT),
			hhmm_to_colon(arr_time),
			get_cabin_class(airline, bkg_class),
			"non stop",
			"",
			airline))
	return build_schedule_df(schedule)

# ---------------------------------------------------------------------------
# Amadeus - FXD fare display
# ---------------------------------------------------------------------------
# e.g.  "1   EK 415  Q  19FEB  SYD 1 DXB 3  0600  1320   E0/388          30"
#       "    EK   3  Q  19FEB  DXB 3 LHR 3  1430  1820   E0/388  2320    30"
#       "2   EK  74  L  21FEB  CDG2C DXB 3  1425  0015+1 E0/388          30"  (2C = terminal)
#       "1QF AY5024  N  19FEB  SYD 1 BKK    1025  1610   ..."                 (QF = operating carrier)
#       " CX AY5091  Q  22FEB  HKG 1 SYD 1  2120  0935+1 ..."
_AL = r'(?:[A-Z][A-Z0-9]|[0-9][A-Z])'      # IATA airline code always contains a letter
AMADEUS_FXD_PATTERN = re.compile(
	r'^\s*\d?'                              # journey number (first segment of each journey only)
	rf'(?:({_AL})\s*(?={_AL}\s*\d{{1,4}}\s+[A-Z]\s+\d{{2}}[A-Z]{{3}}))?\s*'   # optional operating carrier
	rf'({_AL})\s*(\d{{1,4}})\s+'            # marketing airline, flight number
	r'([A-Z])\s+'                           # booking class
	r'(\d{2}[A-Z]{3})\s+'                   # departure date
	r'([A-Z]{3})(?:\d[A-Z])?\s+(?:\d\s+)?'  # origin (+ terminal, attached or separate)
	r'([A-Z]{3})(?:\s+\d)?\s+'              # destination (+ terminal)
	r'(\d{4})\s+(\d{4})(?:\+(\d))?'         # dep time, arr time, +N days
)

def format_amadeus_fxd(text):
	text = clean_pasted_text(text)
	# FXD returns many recommendations; each is a separate itinerary option.
	blocks = re.split(r'-+\s*RECOMMENDATION\s+\d+\s+OF\s+\d+[^\n]*', text)
	matched_blocks = []
	for block in blocks:
		block_rows = [m.groups() for m in map(AMADEUS_FXD_PATTERN.match, block.split('\n')) if m]
		if block_rows:
			matched_blocks.append(block_rows)
	if not matched_blocks:
		return build_schedule_df([])

	rows = matched_blocks[0]
	dep_dates = resolve_ddmmm_dates([r[4] for r in rows])
	schedule = []
	for (operating, airline, number, bkg_class, _, origin, dest, dep_time, arr_time, plus_days), dep_date in zip(rows, dep_dates):
		arr_date = dep_date + timedelta(days=int(plus_days or 0))
		schedule.append((
			f"{airline}{number}",
			bkg_class,
			origin,
			dest,
			dep_date.strftime(DATE_FMT),
			hhmm_to_colon(dep_time),
			arr_date.strftime(DATE_FMT),
			hhmm_to_colon(arr_time),
			get_cabin_class(airline, bkg_class),
			"non stop",
			"",
			operating or airline))
	df = build_schedule_df(schedule)
	if len(matched_blocks) > 1:
		df.attrs['note'] = (f"{len(matched_blocks)} fare recommendations were pasted. Only the first one was formatted - "
			"paste a single recommendation to format a different option.")
	return df

# ---------------------------------------------------------------------------
# Gold Medal - itinerary page ("Your Selected Flight Details")
# ---------------------------------------------------------------------------
GOLDMEDAL_ITINERARY_PATTERN = re.compile(
	r'^[ \t]*([A-Za-z ]+?)[ \t]*\(([A-Z])\)[ \t]*\n'                              # Economy (L)
	r'[ \t]*([A-Z0-9]{2}\d{1,4})[ \t]*\n'                                         # AI162
	r'[^\n]*\n'                                                                   # marketing airline name
	r'(?:[ \t]*Operated by ([^\n]+?)[ \t]*\n)?'                                   # optional operating airline
	r'[^\n]*\(([A-Z]{3})\)[ \t]*\n'                                               # origin
	r'[ \t]*(\d{2}:\d{2})[ \t]*/[ \t]*(\d{2}-[A-Za-z]{3}-\d{4})[ \t]*\n'          # dep time / date
	r'.*?\(([A-Z]{3})\)[ \t]*\n'                                                  # destination (terminal, duration, baggage skipped)
	r'[ \t]*(\d{2}:\d{2})[ \t]*/[ \t]*(\d{2}-[A-Za-z]{3}-\d{4})',                 # arr time / date
	re.M | re.S)

def _normalise_dmy(date_str, fmt):
	return datetime.strptime(date_str.title(), fmt).strftime(DATE_FMT)

def format_goldmedal_itinerary(text):
	text = clean_pasted_text(text)
	matches = list(GOLDMEDAL_ITINERARY_PATTERN.finditer(text))
	schedule, stopovers = [], []
	for i, m in enumerate(matches):
		cabin, bkg_class, flight_no, operator, origin, dep_time, dep_date, dest, arr_time, arr_date = m.groups()
		schedule.append((
			flight_no,
			bkg_class,
			origin,
			dest,
			_normalise_dmy(dep_date, DATE_FMT),
			dep_time,
			_normalise_dmy(arr_date, DATE_FMT),
			arr_time,
			cabin.strip(),
			"non stop",
			"",
			operator or flight_no[:2]))
		# "Stopover at Delhi, India (DEL)1h 10m" sits between this segment and the next
		gap_end = matches[i + 1].start() if i + 1 < len(matches) else m.end()
		stop = re.search(r'Stopover[^\n]*?\)\s*(\d+h\s*\d+m)', text[m.end():gap_end])
		stopovers.append(stop.group(1) if stop else '')
	return build_schedule_df(schedule, stopovers)

# ---------------------------------------------------------------------------
# Gold Medal - quote screen
# ---------------------------------------------------------------------------
GOLDMEDAL_QUOTE_PATTERN = re.compile(
	r'^(?:[ \t]*Operated by ([^\n]+?)[ \t]*\n)?'                                  # optional operating airline
	r'[ \t]*([A-Za-z ]+?)[ \t]*\(([A-Z])\)[ \t]*\n'                               # Economy (Q)
	r'[^\n]*\n'                                                                   # baggage (1PC)
	r'[ \t]*(\d{2} [A-Za-z]{3} \d{2})[ \t]*\n'                                    # 05 APR 27
	r'[ \t]*([A-Z]{3})(\d{2}:\d{2})[ \t]*\n'                                      # LCY13:10
	r'.*?^[ \t]*Flight ([A-Z0-9]{2}\d{1,4})[ \t]*\n'                              # city, terminal, duration skipped
	r'[ \t]*(\d{2} [A-Za-z]{3} \d{2})[ \t]*\n'                                    # arrival date
	r'[ \t]*([A-Z]{3})(\d{2}:\d{2})',                                             # ZRH15:50
	re.M | re.S)

def format_goldmedal_quote(text):
	text = clean_pasted_text(text)
	matches = list(GOLDMEDAL_QUOTE_PATTERN.finditer(text))
	schedule, stopovers = [], []
	for i, m in enumerate(matches):
		operator, cabin, bkg_class, dep_date, origin, dep_time, flight_no, arr_date, dest, arr_time = m.groups()
		schedule.append((
			flight_no,
			bkg_class,
			origin,
			dest,
			_normalise_dmy(dep_date, '%d %b %y'),
			dep_time,
			_normalise_dmy(arr_date, '%d %b %y'),
			arr_time,
			cabin.strip(),
			"non stop",
			"",
			operator or flight_no[:2]))
		# "Stopover at Zurich, Switzerland (ZRH) for 2h 5m" sits between this segment and the next
		gap_end = matches[i + 1].start() if i + 1 < len(matches) else m.end()
		stop = re.search(r'Stopover[^\n]*?\bfor\s+(\d+h\s*\d+m)', text[m.end():gap_end])
		stopovers.append(stop.group(1) if stop else '')
	return build_schedule_df(schedule, stopovers)

def generate_script(df):
	script = ""
	previous_segment_date = None
	for i, row in df.iterrows():
		departure_city = airport_codes.get(row['From'], row['From']) 
		arrival_city = airport_codes.get(row['To'], row['To']) 
		depart_time = row['Dep Time']
		arrive_time = row['Arr Time']
		airline = airlines.get(row["Airline"], row["Airline"])
		operating_airlines = row.get(row['Operating Airlines'], row['Operating Airlines']).strip()
		
		dep_time = datetime.strptime(depart_time, "%H:%M").strftime("%I:%M %p")
		arr_time = datetime.strptime(arrive_time, "%H:%M").strftime("%I:%M %p")
		
		current_segment_date = pd.to_datetime(row['Arr Date'])
		
		# For the first row, skip the logic until previous_segment_date is set
		if i==0:  #we know this is the first segment
			script_open = f"We're able to offer:\n\n"
		elif i == df.index[-1]:
			script_open = f'Our final leg would be '
		elif abs((current_segment_date - previous_segment_date).days) > 5:
			script_open = f'On the return we have'
		elif abs((current_segment_date - previous_segment_date).days) <= 2 :
			script_open = f'This flight would connect to'
		else:
			script_open = f'Next we have'
			
		# Update previous_segment_date after the check
		previous_segment_date = current_segment_date
		
		# Append the script_open to the overall script
		script += (script_open + f" **{airline}** flight **{row['Flight Number']}** departing from **{departure_city}** on **{row['Dep Date']}** at **{dep_time}** and arriving into **{arrival_city}** on **{row['Arr Date']}** at **{arr_time}**. This flight is operated by *{operating_airlines}*. \n\n")
		
	return script

st.set_page_config(layout='wide', page_title='Air Schedule Tool', page_icon=":material/flight:")

inject_theme()

display_price = 0
long_text = None

if 'format' not in st.session_state:
	st.session_state.format = False
	
if 'history' not in st.session_state:
	st.session_state.history = []
	
if 'text' not in st.session_state:
	st.session_state.text = ""
	
if 'price' not in st.session_state:
	st.session_state.price = ""
	
if 'widget' not in st.session_state:
	st.session_state.widget = ""

def clear_text():
	st.session_state.text = ""
	st.session_state.price = st.session_state.widget
	st.session_state.widget = ""
	

tab_air, tab_email = st.tabs(["Flight Schedules", "HTML Emails"])

# Rendered first so an st.stop() in the flight flow below can never cut this tab off.
with tab_email:
	render_email_formatter()

with tab_air:
	st.title("Formatting Tool")

	col1, col2, col3 = st.columns([0.34, 0.05, 0.561])

	with col1:
		sked_source = st.selectbox(label='Schedule Source - Where did you get your schedule from?',options=SCHEDULE_SOURCES, placeholder='Tropics', help="Selection dictates how the schedule gets parsed")
		GETflag = False
		if sked_source == 'AMADEUS':
			GETflag = st.checkbox('__Grand European Schedule__')
		st.markdown(
				'<hr style="border:1px solid rgba(49, 51, 63, 0.2); margin-top:5px; margin-bottom:5px;">',
				unsafe_allow_html=True
			)
		st.write("Paste your schedule below and the software will format it for you.")
		data = st.text_area(label='inputted schedule',label_visibility='collapsed', height=250, value=st.session_state.text)
		st.session_state.text = data
		recordPrice = st.toggle('**OPTIONAL - CAPTURE PRICE**\n\nUsed only to show price at time of formatting (when looking through previous requests)')
		if recordPrice:
			price_inputted = st.text_input('Schedule Price - per person',help="Price must be inputted before formatting otherwise it will not be captured", key = 'widget', placeholder=0)
			if price_inputted:
				if re.search(r'[a-zA-Z]', price_inputted):  # This regex allows only numbers and periods
					st.warning("Please enter a valid price without any letters.")
				else:
					# Optionally, you can further process the price here (like removing commas, etc.)
					price = re.sub(r'[^0-9.]', '', price_inputted)
			else:
				price = False
		else:
			price = False
		st.write('')
		st.write('')
		subcol1, subcol2 = st.columns([0.5, 0.5])
		with subcol1:
			format = st.button("Format Flight Schedule"	)
		with subcol2:
			if st.button('Clear', key='clear_button', on_click= clear_text):
				pass

	if format and data:
		timestamp = datetime.now()
		st.session_state.format = True
		if sked_source == 'Tropics':
			try:
				schedule = format_tropics_flights(data)
			except Exception as e:
				with col3:
					st.warning(f"Something went wrong while trying to parse flights:\n\n{e}")
					st.stop()
		if sked_source == 'Air Department':
			try:
				schedule = format_airdept_flights(data)
			except Exception as e:
				with col3:
					st.warning(f"Something went wrong while trying to parse flights:\n\n{e}")
					st.stop()
		if sked_source == 'AMADEUS':
			try:
				schedule = format_amadeus(data, get_flag=GETflag)
			except Exception as e:
				with col3:
					st.warning(f"Something went wrong while trying to parse flights:\n\n{e}")
					st.stop()
		if sked_source == 'AMADEUS - UNCONFIRMED':
			try:
				schedule = format_amadeus_unconfirmed(data)
			except Exception as e:
				with col3:
					st.warning(f"Something went wrong while trying to parse flights:\n\n{e}")
					st.stop()

		new_parsers = {
			'AMADEUS - HELD FLIGHTS (RTIM)': format_amadeus_rtim,
			'AMADEUS - FXD FARE DISPLAY': format_amadeus_fxd,
			'GOLD MEDAL - ITINERARY PAGE': format_goldmedal_itinerary,
			'GOLD MEDAL - QUOTE SCREEN': format_goldmedal_quote,
		}
		if sked_source in new_parsers:
			try:
				schedule = new_parsers[sked_source](data)
			except Exception as e:
				with col3:
					st.warning(f"Something went wrong while trying to parse flights:\n\n{e}")
					st.stop()

		if st.session_state.format and isinstance(schedule, pd.DataFrame):
			with col3:
				if schedule.attrs.get('note'):
					st.info(schedule.attrs['note'])
				try:
					st.markdown("### DOT SCRIPT", help = 'Only major airports are currently mapped. Some DOT scripts will return the Airport code, especially if lesser used airports are included in the schedule')
					script = generate_script(schedule)
					st.markdown(script)
				
					st.markdown(
						"<h5 style='color:red;'>Airfare is subject to rate change and availability until your reservation is confirmed with air deposit.</h5>",
						unsafe_allow_html=True
					)
				
					tropics_column_order = [
					'Flight No',
					'From',
					'To',
					'Dep Date',
					'Dep Time',
					'Arr Date',
					'Arr Time',
					'Cabin Class', 
					'Layover Time',
					'Operating Airlines']
				
					airdept_column_order = [
					'Flight No',
					'From',
					'To',
					'Dep Date',
					'Dep Time',
					'Arr Date',
					'Arr Time',
					'Cabin Class', 
					'Operating Airlines']
				
					formatted_df = schedule[airdept_column_order] if sked_source == "Air Department" else schedule[tropics_column_order]
					# Convert the DataFrame to HTML with inline CSS to force gridlines
					html_table = formatted_df.to_html(classes='custom-table1 table-bordered', index=False)

					# Custom CSS for gridlines
					css1 = """
						<style>
							.custom-table1 {
								border: 2px solid black;
								border-collapse: collapse;
								margin-left: auto;
								margin-right: auto;
							}
							.custom-table1 th, .custom-table1 td {
								border: 1px solid black;
								padding: 8px;
								text-align: center;  /* Center align text in both th and td */
							}
						</style>
					"""
					# Render the DataFrame with gridlines in Streamlit
					st.markdown(css1, unsafe_allow_html=True)
					st.markdown(html_table, unsafe_allow_html=True)

					st.session_state.history.append({
						"timestamp": timestamp,
						"schedule": formatted_df,
						"script": script,
						"price": float(price) if price else ''
						})
		
				except Exception as e:
						st.error(f"There was an error with formatting the provided schedule or generating the DOT Script. Please review the schedule inputted to ensure its copied/pasted correctly and the correct schedule source is selected. \n\nErrorMessage: {e}")
						st.markdown("Based on what was provided, the current output for the schedule is:")
						st.dataframe(schedule)

	# Toggle to show/hide history
	st.write("-" * 50)
	show_history = st.checkbox("Show Previous Requests")

	if show_history and st.session_state.history:
		st.subheader("Past Schedules")
		for idx, entry in enumerate(reversed(st.session_state.history), 1):
			st.markdown(f"Run Order: **{len(st.session_state.history) - idx + 1}**\n\nRuntime: **{entry['timestamp']}**")
			if isinstance(entry['price'], float):
				formatted_price = f"Price Inputted at Time of Formatting: **${entry['price']:,.2f}**"
			else:
				formatted_price = 'No price inputted at time of formatting'
			st.markdown(formatted_price)
			st.markdown("##### Formatted Schedule:")
			historic_df = pd.DataFrame(entry['schedule'])
			historic_html = historic_df.to_html(classes='custom-table2 table-bordered', index=False)
			# Custom CSS for gridlines
			css2 = """
				<style>
					.custom-table2 {
						border: 2px solid black;
						border-collapse: collapse;
						align: left;
					}
					.custom-table2 th, .custom-table2 td {
						border: 1px solid black;
						padding: 8px;
						text-align: center;  /* Center align text in both th and td */
					}
					.st-emotion-cache-1h9usn1 {
						margin-bottom: 0px;
						margin-top: 0px;
						margin-left: 0px;
						width: 70%;
						border-style: solid;
						border-width: 1px;
						border-color: rgba(49, 51, 63, 0.2);
						border-radius: 0.5rem;
					}
				</style>
			"""
			# Render the DataFrame with gridlines in Streamlit
			st.markdown(css2, unsafe_allow_html=True)
			st.markdown(historic_html, unsafe_allow_html=True)
			previous_script = st.expander('Auto-generated script')
			previous_script.write(f"#### Script: \n\n{entry['script']}")
			previous_script.markdown(
					"<h5 style='color:red;'>Airfare is subject to rate change and availability until your reservation is confirmed with air deposit.</h5>",
					unsafe_allow_html=True
				)
			st.write("-" * 50)
