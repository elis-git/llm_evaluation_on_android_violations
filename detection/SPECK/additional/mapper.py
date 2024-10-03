import os, sys, re
import pandas as pd
import difflib
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../codeAnalysis')))


import mapper_utils as utils


from Parser import *
from FileReader import *

class Mapper:

    def __init__(self, record: dict):

        self.record = record

        self.apk_to_src_mapping = " "   # csv containing a mapping between apk_name -> src_code_dir_name

        self.src_codes_dir = " "    # dirpath of directory containing all source code projects

        self.current_src_dir_rec = self.get_src_directory()

        self.current_dec_filename = ""

        self.record['language'] = self.set_language()
        self.record['compilable'] = self.is_compilable()

        self.record['src_codes'], self.record['src_paths'], self.record['src_code_line_numbers'] = "", "", ""
        self.record['src_code_context'] = ""

    
    def set_language(self):

        """
        This function returns the language of the current decompiled file to be mapped to the corresponding source code. 
        """

        filename = self.record['file'].split("/")[-1]
        filename = re.sub(r'\$[^.]+\.', '.', filename)

        self.current_dec_filename = filename

        language = ""

        if filename.endswith("Kt.java"):
            language = "kotlin"
        elif filename.endswith(".xml"):
            language = "xml"
        else:
            language = "tbd" # to-be-decided

        return language
    

    def is_compilable(self):

        """
        This function returns whether the APK from which the current decompiled file has been extracted, is compilable.
        """

        df = pd.read_csv(self.apk_to_src_mapping)
        apk = f"{self.record['apk']}.apk"

        compilable = ""

        result = df[df['apk_filename'] == apk]['compilable']
        if not result.empty:
            compilable = result.iloc[0]

        return compilable


    def get_src_directory(self):

        """
        This function returns the source project directory corresponding to the APK from which the current decompiled file has been extracted.
        """

        df = pd.read_csv(self.apk_to_src_mapping)

        apk = f"{self.record['apk']}.apk"

        result = df[df['apk_filename'] == apk]['src_code_folder_name']
        if not result.empty:
            return result.iloc[0]
        

    def get_src_filepaths(self):

        """
        This function returns a list of possible files (paths) from the source code directory that match 
        the current decompiled one, containing the faulty line.
        """

        decompiled_filename = self.current_dec_filename
        language = self.record['language'] 

        src_filepaths = []
        target_filename = ""

        if language == "kotlin":
            decompiled_filename = decompiled_filename.replace("Kt.java", ".kt")
        
        if language == "xml":
            src_filepaths = self.get_manifests()
            return src_filepaths
        
        target_filename = decompiled_filename.split(".")[0]

        search_dir = os.path.join(self.src_codes_dir, self.current_src_dir_rec)

        for root, _, files in os.walk(os.path.join(self.src_codes_dir, search_dir)):
            for file in files:
                filename = file.split(".")[0]
                
                if target_filename in filename:
                    src_filepath = os.path.join(root, file)
                    src_filepaths.append(src_filepath)
            
        return src_filepaths
    

    def get_manifests(self):

        """
        This function returns a list of possible Android Manifest files (if more than one is present in the source code directory) 
        that match the current decompiled one, containing the faulty line.        
        """

        search_dir = os.path.join(self.src_codes_dir, self.current_src_dir_rec)

        manifests = []

        for dirpath, _, filenames in os.walk(os.path.join(self.src_codes_dir, search_dir)):
            for filename in filenames:
                if filename.endswith('AndroidManifest.xml'):
                    manifests.append(os.path.join(dirpath, filename))

        return manifests


    def get_src_code_info(self):

        """
        This function returns all the needed information for the actual mapping: 
        - original faulty line (from source code directory, mapped to the one from the decompiled file)
        - filepath of the source file containing the faulty line
        - line number of the faulty line in the source file
        """
        
        src_code = ""
        src_code_best_match_ratio = 0
        src_code_line_number = -1
        src_filepath = ""

        target_code = self.record['code']

        src_filepaths = self.get_src_filepaths()

        if len(src_filepaths) > 0:
            
            encodings_to_try = ['utf-8', 'latin-1']

            for path in src_filepaths:
                for encoding in encodings_to_try:
                    try:
                        with open(path, mode='r', encoding=encoding) as src_file:
                            for line_number, line in enumerate(src_file, 1):
                                ratio = difflib.SequenceMatcher(None, target_code, line).ratio()
                                if ratio > src_code_best_match_ratio:
                                    src_code_best_match_ratio = ratio
                                    src_code = line.strip()
                                    src_code_line_number = line_number
                                    src_filepath = path
                        break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        traceback.print_exc()
                        src_code = "MAPPING_ERROR"
                        break

            if self.record['language'] == "tbd":
                if src_filepath != "":
                    if src_filepath.endswith(".java"):
                        self.record['language'] = "java"
                    else:
                        self.record['language'] = "kotlin"
                        src_code = "KOTLIN_CODE"
                        src_filepath = "KOTLIN_CODE"

        if src_code == "":
            src_code = "SRC_CODE_NOT_FOUND"
            src_filepath = "SRC_CODE_NOT_FOUND"

        self.record['src_codes'], self.record['src_paths'], self.record['src_code_line_numbers'] = src_code, src_filepath, src_code_line_number



    def get_context(self):

        """
        This function extractes the context (either Java function or XML full component description) starting from the faulty line,
        the original filepath and corresponding line number.
        """

        blacklist = ["SRC_CODE_NOT_FOUND", "MAPPING_ERROR", "KOTLIN_CODE"]

        src_codes = self.record['src_codes'] 

        if src_codes not in blacklist:

            complete_vuln = ""

            if self.record["language"] == "java":
                complete_vuln = self.__extract_java_method()
            elif self.record['language'] == "xml": 
                complete_vuln = self.__extract_xml_context()

            complete_vuln = utils.add_line_numbers(complete_vuln)

            self.record['src_code_context'] = complete_vuln

        else:
            self.record['src_code_line_numbers'] = -1
            self.record['src_code_context'] = "CONTEXT_NOT_FOUND"

        
    def __extract_java_method(self):

        """
        This function extracts the context (whole function) for Java-related faulty lines.
        """

        snippet = ""

        try: 
            src_code_line_number = int(self.record['src_code_line_numbers'])
            src_code = str(self.record['src_codes'])
            src_path = self.record['src_paths']

            if src_code_line_number != -1:
                fileReader = FileReader(src_path)
                block = Parser.get_function_block_from_line(fileReader, src_code, src_code_line_number)
                snippet = block                
            else:
                snippet = "SRC_CODE_NOT_FOUND"
                self.record['src_codes'] = snippet

        except Exception as e:
            snippet = "EXTRACTION_ERROR"
            self.record['src_codes'] = snippet

        return snippet


    def __extract_xml_context(self):

        """
        This function extracts the whole component defintiion from the Manifest file, starting from XML-related faulty lines.
        """

        snippet = ""
        
        try: 
            filename = str(self.record['src_paths'])
            code = str(self.record['src_codes'])
            rule = int(self.record['rule'])

            if filename != "SRC_CODE_NOT_FOUND": 
                path = filename
                block = Parser.extract_from_manifest(path, code, rule)
                snippet = block
            else:
                snippet = "SRC_CODE_NOT_FOUND"
                self.record['src_codes'] = snippet

        except Exception as e:
            snippet = "EXTRACTION_ERROR"
            self.record['src_codes'] = snippet

        return snippet
    

    def update(self):

        """
        This function updates SPECK detected faulty line record information adding the fields related to source code mapping.
        """

        if self.record['kind'] == "[INTERNAL]":

            self.get_src_code_info()
            self.get_context()

        else:
            self.record['src_codes'], self.record['src_paths'], self.record['src_code_line_numbers'] = "SRC_CODE_NOT_FOUND", "SRC_CODE_NOT_FOUND", "SRC_CODE_NOT_FOUND"
            self.record['src_code_context'] = "CONTEXT_NOT_FOUND"


    def get_updated_record(self):

        """
        This function returns the updated SPECK record to be added to the dataset.
        """

        self.update()

        return self.record
    

