import re
import pandas as pd
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

def remove_java_comment_and_imports(line):
    
    """
    Utility function to remove java comments and imports.

    Parameters:
        - line : the line to check and format

    Returns:
        - formatted line
    """

    single_line_comment_pattern = r'(.+?)\s+//'
    multiple_line_comment_pattern = r'/\*(.*?)\*/'
    match_single = re.search(single_line_comment_pattern, line)
    match_multiple = re.search(multiple_line_comment_pattern, line)

    if line.strip().startswith("//") or line.strip().startswith("import"):
        return ""
    elif match_single:
        cleaned_line = match_single.group(1)
        return cleaned_line
    elif match_multiple:
        return re.sub(multiple_line_comment_pattern, ' ', line)
    else:
        return line
    

def is_java(repair):
    
    """
    Utility function to check whether the repair actually contains the java content.

    Parameters:
        - repair : the repair as it is

    Returns:
        - True if it java code, False if not (natural language repair)
    """

    special_chars = set("{}();")
    return any(char in special_chars for char in repair)


def clean_repair(repair):

    """
    This function prepares the repair for evaluation.
    It cleans the repair from comments and additional irrelevant content.

    Parameters:
        - repair : the repair to be processed and then evaluated

    Returns:
        - cleaned_repair : the cleaned repair formatted as single line
    """

    if not is_java(repair):
        return "NO_REPAIR"
    
    lines = repair.split("\n")
    cleaned_repair = []

    for line in lines:

        clean_line = remove_line_number(line)
        clean_line = remove_java_comment_and_imports(clean_line)
        clean_line = format_line(clean_line)

        if clean_line != "" and clean_line != " ":
            cleaned_repair.append(clean_line)
    
    return " ".join(cleaned_repair)


def post_proc_java(ground_truth, llm_output):

    """
    This function processes both ground truth and llm repairs.

    Parameters:
        - ground_truth : ground truth repair
        - llm_output : llm proposed repair

    Returns:
        - cleaned_ground_truth : the ground truth repair as string
        - cleaned_llm_output : the llm repair as string
    """

    cleaned_ground_truth = clean_repair(ground_truth)
    cleaned_llm_output = clean_repair(llm_output)

    return cleaned_ground_truth, cleaned_llm_output



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
        cleaned_ground_truth, cleaned_llm_output = post_proc_java(ground_truths[i], llm_outputs[i])
        cleaned_ground_truths.append(cleaned_ground_truth)
        cleaned_llm_outputs.append(cleaned_llm_output)
        
        
    return cleaned_ground_truths, cleaned_llm_outputs
