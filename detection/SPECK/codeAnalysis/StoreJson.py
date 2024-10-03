#!/usr/bin/python3

from FileReader import *
from Parser import *
from R import *
import os
import json
import pymongo
import pandas as pd

# import additional.source_code_mapping as src_mapping
# import additional.context_extraction_single as context
from additional.mapper import Mapper

SRC_CODES_DIRECTORY_PATH = "/home/elis/Desktop/uni/assegno/llm_x_apr/fdroid/fdroid-src-codes" # write here path to the folder containing all the src codes fot the apps to be analysed
APKS_DIRECTORY_PATH = "/home/elis/Desktop/uni/assegno/llm_x_apr/fdroid/apkss/decompiled" # write here path to the folder containing all downloaded apks, leave /decompiled as it is
MAPPING_CSV_PATH = "/home/elis/Desktop/uni/assegno/llm_x_apr/llm-evaluation-master/mapping_apk_to_src.csv"  # write here the mapping between apk name and its source code project folder name


class MongoConfig():
	def __init__(self, uri):
		self.uri = uri

class StoreJson():
	outputcol = None

	@staticmethod
	def initMongoDb(cfg: MongoConfig):

		if StoreJson.outputcol:
			return
			
		uri = cfg.uri
		db_name = uri.split("/")[-1]
		myclient = pymongo.MongoClient(uri)
		mydb = myclient[db_name]

		StoreJson.outputcol = mydb["rawoutput"]
		StoreJson.rulestats = mydb["rulestats"]

	@staticmethod
	def store(collection, rec, cfg: MongoConfig):
		if not rec:
			return

		#if cfg.db == None:	# database is not in use
		#	return

		if StoreJson.outputcol == None:
			StoreJson.initMongoDb(cfg)

		if collection == "outputcol":
			outputcol_cursor = StoreJson.outputcol.find()		# retrieve all outputcol
			found = False
			for x in outputcol_cursor:
				# additional: the option below is just saving one entry per rule given the same apk
				# if more lines are violating the same rule in the same file, they are not saved
				# to check if the analysis has been already done, this check is not enough
				# compare also with line number, code AND file
				#if rec["apk"] == x["apk"] and rec["rule"] == x["rule"]:			# check if the analysis of the app was already done on the rule 
				if rec["apk"] == x["apk"] and rec["file"] == x["file"] and rec["rule"] == x["rule"] and rec["lineNumber"] == x["lineNumber"] and rec["code"] == x["code"]:
					print(f"\033[1m\033[33m[!] App {rec['apk']} was already analysed on Rule {rec['rule']}!\033[0m\033[0m")
					found = True
					break
			if not found:										# if new analysis, then add its outputcol in the db
				# E: adding src code information 
				mapper = Mapper(rec)
				new_rec = mapper.get_updated_record()

				# rec["src_codes"], rec["src_code_line_numbers"], rec["src_paths"], rec["language"] = src_mapping.map(rec, SRC_CODES_DIRECTORY_PATH, MAPPING_CSV_PATH)
				# rec["compilable"] = src_mapping.is_compilable(f"{rec['apk']}.apk", MAPPING_CSV_PATH)
				# if rec["src_paths"] != "NO SOURCE CODE":
				# 	rec["src_code_context"] = context.extract(rec, SRC_CODES_DIRECTORY_PATH)
				# 	rec["src_paths"] = rec["src_paths"].split(SRC_CODES_DIRECTORY_PATH)[-1]

				StoreJson.outputcol.insert_one(new_rec)

		elif collection == "rulestats":
			rulestats_cursor = StoreJson.rulestats.find()		# retrieve all rulestats
			found = False
			for x in rulestats_cursor:
				if rec["apk"] == x["apk"] and rec["rule"] == x["rule"]:
					print(f"\033[1m\033[35m[!] App {rec['apk']} was already analysed on Rule {rec['rule']}!\033[0m\033[0m")
					# print(x)									# print the analysis previously stored
					found = True
					break
			if not found:										# if new analysis, then add its rulestats in the db
				StoreJson.rulestats.insert_one(rec)

		else:
			print(f"Collection {collection} does not exist!!")
			exit(0)


	@staticmethod
	def showResults(results, nb, Reader, packageDir, validation, nr, apk, mongo_cfg=None, errorMsg=""):
		# print(f'self.results: {results}')
		for file in results:
			kind = "[EXTERNAL]"
			if ((packageDir != None) and (packageDir in file[0])) or ("AndroidManifest.xml" in file[0]):
				kind = "[INTERNAL]"

			for X in [R.WARNING, R.CRITICAL, R.OK]:
				if X in file[1] and len(file[1][X]) > 0:
					fileReader = Reader(file[0], False)
					lineNumber = -1
					for i in file[1][X]:
						if i[R.INSTR] != '':
							lineNumber = fileReader.getLine(i[R.INSTR], i)
							
							if lineNumber == -1:
								lineNumber = fileReader.getLine(i[R.INSTR][:30], i)

						else:
							lineNumber = -1
						
						apk_name = apk.split('/')[-1]
						myRecord = {}
						myRecord['severity'] = X
						myRecord['apk'] = apk_name
						myRecord['kind'] = kind
						myRecord['file'] = file[0].split(APKS_DIRECTORY_PATH)[-1]
						myRecord['lineNumber'] = lineNumber
						myRecord['code'] = i[R.INSTR]
						myRecord['rule'] = nr
						myRecord['errorMsg'] = errorMsg

						eMsg = ""
						for e in file[1][X]:
							if "eMsg" in e:
								eMsg = e["eMsg"]

						myRecord['eMsg'] = eMsg

						StoreJson.store("outputcol", myRecord, mongo_cfg)
						
				



