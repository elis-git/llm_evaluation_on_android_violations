import pandas as pd
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


from repair.prompting_llms.scripts import prompting

from repair.metrics.scripts.run_metrics import MetricsEvaluator


if __name__ == "__main__":

    prompting.start_prompting_apis()

    ## be sure to save gemini-in-android outputs in a csv file 
    ## structure:
    ## dict: {
    ##      'gemini_in_android': list of android outputs
    ## }
    gemini_in_android_results_csv = "repair/prompting_llms/android_outputs.csv"   
    prompting.add_gemini_in_android_results(gemini_in_android_results_csv)     

    llms_outputs = "repair/prompting_llms/results/llms_outputs.csv"

    metrics_evaluator = MetricsEvaluator(llms_outputs)
    metrics_evaluator.run()
