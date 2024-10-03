import pandas as pd

APK_TO_SRC_MAPPING = "mapping_apk_to_src.csv"



def add_line_numbers(snippet):

    snippet_updated = ""
    lines = snippet.strip().split('\n')
    new_block = '\n'.join([f'{i + 1}: {line}' for i, line in enumerate(lines)])
    snippet_updated = new_block

    return snippet_updated


def get_vuln_line_number(snippet, vuln_line):

    lines = snippet.split('\n')
    for i, line in enumerate(lines):
        if vuln_line in line:
            return i + 1  # line numbers are 1-based
    return None


def get_src_directory(apk_name):

    df = pd.read_csv(APK_TO_SRC_MAPPING)

    apk = f"{apk_name}.apk"

    src_dir = ""

    result = df[df['apk_filename'] == apk]['src_code_folder_name']
    if not result.empty:
        src_dir = result.iloc[0]
    
    return src_dir


def is_compilable(apk_name):

    df = pd.read_csv(APK_TO_SRC_MAPPING)
    apk = f"{apk_name}.apk"

    compilable = ""

    result = df[df['apk_filename'] == apk]['compilable']
    if not result.empty:
        compilable = result.iloc[0]

    return compilable