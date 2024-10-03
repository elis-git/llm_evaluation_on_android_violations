#!/usr/bin/python3

from Rules import *
from FileReader import *
from Parser import *
from R import *
from Common import *
import sys, re


'''
RULE N°17 -- UPDATED

+ Avoid SQL injection
-> https://developer.android.com/training/articles/security-tips#ContentProviders

? Pseudo Code:
	1. Look for classes which extend ‘ContentProvider’
	2. Check method names (whitelist: query, update, delete)

! Output
	-> NOTHING	: no class which extends 'ContentProvider' found
	-> OK 		: class which extends 'ContentProvider' use only whitelisted methods
	-> CRITICAL	: class which extends 'ContentProvider' doesn't use only whitelisted methods

'''

class Rule17(Rules):
	def __init__(self, directory, database, verbose=True, verboseDeveloper=False, storeManager=None, flowdroid=False, platform="",validation=False, quiet=True):
		Rules.__init__(self, directory, database, verbose, verboseDeveloper, storeManager, flowdroid, platform, validation, quiet)

		self.AndroidErrMsg = "content provider(s) might be subject to SQL injection"
		self.AndroidOkMsg = "content provider(s) (are) not subject to SQL injection"
		self.AndroidText = "https://developer.android.com/training/articles/security-tips#ContentProviders"

		self.okMsg = "Content provider use only whitelisted methods"
		self.errMsg = "Content provider doesn't use only whitelisted methods (query, update and delete)"
		self.errMsg2 = "Selection may be concatenated with user data"

		self.category = R.CAT_2
		
		self.filter('android.content.ContentProvider')
		self.show(17, "Avoid SQL injection")

	def checkSelection(self, fileReader, block):
		NotIn = []
		pattern = re.compile(r'".+?"\s*\+\s*.+?,\s*.+?\)', re.DOTALL)
		matches = pattern.findall(block)
		for match in matches:
			lineNum = fileReader.getLineNumber(match.strip())
			lineContent = fileReader.getLineContent(lineNum, True)
			if any(keyword in lineContent[R.INSTR] for keyword in ["query", "update", "delete"]):
				NotIn.append(lineContent)
		return NotIn


	def run(self):
		self.loading()

		for f in self.javaFiles:
			fileReader = FileReader(f)

			listClss, listFunc = Common.get_classes_and_funcs(fileReader)
			extendsContentProvider = Common.get_extends_class(listClss, 'ContentProvider')
			
			In = []
			NotIn = [] # not inherited methods
			NotIn2 = [] # found selection concatenated with user data
			blackListForSelection = ['selection']
			# checks for not inherited functions
			for extends in extendsContentProvider:
				isOk = True
				for func in listFunc:
					if func[R.CLASSID] == extends[R.CLASSID]:
						isInherited = Common.isFuncInherited(fileReader, func[R.INSTR])
						if not isInherited:
							NotIn.append(func)
							block = Parser.get_function_block(fileReader, func[R.INSTR])
							if block != "":
								NotIn2 += self.checkSelection(fileReader, block)
						else:
							if Common.match_any_in_list(func[R.INSTR], blackListForSelection):
								block = Parser.get_function_block(fileReader, func[R.INSTR])
								if block != "":	# the function has been overridden
									# check if selection is concatenated
									NotIn2 += self.checkSelection(fileReader, block)
									isOk = False
					if isOk:
						In.append(extends)

			# Set log msg
			In 		= Parser.setMsg(In, R.OK)
			NotIn 	= Parser.setMsg(NotIn, R.WARNING, self.errMsg)
			NotIn2  = Parser.setMsg(NotIn2, R.CRITICAL, self.errMsg2)

			self.updateOWN(f, In, NotIn, (len(In) == 0 and len(NotIn) == 0))
			self.updateCN(f, NotIn2)
			self.loading()
			fileReader.close()

		self.store(17, self.AndroidOkMsg, self.AndroidErrMsg, self.AndroidText, self.category)
		self.display(FileReader)