#!/usr/bin/python3

from Rules import *
from FileReader import *
from Parser import *
from R import *
from Common import *
import sys


'''
RULE N°18 -- UPDATED

+ Prefer explicit intents
-> https://developer.android.com/training/articles/security-tips#use-intents

? Pseudo Code:
	1. Get intents used in 'bindService', 'startService' or 'sendOrderedBroadcast'
	2. Check if these intents are explicits

! Output
	-> NOTHING	: no implicit intent found in 'bindService', 'startService' or 'sendOrderedBroadcast'
	-> CRITICAL	: implicit intent found in 'bindService', 'startService' or 'sendOrderedBroadcast'
'''

class Rule18(Rules):
	def __init__(self, directory, database, verbose=True, verboseDeveloper=False, storeManager=None, flowdroid=False, platform="",validation=False, quiet=True):
		Rules.__init__(self, directory, database, verbose, verboseDeveloper, storeManager, flowdroid, platform, validation, quiet)

		self.AndroidErrMsg = "implicit intent(s) might execute an android component untrusted"
		self.AndroidOkMsg = "no implicit intent(s) might execute an android component untrusted"
		self.AndroidText = "https://developer.android.com/training/articles/security-tips#use-intents"

		self.errMsg = "Implicit intent might execute an android component untrusted"
		self.category = R.CAT_1
		
		self.filter('android.content.Intent')
		self.show(18, "Prefer explicit intents")



	def isExplicit(self, fileReader, intent):
		to_eval = intent[R.INSTR]
		intent_var_name = Parser.findVarName(to_eval, ['', None])[0]

		# check if the class is taken
		if ".class" in to_eval or "Class.forName(" in to_eval or "getClass(" in to_eval or "getPackageName(" in to_eval or "new ComponentName(" in to_eval or "getComponent(" in to_eval:
			return True
		
		# check if the class is setted after initialisating the intent
		else:
			settingClassMethods = Common.get_all_obj_names(fileReader, 'setComponentName')
			settingClassMethods += Common.get_all_obj_names(fileReader, 'setClassName')
			settingClassMethods += Common.get_all_obj_names(fileReader, 'setClass')
			settingClassMethods += Common.get_all_obj_names(fileReader, 'setComponent')

		_, funcs = Common.get_classes_and_funcs(fileReader)
		for func in funcs: 
			current_func = intent['funcName']
			if current_func in func[R.INSTR]:
				args = []
				pattern = r',\s*Class(?:<\w*>)?\s+(\w+)\s*(?=[,)])'		
				args = re.findall(pattern, func[R.INSTR])
				if Common.match_any_in_list(to_eval, args):
					return True

		for func in settingClassMethods:
			if intent_var_name in func[R.INSTR]:
				return True
		
		return False

	def run(self):
		self.loading()
		fctList = ['bindService', 'startService', 'sendOrderedBroadcast']
		for f in self.javaFiles:

			if ((self.packageDir != None) and (self.packageDir in f)) or ("AndroidManifest.xml" in f):

				fileReader = FileReader(f)

				intents = Common.get_all_var_names(fileReader, ['Intent '])
				intentsInstantiation = Common.get_all_var_names(fileReader, ['Intent', 'new'])
				fctCallingIntent = Common.get_all_arg_names(fileReader, 'bindService', 0)
				fctCallingIntent += Common.get_all_arg_names(fileReader, 'startService', 0)
				fctCallingIntent += Common.get_all_arg_names(fileReader, 'startActivity', 0)
				fctCallingIntent += Common.get_all_arg_names(fileReader, 'sendOrderedBroadcast', 0)

				# 'InMethod' will contain all intents used by 'bindService', 'startService’, 'sendOrderedBroadcast' or 'startActivity'
				InMethod, _ = Common.compare(intentsInstantiation, fctCallingIntent, with1=True, scope_with1=intents)
				
				# Check if intents are explicit or implicit
				NotIn = []
				In = [] 
				for e in InMethod:
					explicit = self.isExplicit(fileReader, e)
					if not explicit:
						NotIn.append(e)
					else:
						In.append(e)

				# Case where intent is instantiated in an argument position
				NotIn2 = []
				for e in fctCallingIntent:
					for fct in fctList:
						if fct in e['instr']:
							if ("new" and "Intent") in e['instr']:
								explicit = self.isExplicit(fileReader, e)
								if not explicit:
									NotIn2.append(e)
								else:
									In.append(e)
							break

				NotIn = NotIn + NotIn2

				# Set log msg
				NotIn 	= Parser.setMsg(NotIn, R.CRITICAL, self.errMsg)
				In = Parser.setMsg(In, R.OK, self.AndroidOkMsg)

				self.updateOCN(f, In, NotIn, (len(In) == 0 and len(NotIn) == 0))
				self.loading()
				fileReader.close()

		self.store(18, self.AndroidOkMsg, self.AndroidErrMsg, self.AndroidText, self.category, False, [self.errMsg])
		self.display(FileReader)

