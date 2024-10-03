import pandas as pd
import sys, os, subprocess, re


from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import repair.metrics.scripts.utils_xml as utils_xml
import repair.metrics.scripts.utils_java as utils_java



class CodeBLEUHelper:

    def __init__(self, model: str, data: pd.DataFrame, params="0.25,0.25,0.25,0.25"):

        self.model = model
        self.data = data
        self.params = params

        self.ground_truths = []
        self.llm_outputs = []

        self.ngram_match_results = []
        self.weighted_ngram_results = []
        self.syntax_match_results = []
        self.dataflow_match_results = []

        if not os.path.isdir(f"repair/metrics/results_java/"):
            os.mkdir(f"repair/metrics/results_java/")

        self.results_csv = f"repair/metrics/results_java/scores_java_{self.model}.csv"


    
    def _compute_submetrics(self):

        """
        This function runs codeBLEU module to compute similarity scores for each pair of ground truth-llm repair.
        """

        for index in range(len(self.ground_truths)):

            ground_truth = str(self.ground_truths[index])
            llm_output = str(self.llm_outputs[index])

            ref_file = os.path.join('repair/metrics/.tmp', "tmp_ref.txt")
            hyp_file = os.path.join('repair/metrics/.tmp', "tmp_hyp.txt")

            with open(ref_file, "w", encoding='utf-8') as file:
                file.write(ground_truth)
            with open(hyp_file, "w", encoding='utf-8') as file:
                file.write(llm_output)

            command = [
                'python', 'repair/metrics/CodeBLEU/calc_code_bleu.py',  
                '--refs', ref_file,
                '--hyp', hyp_file,
                '--lang', 'java',
                '--params', self.params
            ]

            try:
                result = subprocess.run(command, capture_output=True, text=True)
                output = result.stdout

                ngram_match = re.search(r'ngram match: ([\d\.]+)', output)
                weighted_ngram_match = re.search(r'weighted ngram match: ([\d\.]+)', output)
                syntax_match = re.search(r'syntax_match: ([\d\.]+)', output)
                dataflow_match = re.search(r'dataflow_match: ([\d\.]+)', output)

                if ngram_match:
                    ngram_match_value = float(ngram_match.group(1))

                if weighted_ngram_match:
                    weighted_ngram_match_value = float(weighted_ngram_match.group(1))

                if syntax_match:
                    syntax_match_value = float(syntax_match.group(1))

                if dataflow_match:
                    dataflow_match_value = float(dataflow_match.group(1))

                self.ngram_match_results.append(ngram_match_value)
                self.weighted_ngram_results.append(weighted_ngram_match_value)
                self.syntax_match_results.append(syntax_match_value)
                self.dataflow_match_results.append(dataflow_match_value)

            except Exception as e:
                print(f'Failure for index {index}. EXCEPTION: {e}')
                self.ngram_match_results.append(-1)
                self.weighted_ngram_results.append(-1)
                self.syntax_match_results.append(-1)
                self.dataflow_match_results.append(-1)

        self._compute_codebleus()


    def _compute_codebleus(self):

        """
        This function computes codeBLEU values.
        """

        alpha,beta,gamma,theta = [float(x) for x in self.params.split(',')]       
        codebleu_results = []

        for i in range(len(self.ngram_match_results)):

            code_bleu_score = alpha*self.ngram_match_results[i]\
                        + beta*self.weighted_ngram_results[i]\
                        + gamma*self.syntax_match_results[i]\
                        + theta*self.dataflow_match_results[i]
            
            codebleu_results.append(code_bleu_score)

        return codebleu_results


    def start(self):

        """
        This function starts the post-processing for each pair of ground truth-llm_output, then it computes CodeBLEU scores.
        At the end, a new .csv file is created with the results.
        """

        ## post-processing snippets before computing codebleu
        self.ground_truths, self.llm_outputs = utils_java.start_post_processing(
            self.data['ground_truths'].tolist(), self.data[self.model].tolist())
        
        if not os.path.isfile(self.results_csv):

            self._compute_submetrics()

            result_df = pd.DataFrame({
                'id_': self.data['_id'].tolist(),
                'rule': self.data['rule'].tolist(),
                'ground_truths': self.ground_truths,
                f'{self.model}_outputs': self.llm_outputs,
                'ngram_match': self.ngram_match_results,
                'weighted_ngram': self.weighted_ngram_results,
                'syntax_match': self.syntax_match_results,
                'dataflow_match': self.dataflow_match_results
            })
            result_df.to_csv(self.results_csv, index=False)

        else: ## load submetrics to compute codebleu

            result_df = pd.read_csv(self.results_csv)

            self.ngram_match_results = result_df['ngram_match']
            self.weighted_ngram_results = result_df['weighted_ngram']
            self.syntax_match_results = result_df['syntax_match']
            self.dataflow_match_results = result_df['dataflow_match']

        codebleus = self._compute_codebleus()
        result_df = pd.read_csv(self.results_csv)
        result_df[f'codebleu_{self.params}'] = codebleus

        result_df.to_csv(self.results_csv, index=False)

        print(f'CodeBLEU with parameters {self.params} for Java-related violations has been computed.')



