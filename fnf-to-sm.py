# fnf-to-sm.py
# FNF to SM converter
# Copyright (C) 2021 shockdude

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <https://www.gnu.org/licenses/>.

# Built from the original chart-to-sm.js by Paturages, released under GPL3 with his permission

import re
import json
import math
import sys
import os

VERSION = "v0.1.2"

SM_EXT = ".sm"
SSC_EXT = ".ssc"
FNF_EXT = ".json"

# stepmania editor's default note precision is 1/192
MEASURE_TICKS = 192
BEAT_TICKS = 48
# fnf step = 1/16 note
STEP_TICKS = 12

NUM_COLUMNS = 4

# borrowed from my Sharktooth code
class TempoMarker:
	def __init__(self, bpm, tick_pos, time_pos):
		self.bpm = float(bpm)
		self.tick_pos = tick_pos
		self.time_pos = time_pos

	def getBPM(self):
		return self.bpm

	def getTick(self):
		return self.tick_pos
		
	def getTime(self):
		return self.time_pos
	
	def timeToTick(self, note_time):
		return int(round(self.tick_pos + (float(note_time) - self.time_pos) * MEASURE_TICKS * self.bpm / 240000))
		
	def tickToTime(self, note_tick):
		return self.time_pos + (float(note_tick) - self.tick_pos) / MEASURE_TICKS * 240000 / self.bpm

# compute the maximum note index step per measure
def measure_gcd(num_set, MEASURE_TICKS):
	d = MEASURE_TICKS
	for x in num_set:
		d = math.gcd(d, x)
		if d == 1:
			return d
	return d;

tempomarkers = []

# helper functions for handling global tempomarkers 
def timeToTick(timestamp):
	for i in range(len(tempomarkers)):
		if i == len(tempomarkers) - 1 or tempomarkers[i+1].getTime() > timestamp:
			return tempomarkers[i].timeToTick(timestamp)
	return 0
			
def tickToTime(tick):
	for i in range(len(tempomarkers)):
		if i == len(tempomarkers) - 1 or tempomarkers[i+1].getTick() > tick:
			return tempomarkers[i].tickToTime(tick)
	return 0.0

def tickToBPM(tick):
	for i in range(len(tempomarkers)):
		if i == len(tempomarkers) - 1 or tempomarkers[i+1].getTick() > tick:
			return tempomarkers[i].getBPM()
	return 0.0

