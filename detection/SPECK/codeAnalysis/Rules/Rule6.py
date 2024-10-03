#!/usr/bin/python3

from Rules import *
from FileReader import *
from Parser import *
from R import *
from Common import *
import sys


'''
RULE N°6 -- UPDATED

+ Use HTML message channels
** If your app must use JavaScript, use HTML message channels instead of evaluateJavascript(), ...
-> https://developer.android.com/topic/security/best-practices#webview

? Pseudo Code:
	1. Look for particular keywords which have security issues

! Output
	-> NOTHING	: no depreciated function found
	-> CRITICAL	: deprecated function found
'''

class Rule6(Rules):
	def __init__(self, directory, database, verbose=True, verboseDeveloper=False, storeManager=None, flowdroid=False, platform="",validation=False, quiet=True):
		Rules.__init__(self, directory, database, verbose, verboseDeveloper, storeManager, flowdroid, platform, validation, quiet)

		self.AndroidErrMsg = "deprecated function(s) (are) used"
		self.AndroidOkMsg = "no depreciated Javascript function is used"
		self.AndroidText = "https://developer.android.com/topic/security/best-practices#webview"

		# self.okMsg = "No javascript function deprecated is used"
		# self.errMsg = "evaluateJavascript(), addJavascriptInterface() or setJavaScriptEnabled() are used but deprecated"
		self.okMsg = "Javascript usage may be controlled"
		self.errMsg = "evaluateJavascript(), addJavascriptInterface() or setJavaScriptEnabled() are used but not controlled"
		
		self.category = R.CAT_2
		
		self.filter('android.webkit.WebView')
		self.show(6, "Use HTML message channels")

	def run(self):
		self.loading()
		for f in self.javaFiles:
			fileReader = FileReader(f)
			

			In = []
			NotIn = []

			# Look for critical functions
			found_1 = Common.search_keywords(fileReader, ['.evaluateJavascript'])
			found_2 = Common.search_keywords(fileReader, ['.addJavascriptInterface', 'addJavascriptInterface'])
			found_3 = Common.search_keywords(fileReader, ['.setJavaScriptEnabled(true)'])
		
			
			found = found_1 + found_2 + found_3
			for elem in found:
				if not elem[R.INIF]:
					NotIn.append(elem)
				else:
					In.append(elem)
			
			# Set log msg
			In = Parser.setMsg(In, R.OK, self.okMsg)
			NotIn = Parser.setMsg(NotIn, R.CRITICAL, self.errMsg)

			self.updateCN(f, NotIn)
			self.loading()
			fileReader.close()

		self.store(6, self.AndroidOkMsg, self.AndroidErrMsg, self.AndroidText, self.category, True)
		self.display(FileReader)
