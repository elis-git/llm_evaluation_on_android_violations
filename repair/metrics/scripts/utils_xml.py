import re, os
import pandas as pd
import xml.etree.ElementTree as ET
from nltk.tokenize import word_tokenize
from pathlib import Path


def delete_tmp_file(filename):

    """
    Utility function to delete temporary files.

    Parameters:
        - filename : complete name of the file to delete

    Returns:
        - it deletes the file
    """

    filepath = Path(filename)

    if filepath.exists():
        filepath.unlink()


def format_line(line):

    """
    Utility function to remove double whitespaces and replace them with a single one.

    Parameters:
        - line : the line to check and format

    Returns:
        - formatted line
    """

    line = line.strip()
    return re.sub(r'\s+', ' ', line)


def remove_line_number(line):
    
    """
    Utility function to remove heading line numbers (if present).

    Parameters:
        - line : the line to check and format

    Returns:
        - formatted line
    """

    if re.match(r"^\d+:\s*", line):
        return re.sub(r"^\d+:\s*", "", line)
    else:
        return line
    

def remove_xml_comment(line):

    """
    Utility function to remove xml comments, 
    except <!--uses-permission--> since it is part of a repair and has to be included.

    Parameters:
        - line : the line to check and format

    Returns:
        - formatted line
    """

    xml_comment_pattern = r"<!--\s*(.*?)\s*-->"
    xml_comment_to_keep = r"<!--\s*<uses-permission(.*?)-->"

    line = line.strip()
    if re.match(xml_comment_to_keep, line):
        return line
    elif "<!--" in line:
        return re.sub(xml_comment_pattern, "", line)
    else:
        return line
    

def remove_special_char(repair_tokens):

    """
    Utility function to remove special characters and prepare the repair for post-processing type 1.

    Parameters:
        - repair : repair to clean

    Returns:
        - repair cleaned and tokenized
    """

    cleaned_list = [''.join(char for char in item if char.isalnum() or char.isspace() or char == '.' or char == "_") for item in repair_tokens]
    cleaned_repair = []
    for elem in cleaned_list:
        if elem != "":
            cleaned_repair.append(elem)
    return cleaned_repair
    

def clean_repair(repair):

    """
    This function cleans the repair from comments, additional line numbers and bad spacing.

    Parameters:
        - repair : repair to clean

    Returns:
        - repair cleaned and formatted on a single line
    """

    lines = repair.split("\n")
    cleaned_repair = []

    for line in lines:
        clean_line = remove_line_number(line)
        
        clean_line = remove_xml_comment(clean_line)

        clean_line = format_line(clean_line)

        # if the line has content
        if clean_line != "" and clean_line != " ":
            cleaned_repair.append(clean_line)
    
    return " ".join(cleaned_repair)


def extract_xml_attributes(repair):

    """
    This function parses the repair and extracts its attributes and structures.

    Parameters:
        - repair : repair to parse

    Returns:
        - a dictionary containing all the attributes and their values (empty if the repair has no relevant elements) 
    """

    try:
        with open("tmp_xml.xml", "w") as file:
            file.write(repair)

        tree = ET.parse('tmp_xml.xml')
        root = tree.getroot()
        data = {}
    
        for elem in root:

            # manage service or receiver component
            if elem.tag == 'service' or elem.tag == 'receiver':
                for key in elem.attrib: # iterate list of attributes for the tag
                    if 'tools' in key:
                        attribute = key.split('tools}')[-1]
                        data[f'{elem.tag}.tools.{attribute}'] = elem.attrib[key]
                    else:
                        attribute = key.split('android}')[-1]
                        if attribute == 'permission':
                            data[f'{elem.tag}.{attribute}'] = 'custom_permission' # abstract permission name
                        else:
                            data[f'{elem.tag}.{attribute}'] = elem.attrib[key] # take the value as it is
               
                for subelem in elem:
                    if subelem.tag == 'intent-filter': # manage intent-filter
                        for child_elem in subelem:
                            tag_name = child_elem.tag
                            for attr_key, attr_value in child_elem.attrib.items():
                                attribute = attr_key.split('android}')[-1]
                                data[f'{elem.tag}.intent-filter.{tag_name}.{attribute}'] = attr_value
                    for key in subelem.attrib:  # manage other subelements
                        attribute = key.split('android}')[-1]
                        data[f'{elem.tag}.{subelem.tag}.{attribute}'] = subelem.attrib[key]

            # manage permission tag
            if elem.tag == 'permission':
                for key in elem.attrib: # iterate list of attributes for the tag
                    attribute = key.split('android}')[-1]
                    if attribute == 'name':
                        data[f'{elem.tag}.{attribute}'] = 'custom_permission' # abstract permission name
                    else:
                        data[f'{elem.tag}.{attribute}'] = elem.attrib[key]

        delete_tmp_file("tmp_xml.xml")
        return data
    
    except ET.ParseError as e:
        print(e)
        delete_tmp_file("tmp_xml.xml")
        return {}
    

def to_string(dictionary):

    """
    Utility function to write as a string elements of the dictionary.

    Parameters:
        - dictionary : a dictionary of attributes and their values

    Returns:
        - a single line containing each attribute and value of the dictionary in the form of: key value
    """

    result = []
    for key in dictionary:
        part = f'{key} {dictionary[key]}'
        result.append(part)
    return " ".join(result)