class XMLHelper:

    def __init__(self, model: str, data: pd.DataFrame):

        self.model = model
        self.data = data

        self.ground_truths = []
        self.llm_outputs = []

        if not os.path.isdir(f"repair/metrics/results_xml/"):
            os.mkdir(f"repair/metrics/results_xml/")

        self.results_csv = f"repair/metrics/results_xml/scores_xml_{self.model}.csv"


    def _compute_similarity(self):

        """
        This function computes similarity between post-processed ground truth and llm output, accordingly with 
        three metrics: jaccard similarity, levensthein distance, cosine similarity.
        """

        jaccard, lev, cosine = [], [], []

        for i in range(len(self.ground_truths)):
            
            jaccard_score = _calculate_jaccard_similarity(self.ground_truths[i], self.llm_outputs[i])
            lev_score = _calculate_lev_distance(self.ground_truths[i], self.llm_outputs[i])
            cosine_score = _calculate_cosine_similarity(self.ground_truths[i], self.llm_outputs[i])

            jaccard.append(jaccard_score)
            lev.append(lev_score)
            cosine.append(cosine_score)

        return jaccard, lev, cosine



    def start(self):

        """
        This function starts the post-processing for each pair of ground truth-llm_output, then it computes scores for 
        XML-related similarity metrics.
        At the end, a new .csv file is created with the results.
        """

        self.ground_truths, self.llm_outputs = utils_xml.start_post_processing(
            self.data['ground_truths'].tolist(), self.data[self.model].tolist())
        

        jaccard, lev, cosine = self._compute_similarity()

        result_df = pd.DataFrame({
            'id_': self.data['_id'].tolist(),
            'rule': self.data['rule'].tolist(),
            'ground_truths': self.ground_truths,
            f'{self.model}_outputs': self.llm_outputs,
            'jaccard': jaccard,
            'levensthein': lev,
            'cosine': cosine
        })

        result_df.to_csv(self.results_csv, index=False)

        print(f'Metrics evaluation for XML-related violations has been computed.')


def _calculate_jaccard_similarity(ground_truth, llm_output):

    if ground_truth == "" and ground_truth == llm_output:
        return 1.0

    words_text1 = set(ground_truth.split(" "))
    words_text2 = set(llm_output.split(" "))
    
    intersection = len(words_text1.intersection(words_text2))
    union = len(words_text1.union(words_text2))
    
    jaccard_similarity = intersection / union if union != 0 else 0

    return jaccard_similarity


def _lev_helper(ground_truth, llm_output):

    if len(ground_truth) < len(llm_output):
        return _lev_helper(llm_output, ground_truth)

    if len(llm_output) == 0:
        return len(ground_truth)

    previous_row = range(len(llm_output) + 1)

    for i, c1 in enumerate(ground_truth):
        current_row = [i + 1]

        for j, c2 in enumerate(llm_output):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)

            current_row.append(min(insertions, deletions, substitutions))

        previous_row = current_row

    return previous_row[-1]