def fnf_to_sm(infile):
	chart_jsons = []
	
	# given a normal difficulty .json,
	# try to detect all 3 FNF difficulties if possible
	infile_name, infile_ext = os.path.splitext(infile)
	infile_easy = infile_name + "-easy" + FNF_EXT
	infile_hard = infile_name + "-hard" + FNF_EXT
	
	with open(infile, "r") as chartfile:
		chart_json = json.loads(chartfile.read().strip('\0'))
		chart_json["diff"] = "Medium"
		chart_jsons.append(chart_json)
		
	if os.path.isfile(infile_easy):
		with open(infile_easy, "r") as chartfile:
			chart_json = json.loads(chartfile.read().strip('\0'))
			chart_json["diff"] = "Easy"
			chart_jsons.append(chart_json)
			
	if os.path.isfile(infile_hard):
		with open(infile_hard, "r") as chartfile:
			chart_json = json.loads(chartfile.read().strip('\0'))
			chart_json["diff"] = "Hard"
			chart_jsons.append(chart_json)

	chartWho = input("Who's side would you like to convert? (boyfriend/dad)").lower()
	if chartWho == "" or chartWho != "boyfriend" and chartWho != "dad":
		chartWho = "boyfriend"

	# for each fnf difficulty
	sm_header = ''
	sm_notes = ''
	for chart_json in chart_jsons:
		song_notes = chart_json["song"]["notes"]
		num_sections = len(song_notes)
		# build sm header if it doesn't already exist
		if len(sm_header) == 0:
			song_name = chart_json["song"]["song"]
			song_bpm = chart_json["song"]["bpm"]
			
			print("Converting {} to {}.sm".format(infile, song_name))

			# build tempomap
			bpms = "#BPMS:"
			current_bpm = None
			current_tick = 0
			current_time = 0.0
			for i in range(num_sections):
				section = song_notes[i]
					
				if section.get("changeBPM", 0) != 0:
					section_bpm = float(section["bpm"])
				elif current_bpm == None:
					section_bpm = song_bpm
				else:
					section_bpm = current_bpm
				if section_bpm != current_bpm:
					tempomarkers.append(TempoMarker(section_bpm, current_tick, current_time))
					bpms += "{}={},".format(i*4, section_bpm)
					current_bpm = section_bpm

				# each step is 1/16
				section_num_steps = section["lengthInSteps"]
				# default measure length = 192
				section_length = STEP_TICKS * section_num_steps
				time_in_section = 15000.0 * section_num_steps / current_bpm

				current_time += time_in_section
				current_tick += section_length

			# add semicolon to end of BPM header entry
			bpms = bpms[:-1] + ";\n"

			# write .sm header
			sm_header = "#TITLE:{}\n".format(song_name)
			sm_header += "#MUSIC:{}.ogg;\n".format(song_name)
			sm_header += bpms

		notes = {}
		last_note = 0
		diff_value = 1

		# convert note timestamps to ticks
		for i in range(num_sections):
			section = song_notes[i]
			section_notes = section["sectionNotes"]
			for section_note in section_notes:
				tick = timeToTick(section_note[0])
				note = section_note[1]
				mustHit = False
				if section["mustHitSection"]:
					mustHit = True
				if ((note < 4 and chartWho == "boyfriend" and mustHit) or (not mustHit and note >= 4 and chartWho == "boyfriend")) or (note >= 4 and chartWho == "dad" and mustHit or not mustHit and note < 4 and chartWho == "dad"):
					length = section_note[2]
					
					# Initialize a note for this tick position
					if tick not in notes:
						notes[tick] = [0]*NUM_COLUMNS

					print(note, mustHit, chartWho)

					note = (note) % 4

					if length == 0:
						notes[tick][note] = 1
					else:
						notes[tick][note] = 2
						# 3 is "long note toggle off", so we need to set it after a 2
						long_end = timeToTick(section_note[0] + section_note[2])
						if long_end not in notes:
							notes[long_end] = [0]*NUM_COLUMNS
						notes[long_end][note] = 3
						if last_note < long_end:
							last_note = long_end

					if last_note <= tick:
						last_note = tick + 1

		if len(notes) > 0:
			# write chart & difficulty info
			sm_notes += "\n"
			sm_notes += "#NOTES:\n"
			sm_notes += "	  dance-single:\n"
			sm_notes += "	  :\n"
			sm_notes += "	  {}:\n".format(chart_json["diff"]) # e.g. Challenge:
			sm_notes += "	  {}:\n".format(diff_value)
			sm_notes += "	  :\n" # empty groove radar

			# ensure the last measure has the correct number of lines
			if last_note % MEASURE_TICKS != 0:
				last_note += MEASURE_TICKS - (last_note % MEASURE_TICKS)

			# add notes for each measure
			for measureStart in range(0, last_note, MEASURE_TICKS):
				measureEnd = measureStart + MEASURE_TICKS
				valid_indexes = set()
				for i in range(measureStart, measureEnd):
					if i in notes:
						valid_indexes.add(i - measureStart)
				
				noteStep = measure_gcd(valid_indexes, MEASURE_TICKS)

				for i in range(measureStart, measureEnd, noteStep):
					if i not in notes:
						sm_notes += '0'*NUM_COLUMNS + '\n'
					else:
						for digit in notes[i]:
							sm_notes += str(digit)
						sm_notes += '\n'

				if measureStart + MEASURE_TICKS == last_note:
					sm_notes += ";\n"
				else:
					sm_notes += ',\n'

	# output simfile
	with open("{}.sm".format(song_name), "w") as outfile:
		outfile.write(sm_header)
		if len(sm_notes) > 0:
			outfile.write(sm_notes)

# get simple header tag value
def get_tag_value(line, tag):
	tag_re = re.compile("#{}:(.+)\\s*;".format(tag))
	re_match = tag_re.match(line)
	if re_match != None:
		value = re_match.group(1)
		return value
	# try again without a trailing semicolon
	tag_re = re.compile("#{}:(.+)\\s*".format(tag))
	re_match = tag_re.match(line)
	if re_match != None:
		value = re_match.group(1)
		return value
	return None

# parse the BPMS out of a simfile
def parse_sm_bpms(bpm_string):
	sm_bpms = bpm_string.split(",")
	bpm_re = re.compile("(.+)=(.+)")
	for sm_bpm in sm_bpms:
		re_match = bpm_re.match(sm_bpm)
		if re_match != None and re_match.start() == 0:
			current_tick = int(round(float(re_match.group(1)) * BEAT_TICKS))
			current_bpm = float(re_match.group(2))
			current_time = tickToTime(current_tick)
			tempomarkers.append(TempoMarker(current_bpm, current_tick, current_time))