def compare_xml_attributes(ref_attributes, llm_attributes):

    """
    This function compares attributes of the repair proposed by LLM against ground truth ones.
    It includes in LLM final attributes only the ones actually needed for effective repair,
    any additional ones won't be included. 
    Metrics for comparing xml repairs are text similarity metrics, therefore any additional
    word will result in a smaller similarity score, even if all the needed attributes are 
    present, leading to a correct repair.

    Parameters:
        - ref_attributes : dictionary of ground truth repair attributes and their values
        - llm_attributes : dictionary of llm repair attributes and their values

    Returns:
        - new_llms_attributes : an updated dictionary containing only llm attributes relevant for 
                                the repair (if present)
    """

    new_llm_attributes = {}
    for attr in llm_attributes:
        if attr in ref_attributes:
            new_llm_attributes[attr] = llm_attributes[attr]

    return new_llm_attributes


def wrap_xml_element(repair):

    """
    Utility function to wrap the repair to give it the tree structure, needed for correct parsing.

    Parameters:
        - repair : the cleaned and formatted repair

    Returns:
        - the repair wrapped with necessary information for parsing
    """

    wrapped_repair = ""

    if 'manifest' in repair and ('<receiver' in repair or '<service' in repair or '<permission' in repair):
        pattern_permission = re.compile(r'<permission(.*?)(</permission>|\s*/>)', re.DOTALL)
        pattern_receiver = re.compile(r'<receiver(.*?)(</receiver>|\s*/>)', re.DOTALL)
        pattern_service = re.compile(r'<service(.*?)(</service>|\s*/>)', re.DOTALL)
        permissions = pattern_permission.findall(repair)
        receivers = pattern_receiver.findall(repair)
        services = pattern_service.findall(repair)
        part = ""
        if len(permissions) > 0:
            end_permission = '</permission>' if permissions[0][0].strip().endswith(">") else '/>'
            part += f'<permission{permissions[0][0]}{end_permission}'
        if len(receivers) > 0:
            end_receiver = '</receiver>' if receivers[0][0].strip().endswith(">") else '/>'
            part += f'<receiver{receivers[0][0]}{end_receiver} '
        if len(services) > 0:
            end_service = '</service>' if services[0][0].strip().endswith(">") else '/>'
            part += f'<service{services[0][0]}{end_service} '
        wrapped_repair = f'<root xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools">{part}</root>' 
        
    # specific for managing rule 3 repairs
    elif "<!--<uses-" in repair or "<!-- <uses-" in repair or "REMOVE_PERMISSION" in repair:
        wrapped_repair = f'<root xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools"></root>' 
    else:
        wrapped_repair = f'<root xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools">{repair.strip()}</root>' 
        if re.search(r'"{2,}', wrapped_repair):
            wrapped_repair = re.sub(r'"{2,}', '"', wrapped_repair)

    return wrapped_repair


def is_xml(repair):

    """
    Utility function to check whether the repair actually contains the xml correct snippet.

    Parameters:
        - repair : the repair as it is

    Returns:
        - True if it has the xml structure, False if not (natural language repair)
    """
    
    if not repair.strip().startswith("<"):
        return False
    return True


def prepare_xml_repair(repair):

    """
    This function prepares the repair for evaluation.
    It cleans the repair from comments and extracts its structure.

    Parameters:
        - repair : the repair to be processed and then evaluated

    Returns:
        - repair_attributes : a dictionary containing repair attributes and their values 
    """

    repair = clean_repair(repair)

    is_tree = is_xml(repair)

    if not is_tree:
        repair = "REMOVE_PERMISSION"
    
    repair = wrap_xml_element(repair)
    repair_attributes = extract_xml_attributes(repair)

    return repair_attributes


def post_proc_xml(ref_repair, llm_repair):

    """
    This function starts the processing for both ground truth and llm repairs.

    Parameters:
        - ref_repair : ground truth repair
        - llm_repair : llm proposed repair

    Returns:
        - ref_attributes_text : the attibutes and values of the ground truth repair as string
        - llm_attributes_text : the attibutes and values of the llm repair as string
    """

    ref_attributes = prepare_xml_repair(ref_repair)
    llm_attributes = prepare_xml_repair(llm_repair)
    
    ref_attributes_text = to_string(ref_attributes)
    llm_attributes_text = to_string(compare_xml_attributes(ref_attributes,llm_attributes))

    return ref_attributes_text, llm_attributes_text



def start_post_processing(ground_truths: list, llm_outputs: list):

    """
    This function starts the post-processing for the full list of ground truths and llm repairs.

    Parameters:
        - ground_truths 
        - llm_output

    Returns:
        - cleaned_ground_truths : list of post-processed ground truths
        - cleaned_llm_outputs : list of post-processed llm outputs
    """

    cleaned_ground_truths, cleaned_llm_outputs = [], []

    for i in range(len(ground_truths)):
        cleaned_ground_truth, cleaned_llm_output = post_proc_xml(ground_truths[i], llm_outputs[i])
        cleaned_ground_truths.append(cleaned_ground_truth)
        cleaned_llm_outputs.append(cleaned_llm_output)
        
        
    return cleaned_ground_truths, cleaned_llm_outputs

