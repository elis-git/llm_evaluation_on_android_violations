#!/usr/bin/python3

import os, re
from FileReader import *
from XmlReader import *
from R import *


class Parser():

	@staticmethod
	def setMsg(tokens, kind, msg=None):
		for t in tokens:
			t[R.ERRORTYPE] = kind
			t[R.ERRORMSG] = msg
		return tokens


	'''
	@param   : functions=[[function name, (*args)], ...]
	@returns : a list of dict element which match with conditions given in function arguments
	'''
	@staticmethod
	def finder(fileReader, functions=None, flag=False):
		output = []
		for i in range(0, len(functions)):
			output.append([])
		line, tok = fileReader.getNextInstruction()
		while line != '':
			line = ' '.join(line.split()).strip()
			if ('{' in line) or ('super.' in line): # avoid line which is function declaration
				pass
			elif (fileReader.isInterface() or (not fileReader.wasInstr() and flag == False)): 	# avoid 'interfaces' and functions / classes
				pass
			elif functions != None:
				p = 0
				for f in functions:
					out, outType = f[0](line, f[1])		# f[0] = fileReader, f[1] = tuple('method_name', arg, None)
					if out != None:
						tok = fileReader.constructToken(line)
						tok[R.VALUE] = out
						tok[R.TYPE]  = outType
						tok[R.EXTRA] = f[1]
						output[p].append(tok)
					p += 1
			line, tok = fileReader.getNextInstruction()
		fileReader.resetCursor()
		return output


	@staticmethod
	def findVarName(line, args):
		out = None
		if (len(args) == 2 and args[1] == None):
			conditions = args[0]
			if (not line.startswith('return ')) and all(c in line for c in conditions):
				out = line.split("=")[0].strip()
				out = out.split(" ")[-1]
				if (out.endswith(';')):
					out = out.split(';')[0]

				# Avoid keywords which are in string
				if ('"' or "'") in line.split("=")[0].strip():
					out = None

				# Handle case where variable is like "this.object.MyVariable = myFunction()"
				if out != None and 'this.' in out:
					out = out.split('this.')[-1]
				if out != None and '.' in out:
					out = out.split('.')[-1]
		return out, R.VARNAME


	@staticmethod
	def findTypeVar(line, args):
		out = None
		if (len(args) == 2 and args[1] == None):
			conditions = args[0]
			
			# Handle case where a variable was created with 'new' directly
			# so its useless to find variable type, because the variable was captured with its indentiation ('new myClass(...)')
			for c in conditions:
				if 'new ' in c and all(c in line for c in conditions):
					out = c.split(' ')[-1].strip().split('(')[0].strip()
					break
			if out == None and all(c in line for c in conditions):
				line = line.split("=")[0].strip()
				out = line.split(" ")[0]
				index = 0
				while out in ['private', 'public', 'protected', 'final', 'static']:
					out = line.split(" ")[index+1]
					index += 1
		return out, R.TYPEVAR


	@staticmethod
	def findObjName(line, args):
		out = None
		if (len(args) == 2 and args[1] == None):
			func = args[0]
			if Parser.isString(line, func):
				line = ''
			if ("."+func+"(" in line) or ("."+func+" (" in line):
				line = line.split("."+func)[0].strip()
				out = line.split(' ')[-1].strip()

				# Handle case where variable is like "this.object.MyVariable.myMethod()"
				if 'this.' in out:
					out = out.split('this.')[-1]
				if '.' in out:
					out = out.split('.')[-1]
		# if out != None:
			# print(f'{out} \n')
		return out, R.OBJNAME
		

	@staticmethod
	def findArgName(line, args):
		out = None
		if (len(args) == 3 and args[2] == None):
			func = args[0] 			# method name
			pos = args[1] 			# argument position that we want
			if (func+'(' in line) or (func+' (' in line):
				if Parser.isString(line, func):
					line = ''

				if (func+'(' in line):
					line = line.split(func+'(')[1].strip()
				elif line != '':
					line = line.split(func+' (')[1].strip()
				
				if line != '':
					depth = 1
					start = 0
					index = 0
					res = []
					for c in line:
						if c == '(':
							depth += 1
						elif c == ')':
							depth -= 1
						
						if c == ')' and depth == 0:
							res.append(line[start:index].strip())
							break
						if c == ',' and depth == 1:
							res.append(line[start:index].strip())
							start = index+1

						index += 1

					line = res
					if len(line) > pos:
						out = line[pos].strip()

		return out, R.ARGNAME


	@staticmethod
	def findArgsName(line, args):
		out = None
		if (len(args) == 3 and args[2] == None):
			func = args[0] 		# method name
			pos = args[1] 		# list that indicates argument positions that we want
			if (func+'(' in line) or (func+' (' in line):
				if Parser.isString(line, func):
					line = ''

				if (func+'(' in line):
					line = line.split(func+'(')[1].strip()
				elif line != '':
					line = line.split(func+' (')[1].strip()
				
				if line != '':
					depth = 1
					start = 0
					index = 0
					res = []
					for c in line:
						if c == '(':
							depth += 1
						elif c == ')':
							depth -= 1
						
						if c == ')' and depth == 0:
							res.append(line[start:index].strip())
							break
						if c == ',' and depth == 1:
							res.append(line[start:index].strip())
							start = index+1

						index += 1

					line = res
					if len(line) == len(pos):
						out = line

		return out, R.ARGNAME


	@staticmethod
	def findLine(line, args):
		out = None
		if (len(args) <= 3):
			listConditions = args[0]

			# allow or not to search data between quotes
			withString = False
			if len(args) == 3:
				withString = args[1]
			
			for conditions in listConditions:
				if all(elem in line for elem in conditions):

					add = True					
					if withString == False:
						for elem in conditions:
							if (Parser.isString(line, elem)):
								add = False
								break
					if add:	
						out = line
						break
		return out, R.INSTR
	
	



	####################################################################################################
	#                                              SCOPES                                              #
	####################################################################################################

	@staticmethod
	def getVarScope(variable):
		if variable[R.CLASSID] > 0 and variable[R.FUNCID] == 0:
			return R.VARCLASS
		elif variable[R.CLASSID] == 0 and variable[R.FUNCID] == 0:
			return R.VARGLOBAL
		else:
			return R.VARLOCAL


	@staticmethod
	def setScopes(variables):
		for var in variables:
			var[R.SCOPE] = Parser.getVarScope(var)
		return variables


	@staticmethod
	def setScopesWith(variables, vdeclared):
		for var in variables:
			for d in vdeclared:
				if var[R.VALUE] == d[R.VALUE]:
					if d[R.SCOPE] == R.VARGLOBAL:
						var[R.SCOPE] = R.VARGLOBAL
					elif d[R.SCOPE] == R.VARCLASS and d[R.CLASSID] == var[R.CLASSID]:
						var[R.SCOPE] = R.VARCLASS
					elif d[R.SCOPE] == R.VARLOCAL and d[R.CLASSID] == var[R.CLASSID] and d[R.FUNCID] == var[R.FUNCID]:
						var[R.SCOPE] = R.VARLOCAL
		return variables


	@staticmethod
	def scopeReachable(referenced, compared):
		In = []
		NotIn = []
		for r in referenced:
			isIn = False
			for c in compared:
				if ((r[R.SCOPE] == R.VARGLOBAL) or
					(r[R.SCOPE] == R.VARCLASS and r[R.CLASSID] == c[R.CLASSID]) or
					(r[R.SCOPE] == R.VARLOCAL and r[R.CLASSID] == c[R.CLASSID] and r[R.FUNCID] == c[R.FUNCID])):
					isIn = True
					break
			if isIn:
				In.append(r)
			else:
				NotIn.append(r)
		return In, NotIn


	@staticmethod
	def diff(reference, comparison, reverse=False):
		In 		= []
		NotIn 	= []

		# BE CAREFUL ! reference must have 'SCOPE' field initialized.
		#if len(reference) > 0 and reference[0][R.SCOPE] == None:
		#	print("[DEBUG] Parser.diff -> references scope not initialized !")

		# a reference can be used without a comparison
		if reverse:
			for c in comparison:
				isIn = False
				for r in reference:
					if r[R.VALUE] == c[R.VALUE] and r[R.SCOPE] != None:
						if r[R.SCOPE] == R.VARGLOBAL:
							isIn = True
							c[R.SCOPE] = R.VARGLOBAL
							break
						elif r[R.SCOPE] == R.VARCLASS and r[R.CLASSID] == c[R.CLASSID]:
							isIn = True
							c[R.SCOPE] = R.VARCLASS
							break
						elif r[R.SCOPE] == R.VARLOCAL and r[R.CLASSID] == c[R.CLASSID] and r[R.FUNCID] == c[R.FUNCID]:
							isIn = True
							c[R.SCOPE] = R.VARLOCAL
							break
				if isIn:
					In.append(c)
				else:
					NotIn.append(c)
		# a reference can't be used without a comparison
		#What is this second branch of if-else for? Please, explain
		else:
			for r in reference:
				isIn = False
				for c in comparison:
					if r[R.VALUE] == c[R.VALUE] and r[R.SCOPE] != None:
						if r[R.SCOPE] == R.VARGLOBAL:
							isIn = True
							break
						elif r[R.SCOPE] == R.VARCLASS and r[R.CLASSID] == c[R.CLASSID]:
							isIn = True
							break
						elif r[R.SCOPE] == R.VARLOCAL and r[R.CLASSID] == c[R.CLASSID] and r[R.FUNCID] == c[R.FUNCID]:
							isIn = True
							break
				if isIn:
					In.append(r)
				else:
					NotIn.append(r)
		return In, NotIn


	# It returns all class and function definitions
	# no 'value' set: consider just 'instr', 'classId', 'funcId', 'type'
	@staticmethod
	def getClassNFunc(fileReader): 
		listClss = []
		listFunc = []
		blackList = ["for", "while", "if", "else", "switch", "case", "default", "try", "catch", "finally"]
		line, tok = fileReader.getNextInstruction()
		while line != '':
			line = ' '.join(line.split()).strip()
			function = re.match("(public|private|static|protected|abstract|native|synchronized)+ ?([a-zA-Z0-9<>._?, ]*) ?([a-zA-Z0-9_]+) *\\([a-zA-Z0-9<>\\[\\]._?, \n]*\\)", line)
			clss = re.match("(public|private|static|protected|abstract|native|synchronized) [a-zA-Z0-9<>._?, ]* ?(class|interface)", line)
			if clss != None:
				tok = fileReader.constructToken(line)
				tok[R.TYPE]  = R.CLASS
				listClss.append(tok)
			elif function != None:
				avoid = False
				for e in blackList:
					if line.startswith(e):
						avoid = True
						break
				if not avoid:
					tok = fileReader.constructToken(line)
					tok[R.TYPE]  = R.FUNC
					listFunc.append(tok)
			line, tok = fileReader.getNextInstruction()
		
		fileReader.resetCursor()
		return listClss, listFunc
	


	@staticmethod
	def getAllPath(rootDirectory, fileExtension):
		res = []
		for root, _, files in os.walk(rootDirectory):
			for file in files:
				if file.endswith(fileExtension):
					res.append(os.path.join(root, file))
		return res


	@staticmethod
	def initStatFiles():
		nbFiles = {}
		nbFiles[R.CRITICAL]	= 0
		nbFiles[R.NA] 		= 0
		nbFiles[R.OK] 		= 0
		nbFiles[R.WARNING] 	= 0
		nbFiles[R.NOTHING] 	= 0
		return nbFiles


	@staticmethod
	def isString(line, elem):
		line = line.split('"')
		for i in range(0, len(line)):
			if elem in line[i]:
				if i%2 != 0:
					return True
		return False


	# additional
	@staticmethod
	def get_function_block(file_reader, function_name):

		"""
		This function retrieves the body of a function.

		Parameters:
			- file_reader : file in which the function is (already parsed by a FileReader)
			- function_name : name of the function of which to extract the body
		"""

		# get the list of all the functions in the file
		_, list_func = Parser.getClassNFunc(file_reader)

		# get the function names
		func_names = []
		func_path = []
		class_name = list_func[0]['clssName']
		for elem in list_func: 
			func_names.append(elem[R.INSTR])
			func_path.append(elem[R.PATH])

		# find index current func
		index_current_func = -1
		for index, func in enumerate(func_names):
			if function_name in func:
				index_current_func = index
				break

		index_next_func = -1
		current_func_path = func_path[index_current_func].split(class_name)[-1]
		for i in range(index_current_func+1, len(func_path)):
			next_func_path = func_path[i].split(class_name)[-1]
			if not current_func_path in next_func_path:
				index_next_func = i
				break

		func_line_number = file_reader.getLineNumber(func_names[index_current_func])
		next_func_line_number = file_reader.getLineNumber(func_names[index_next_func])
		block = file_reader.getBlock(func_line_number, next_func_line_number)
		pattern = re.compile(r'(.*\})', re.DOTALL)
		matches = pattern.findall(block)
		if matches:
			block = matches[-1]
		else:
			block = ""
		return block
	
	
	# additional
	@staticmethod
	def get_function_block_from_line(file_reader: FileReader, code: str, line_number=-1):

		"""
		This function retrieve a code block where a line falls in.

		Parameters:
			- fileReader : file in which the function is (already parsed by a FileReader) 
			- line : find the function starting from this line, then extract the body
			- lineNumber : the number of the line (may be None)

		Returns:
			- function body where the target line is included
		"""

		def get_last_line(file_reader):

			line_number = 0
			with open(file_reader.filename, 'r') as file:
				for line_number, _ in enumerate(file, 1):
					pass

			return line_number
			

		if line_number == -1:
			line_number = file_reader.getLineNumber(code)

		# get list of all the functions in the file
		_, list_func = Parser.getClassNFunc(file_reader)

		func_names = []
		func_path = []
		class_name = list_func[0]['clssName']
		for elem in list_func: 
			func_names.append(elem[R.INSTR])
			func_path.append(elem[R.PATH])

		index_current_func = -1 # current function: the function containing the line
		for index, func in enumerate(func_names):
			func_line_number = file_reader.getLineNumber(func)
			if func_line_number > line_number:
				index_current_func = index-1 # previous one
				break
		
		index_next_func = -1
		current_func_path = func_path[index_current_func].split(class_name)[-1]
		for i in range(index_current_func+1, len(func_path)):
			next_func_path = func_path[i].split(class_name)[-1]
			if not current_func_path in next_func_path:
				index_next_func = i
				break

		func_line_number = file_reader.getLineNumber(func_names[index_current_func])
		if index_next_func == -1:
			next_func_line_number = get_last_line(file_reader)
		else:
			next_func_line_number = file_reader.getLineNumber(func_names[index_next_func])
		block = file_reader.getBlock(func_line_number, next_func_line_number)
		pattern = re.compile(r'(.*\})', re.DOTALL)
		matches = pattern.findall(block)
		if matches:
			block = matches[-1]
		else:
			block = ""
		block = Parser.parseBlock(block)
		return block
	
	
	# additional
	@staticmethod
	def parseBlock(block):
		
		result = ""
		if block != "":
			lines = block.splitlines()
			result = ""
			for index, line in enumerate(lines[:-1]):
				line = line.replace('\t', '  ')
				next_line = lines[index+1]
				if next_line.rstrip().startswith("{"):
					result += line + " {\n"
				elif line.rstrip().startswith("{"):
					result += ""
				elif line.rstrip().endswith(";") or line.rstrip().endswith("}"):
					result += f"{line}\n"
				else:
					result += line 

			line = lines[-1].rstrip()
			if line.startswith("{"):
				result += line + " {"
			elif line.startswith(" {"):
				result += ""
			
			result = '\n'.join(line for line in result.split('\n') if line.strip())
		
		return result


	# additional		
	@staticmethod
	def extract_from_manifest(filename: str, code: str, rule=None):

		"""
		This function extracts context from the manifest starting from a line.

		Parameters:
			- filename : file in which the function is (already parsed by a FileReader) 
			- line : find the context of this line
			- rule : rule the line violates (may be None)

		Returns:
			- context surrounding the line (complete component definition)
		"""

		if rule == 3 or rule == 10:
			return code

		if ">" in code:
			code = code.replace(">", "")
		tag = ""
		
		# get tag by rule
		if "<service" not in code and "<receiver" not in code:
			if rule == 20: 
				tag = "service"
			elif rule == 23:
				tag = "receiver"
			else:
				return code
			
		# get tag by line
		elif "<service" in code:
			tag = "service"
		elif "<receiver" in code:
			tag = "receiver"
		else:
			return code
		
		xml_reader = XmlReader(filename)
		blocks = xml_reader.getArgsTag(tag)
		block = ""
		for elem in blocks:
			if code in elem['instr']:
				block = elem['instr']
		
		attributes = block.split("android:")
		attributes[-1] = attributes[-1] + ">"
		block = "\nandroid:".join(attributes)
		block += "\n</" + tag + ">"

		# print(block)
		return block

