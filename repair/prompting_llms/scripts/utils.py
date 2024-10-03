import os
import pandas as pd
import pickle
import json
import random

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def save_checkpoint(checkpoint_filename, list_responses, last_index):

    data = {
        'list_responses': list_responses,
        'last_index': last_index
    }
    
    with open(checkpoint_filename, 'wb') as f:
        pickle.dump(data, f)


def load_checkpoint(checkpoint_filename):

    try:
        with open(checkpoint_filename, 'rb') as f:
            data = pickle.load(f)
        return data['list_responses'], data['last_index']
    except FileNotFoundError:
        return [], -1
    

def read_from_json(filename):

    data = []

    try:
        with open(filename, 'r') as file:
            data = json.load(file)
    except Exception:
        return data

    return data


def extract_code_snippets(csv_path):

    df = pd.read_csv(csv_path)
    code_snippets = df['code_snippet'].tolist()

    cleaned_code_snippets = []
    for code in code_snippets:
        if pd.notna(code):
            cleaned_code_snippets.append(code)

    return cleaned_code_snippets


def get_guideline(rule: str):
   
    rules_description = "detection/SPECK_mod/SPECK/codeAnalysis/Rules/rules.json"
    try:
        with open(rules_description, 'r') as file:
            data = json.load(file)
    except Exception as e:
        print(e)
    
    for item in data:
        if item.get('rule_id') == rule:
            return item.get('short_description')
    
    return None


def find_line_number(snippet, target_line):
 
    lines = snippet.split('\n')
    
    vectorizer = TfidfVectorizer().fit_transform([target_line] + lines)
    
    cosine_similarities = cosine_similarity(vectorizer[0:1], vectorizer[1:]).flatten()
    
    most_similar_index = np.argmax(cosine_similarities)
    
    return int(most_similar_index + 1)


def get_prompt_info(vuln_line: str, snippet: str, rule: str):

    vuln_line_number = find_line_number(snippet, vuln_line)
    guideline = get_guideline(rule)

    return vuln_line_number, guideline


def get_prompt(record: dict, template: str):

    """
    This function prepare the prompt given the template and the needed information, available in @param record.
    """

    try: 
        vulnerable_snippet = record['vulnerable_snippet']
        vulnerable_line = record['vulnerable_line']
        violated_rule = str(int(record['rule']))

        vuln_line_number = str(find_line_number(vulnerable_snippet, vulnerable_line))
        guideline = get_guideline(violated_rule)

        prompt = ""

        prompt = template.replace("[CODE_SNIPPET]", vulnerable_snippet)
        prompt = prompt.replace("[GUIDELINE]", guideline)
        

        if vuln_line_number is not None:
            prompt = prompt.replace("[LINE_NUMBER]", vuln_line_number)
        else:
            prompt = prompt.replace("[LINE_NUMBER]", "ERROR_LINE_NUMBER")

    except:
        prompt = "UNKNOWN_ERROR"

    return prompt
