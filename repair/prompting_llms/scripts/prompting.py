import pandas as pd
import os, sys

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

import repair.prompting_llms.scripts.helpers as helpers

from repair.prompting_llms.scripts.helpers import PromptManager, Requester, OutputManager


def start_prompting_apis():

    """
    This function starts prompting the LLMs.
    """

    pm = PromptManager()

    models = ['gpt-4o', 'gemini-1.5-flash-001']     ## gemini-in-android does not have API access

    for model in models:

        requester = Requester(model, pm)
        requester.get_responses()

        om = OutputManager(requester)
        om.save_outputs()


def add_gemini_in_android_results(android_csv: str):

    """
    This function reads gemini-in-android results from .csv file and saves them.
    """

    helpers.get_outputs_from_csv(android_csv)
    

        
