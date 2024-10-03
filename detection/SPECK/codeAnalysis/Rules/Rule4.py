#!/usr/bin/python3

from Rules import *
from FileReader import *
from Parser import *
from R import *
from Common import *
import sys


'''
RULE N°4 -- UPDATED

+ Use intents to defer permissions
** Whenever possible, don't add a permission to your app to complete an action that could be completed in another app.
** Instead, use an intent to defer the request to a different app that already has the necessary permission.
-> https://developer.android.com/topic/security/best-practices#permissions
-> https://developer.android.com/guide/topics/permissions/overview#permission-groups

? Pseudo Code:
	1. Get all permissions' names
	2. Compare with a blacklist

! Output
	-> NOTHING	: no dangerous permission found
	-> WARNING	: dangerous permission found
'''

class Rule4(Rules):
	def __init__(self, directory, database, verbose=True, verboseDeveloper=False, storeManager=None, flowdroid=False, platform="",validation=False, quiet=True):
		Rules.__init__(self, directory, database, verbose, verboseDeveloper, storeManager, flowdroid, platform, validation, quiet)

		self.mapDir = DIR + '/../permissions-mapping/'

		self.AndroidErrMsg = "permission(s) complete actions that could be completed by another app"
		self.AndroidOkMsg = "no dangerous permission is used"
		self.AndroidText = "https://developer.android.com/topic/security/best-practices#permissions"

		self.okMsg = "There is no permission to defer"		
		self.errMsg = "Function(s) can use dangerous permission(s)"
		self.category = R.CAT_1

		self.targetSdkVersion = "25" # latest available
		
		self.findXml()
		self.show(4, "Use intents to defer permissions")

	def getDangerousPermissions(self, xmlReader, permissions):
		prefix = "android.permission."
		
		blackList = ['READ_CALENDAR'	, 'WRITE_CALENDAR'			, 'CAMERA', 'READ_CONTACTS'	, 'WRITE_CONTACTS'	,
					 'GET_ACCOUNTS'		, 'ACCESS_FINE_LOCATION'	, 'ACCESS_COARSE_LOCATION'	, 'RECORD_AUDIO'	,
					 'READ_PHONE_NUMBERS'		, 'READ_SMS'				, 'RECEIVE_SMS'		,
					 'CALL_PHONE'		, 'ANSWER_PHONE_CALLS'		, 'READ_CALL_LOG'			, 'WRITE_CALL_LOG'	,
					 'USE_SIP'			, 'PROCESS_OUTGOING_CALLS', 'SEND_SMS'		, 
					 'RECEIVE_WAP_PUSH'	, 'RECEIVE_MMS'				, 'READ_EXTERNAL_STORAGE'	, 'ADD_VOICEMAIL' ]
		'''
		-> What to use to avoid these dangerous permissions ?
		CALENDAR 	: CalendarContract
		CAMERA	 	: MediaStore
		CONTACTS 	: ContactsContract
		LOCATION 	: Intent.ACTION_VIEW
		MICROPHONE 	: MediaRecorder
		PHONE 		: Intent.ACTION_DIAL
		SENSORS 	: SensorManager
		SMS 		: Intent.ACTION_SEND
		STORAGE 	: Intent.ACTION_GET_CONTENT
		'''

		blackList = [prefix + s for s in blackList]
		dangerousPermissions = []
		for p in permissions:
			for arg in p[XmlReader.ARGS]:
				if 'android:name=' in arg:
					value = xmlReader.getArgValue(arg)
					if value in blackList:
						dangerousPermissions.append(p)
					break
		return dangerousPermissions


	def run(self):
		self.loading()

		if self.manifest != None:
			xmlReader = XmlReader(self.manifest)

			# 1. Get targetSdkVersion 
			self.targetSdkVersion = self.getTargetSdkVersion(xmlReader)
			if self.targetSdkVersion != None:
					
					# 2. Get all permissions in Manifest File
				permissionsArgs = xmlReader.getArgsTag("uses-permission")
				dangerousPermissions = self.getDangerousPermissions(xmlReader, permissionsArgs)
					
				# 3. Get all functions names associated with permissions found in FRAMEWORK/SDK files
				funcNames = self.getFuncMapped(dangerousPermissions, '::')

				# 4. Get all contents  associated with permissions found in CP file
				contentNames = self.getCpMapped(dangerousPermissions)

				# 5. Get all 'funcNames' / 'contentNames' not used in .java files
				
				notUsed = self.getUnusedPermissions(funcNames.copy(), contentNames.copy(), dangerousPermissions.copy())
				
				# construct token for each file
				for elem in notUsed:
					dangerous_func = elem[0]
					listPerm = elem[1]
					file = elem[2]
					fileReader = FileReader(file)
					found = Common.search_keywords(fileReader, [dangerous_func])	#token
			
					found = Parser.setMsg(found, R.WARNING, self.errMsg + ": " + ", ".join(listPerm))
					
					# self.updateWN(xmlReader.getFile(), NotIn)
					self.updateWN(file, found)
					self.loading()
					fileReader.close()

				
				# xmlReader.close()

				self.store(4, self.AndroidOkMsg, self.AndroidErrMsg, self.AndroidText, self.category, True)
				self.display(XmlReader)

			else:
				self.loading()



	def getFuncMapped(self, permissions, sp):
		functions = []
		# SDK-MAP AND FRAMEWORK-MAP FILES
		mapFiles = [self.mapDir + 'sdk-map-'+ self.targetSdkVersion + '.txt', self.mapDir + 'framework-map-'+ self.targetSdkVersion + '.txt']
		for mapFile in mapFiles:
			with open(mapFile) as file:
				while True:
					line = file.readline()
					if line == '':
						break
					p = line.split(sp)[1].strip().split(', ')			
					index = 0
					for elem in p:
						for perm in permissions:
							if elem.strip() in perm[R.INSTR]:
								index += 1
								
					if index != 0: #and index == len(p):
						# [package, permissions]
						functions.append([line.split(sp)[0].strip(), line.split(sp)[1].strip()])
	
		return functions

	def getCpMapped(self, permissions):
		contents = []

		# CP-MAP FILE
		with open(self.mapDir + 'cp-map-'+ self.targetSdkVersion + '.txt') as file:
			while True:
				line = file.readline()
				if line == '':
					break
				
				if "[grant-uri-permission]" not in line:
					p = ' '.join(line.split()).split(' ')[-1]

					for perm in permissions:
						if p in perm[R.INSTR]:
							contents.append([' '.join(line.split()).split(' ')[0], ' '.join(line.split()).split(' ')[1], p])

		return contents

	def extractPkgNames(self, package):
		pkgList = []

		split = package.split('.')
		pkg = split[0]+".*"
		for i in range(1, len(split)-1):
			pkgList.append(pkg)
			pkg = pkg[0:len(pkg)-2]+"."+split[i]+".*"
		
		pkgList.append(pkg[0:len(pkg)-2]+".*")
		pkgList.append(pkg[0:len(pkg)-2])
		pkgList.append(package)
		return pkgList

	def packageIsIn(self, packageList, packagesImported):
		for listElem in packageList:
			for pImported in packagesImported:
				if listElem == pImported:
					return True

		return False

	def getAllPkg(self, funcNames, contentNames):
		pkgs = []

		for e in funcNames:
			pkgs += self.extractPkgNames(e[0].split('(')[0])

		for e in contentNames:
			pkgs += self.extractPkgNames(e[0])
		
		return pkgs

	def getUnusedPermissions(self, funcNames, contentNames, permissions):
		cpy = funcNames.copy()
		cpyContent = contentNames.copy()
		permissions = permissions.copy()
		to_return = []

		filt = Filter(self.directory, self.getAllPkg(funcNames, contentNames))
		javaFiles = filt.execute() # Parser.getAllPath(self.directory, '.java')

		self.maxFiles = len(javaFiles)

		for file in javaFiles:
			if ((self.packageDir != None) and (self.packageDir in file)) or ("AndroidManifest.xml" in file):
				# print(f'getUnusedPermissions-file: {file}\n')

				self.loading()
				packagesImported = []

				fileReader = FileReader(file)
				line, _ = fileReader.getNextInstruction()
				while line != '':
					# Get all packages in file
					if 'import ' in line:
						x = line.split(' ')[1].split(';')[0].strip()
						packagesImported.append(line.split(' ')[1].split(';')[0].strip())
						
					else:

						# FUNCNAMES 
						for elem in funcNames:
							listPerm = elem[-1].split(', ')
							funcName = elem[0].split('(')[0].split('.')[-1]
							package_func = elem[0].split('(')[0]
							
							# Get all packages extension
							packageList = self.extractPkgNames(package_func)
							
							# Check if function and package are in the file
							if (((funcName+'(' or funcName+' (') in line) 
								and self.packageIsIn(packageList, packagesImported)):
								# print(f'getUnusedPermissions-inIf: found')
									if not [funcName, listPerm, file] in to_return:
										to_return.append([funcName, listPerm, file])

						# CONTENTNAMES 
						for elem in contentNames:
							listPerm = elem[-1].split(', ')
							cName = elem[1]
							package = elem[0]

							# Get all packages extension
							packageList = self.extractPkgNames(package)

							# Check if content and package are in the file
							if ((cName in line) 
								and self.packageIsIn(packageList, packagesImported)):
								if not [cName, listPerm, file] in to_return:
									to_return.append([cName, listPerm, file])


					line, _ = fileReader.getNextInstruction()
				
				fileReader.close()
		
		return to_return
		

	def getPermissionsNotUsed(self, xmlReader, permissionsArgs, notUsed):
		permNotUsed = []

		for p in permissionsArgs:
			for arg in p[XmlReader.ARGS]:
				if 'android:name=' in arg:
					value = xmlReader.getArgValue(arg)

					for elem in notUsed:
						if value in elem.split(', '):
							permNotUsed.append(p)
							break
					break

		return permNotUsed

	def getTargetSdkVersion(self, xmlReader):

		targetSdkVersion = '25'

		tag = xmlReader.getArgsTag("uses-sdk")

		tagM = xmlReader.getArgsTag("manifest")

		for t in tag:
			for arg in t[XmlReader.ARGS]:
				if "android:targetSdkVersion=" in arg:
					value = xmlReader.getArgValue(arg)
				
					if os.path.isfile(self.mapDir + 'sdk-map-'+ value + '.txt'):
						targetSdkVersion = value
					else:
						# assign it as default since it is the latest one available
						targetSdkVersion = '25'

		for t in tagM:
			for arg in t[XmlReader.ARGS]:
				if "platformBuildVersionCode=" in arg:
					value = xmlReader.getArgValue(arg)

					if os.path.isfile(self.mapDir + 'sdk-map-'+ value + '.txt'):
						targetSdkVersion = value
					else:
						# assign it as default since it is the latest one available
						targetSdkVersion = '25'

		return targetSdkVersion


	