def _calculate_lev_distance(ground_truth, llm_output):

    
    if ground_truth == "" and ground_truth == llm_output:
        return 1.0

    if len(ground_truth) > 0 and len(llm_output) > 0:
        similarity = 1 - _lev_helper(ground_truth, llm_output) / max(len(ground_truth), len(llm_output))
    else: 
        similarity = 1.0

    return similarity


def _calculate_cosine_similarity(ground_truth, llm_output):

    
    if ground_truth == "" and ground_truth == llm_output:
        return 1.0

    try:
        vectorizer = CountVectorizer(stop_words=None)

        vectors = vectorizer.fit_transform([ground_truth, llm_output])

        similarity_matrix = cosine_similarity(vectors)

        cosine_similarity_value = similarity_matrix[0, 1]

    except ValueError as v:
        cosine_similarity_value = 0.0

    return cosine_similarity_value




class MetricsEvaluator:

    def __init__(self, outputs_csv: str, codebleu_params: str = "0.25,0.25,0.25,0.25"):
        
        self.data = pd.read_csv(outputs_csv)
        self.codebleu_params = codebleu_params
        
        self.snippet_langs = self.data['language'].tolist()
        self.ground_truths = self.data['ground_truths'].tolist()
        
        self.llm_outputs = {
            'gemini-1.5-flash-001': self.data['gemini-1.5-flash-001_output'].tolist(),
            'gpt-4o': self.data['gpt-4o_output'].tolist(),
            'gemini_in_android': self.data['gemini_in_android_output'].tolist()
        }

        self.java_snippets_csv = 'repair/metrics/java_snippets.csv'
        self.xml_snippets_csv = 'repair/metrics/xml_snippets.csv'
        
        self._extract_and_save_snippets()


    def _extract_and_save_snippets(self):

        java_data = {'_id': [], 'rule': [], 'ground_truths': [], 'gemini-1.5-flash-001': [], 'gpt-4o': [], 'gemini_in_android': []}
        xml_data = {'_id': [], 'rule': [], 'ground_truths': [], 'gemini-1.5-flash-001': [], 'gpt-4o': [], 'gemini_in_android': []}

        for index, language in enumerate(self.snippet_langs):
            _id = self.data['_id'][index]
            rule = self.data['rule'][index]
            ground_truth = self.ground_truths[index]
            gemini_output = self.llm_outputs['gemini-1.5-flash-001'][index]
            gpt4o_output = self.llm_outputs['gpt-4o'][index]
            gemini_in_android_output = self.llm_outputs['gemini_in_android'][index]

            if language == "java":
                java_data['_id'].append(_id)
                java_data['rule'].append(rule)
                java_data['ground_truths'].append(ground_truth)
                java_data['gemini-1.5-flash-001'].append(gemini_output)
                java_data['gpt-4o'].append(gpt4o_output)
                java_data['gemini_in_android'].append(gemini_in_android_output)
            elif language == "xml":
                xml_data['_id'].append(_id)
                xml_data['rule'].append(rule)
                xml_data['ground_truths'].append(ground_truth)
                xml_data['gemini-1.5-flash-001'].append(gemini_output)
                xml_data['gpt-4o'].append(gpt4o_output)
                xml_data['gemini_in_android'].append(gemini_in_android_output)
            else:
                raise ValueError(f"Unsupported language found: {language}")

        self._save_to_csv(java_data, self.java_snippets_csv)
        self._save_to_csv(xml_data, self.xml_snippets_csv)


    def _save_to_csv(self, data: dict, filename: str):

        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)

    
    def _get_metric_results_java(self):

        snippets_df = pd.read_csv(self.java_snippets_csv)

        for model in self.llm_outputs.keys():

            cbHelper = CodeBLEUHelper(model, snippets_df, self.codebleu_params)
            cbHelper.start()


    def _get_metric_results_xml(self):

        snippets_df = pd.read_csv(self.xml_snippets_csv)

        for model in self.llm_outputs.keys():

            xmlhelper = XMLHelper(model, snippets_df)
            xmlhelper.start()

    
    def run(self):

        """
        This function starts the computation of similarity metrics scores both for Java- and XML-related pairs
        of ground_truth and llm output.
        """

        self._get_metric_results_java()
        self._get_metric_results_xml()