def sm_to_fnf(infile):
	title = "Simfile"
	fnf_notes = []
	section_number = 0
	offset = 0
	print("Converting {} to blammed.json".format(infile))
	with open(infile, "r") as chartfile:
		line = chartfile.readline()
		while len(line) > 0:
			value = get_tag_value(line, "TITLE")
			if value != None:
				title = value
				line = chartfile.readline()
				continue
			value = get_tag_value(line, "OFFSET")
			if value != None:
				offset = float(value) * 1000
				line = chartfile.readline()
				continue
			value = get_tag_value(line, "BPMS")
			if value != None:
				parse_sm_bpms(value)
				line = chartfile.readline()
				continue

			# regex for a sm note row
			notes_re = re.compile("^[\\dM][\\dM][\\dM][\\dM]$")

			# TODO support SSC
			if line.strip() == "#NOTES:":
				line = chartfile.readline()
				if line.strip() != "dance-single:":
					line = chartfile.readline()
					continue
				chartfile.readline()
				line = chartfile.readline()
				
				# TODO support difficulties other than Challenge
				if line.strip() != "Challenge:":
				#if line.strip() != "Hard:":
					line = chartfile.readline()
					continue
				chartfile.readline()
				chartfile.readline()
				line = chartfile.readline()
				tracked_holds = {} # for tracking hold notes, need to add tails later
				while line.strip()[0] != ";":
					measure_notes = []
					while line.strip()[0] not in (",",";"):
						if notes_re.match(line.strip()) != None:
							measure_notes.append(line.strip())
						line = chartfile.readline()
					
					# for ticks-to-time, ticks don't have to be integer :)
					ticks_per_row = float(MEASURE_TICKS) / len(measure_notes)
					
					fnf_section = {}
					fnf_section["lengthInSteps"] = 16
					fnf_section["bpm"] = tickToBPM(section_number * MEASURE_TICKS)
					if len(fnf_notes) > 0:
						fnf_section["changeBPM"] = fnf_section["bpm"] != fnf_notes[-1]["bpm"]
					else:
						fnf_section["changeBPM"] = False
					fnf_section["mustHitSection"] = True
					fnf_section["typeOfSection"] = 0
					
					section_notes = []
					for i in range(len(measure_notes)):
						notes_row = measure_notes[i]
						for j in range(len(notes_row)):
							if notes_row[j] in ("1","2","4"):
								note = [tickToTime(MEASURE_TICKS * section_number + i * ticks_per_row) - offset, j, 0]
								section_notes.append(note)
								if notes_row[j] in ("2","4"):
									tracked_holds[j] = note
							# hold tails
							elif notes_row[j] == "3":
								if j in tracked_holds:
									note = tracked_holds[j]
									del tracked_holds[j]
									note[2] = tickToTime(MEASURE_TICKS * section_number + i * ticks_per_row) - offset - note[0]
					
					fnf_section["sectionNotes"] = section_notes
					
					section_number += 1
					fnf_notes.append(fnf_section)
					
					# don't skip the ending semicolon
					if line.strip()[0] != ";":
						line = chartfile.readline()
			
			line = chartfile.readline()
			
	# assemble the fnf json
	chart_json = {}
	chart_json["song"] = {}
	#chart_json["song"]["song"] = title
	chart_json["song"]["song"] = "Blammed"
	chart_json["song"]["notes"] = fnf_notes
	chart_json["song"]["bpm"] = tempomarkers[0].getBPM()
	chart_json["song"]["sections"] = 0
	chart_json["song"]["needsVoices"] = False
	chart_json["song"]["player1"] = "bf"
	chart_json["song"]["player2"] = "pico"
	chart_json["song"]["sectionLengths"] = []
	chart_json["song"]["speed"] = 2.0
	
	#with open("{}.json".format(title), "w") as outfile:
	with open("blammed.json".format(title), "w") as outfile:
		json.dump(chart_json, outfile)

def usage():
	print("FNF SM converter")
	print("Usage: {} [chart_file]".format(sys.argv[0]))
	print("where [chart_file] is a .json FNF chart or a .sm simfile")
	sys.exit(1)

def main():
	if len(sys.argv) < 2:
		print("Error: not enough arguments")
		usage()
	
	infile = sys.argv[1]
	infile_name, infile_ext = os.path.splitext(os.path.basename(infile))
	if infile_ext == FNF_EXT:
		fnf_to_sm(infile)
	elif infile_ext == SM_EXT:
		sm_to_fnf(infile)
	else:
		print("Error: unsupported file {}".format(infile))
		usage()

if __name__ == "__main__":
	main()
