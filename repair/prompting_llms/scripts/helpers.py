import openai
import time, os
import re, logging
import pandas as pd

import repair.prompting_llms.scripts.utils as utils

from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

PROMPTING_LLMS_PATH = "repair/prompting_llms/"
RESPONSES_PATH = os.path.join(PROMPTING_LLMS_PATH, "responses")


class PromptManager:

    def __init__(self) -> None:
        
        self.prompt_template = """The code snippet below has a vulnerability at line [LINE_NUMBER]. It does not follow the security guideline: '[GUIDELINE]'.\nModify the snippet to be consistent with the best practice.\n\n[CODE_SNIPPET]\n\nPlease use the following output structure:\n\n<MODIFIED_CODE> write here the modified code\n\n<EXPLANATION> write here an explanation of the modifications done to the code snippet to make it compliant to the guideline\n"""

        self.system_role = ""

        self.codes_csv_path = "repair/prompting_llms/sample_dataset.csv"

        self.df = pd.read_csv(self.codes_csv_path)

        self.complete_prompts = self.prepare_all_prompts()
        
                
    def prepare_all_prompts(self):

        """
        This function prepares the prompts for LLMs given the vulnerable snippets and relative information.
        """
            
        complete_prompts = []

        for _, row in self.df.iterrows():
            
            prompt = utils.get_prompt(row, self.prompt_template)
            complete_prompts.append(prompt)           

        print('Prompts are ready.')
        return complete_prompts
                


class Requester:

    def __init__(self, model: str, prompt_manager: PromptManager):
        
        self.model = model
        self.checkpoint = f"repair/prompting_llms/checkpoints/checkpoint_{model}.pkl"

        self.responses = []

        self.prompt_manager = prompt_manager    

        load_dotenv()   # to retrieve api-key in .env file


    def _send_request(self, prompt, system_role):

        model = self.model

        if model.startswith("gpt"):
            # note: each request is a new chat, as we need
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            request = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_role},
                    {"role": "user", "content": prompt}
                ]
            )

            return request.choices[0].message.content

        elif model.startswith("gemini"):
            # note: each request is a new chat, as we need
            genai.configure(api_key = os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)

            return response.text
        
        else:

            print('Chosen model is not valid.')
            exit(0)

    
    def get_responses(self):

        prompts = self.prompt_manager.complete_prompts
        system_role = self.prompt_manager.system_role

        if prompts is not None and system_role is not None:

            responses, last_index = utils.load_checkpoint(self.checkpoint)

            print(f'Sending requests for {self.model}...')
        
            for index in range(last_index+1, len(prompts)):
                trials = 0
                while True:
                    try:
                        # start a new chat for every prompt
                        response = self._send_request(prompts[index], system_role)
                        responses.append(f'{response}\n\n')

                        utils.save_checkpoint(self.checkpoint, responses, index)
                        print(f'Response for prompt n. {index} saved.')
                        break

                    except openai.RateLimitError:
                        print("Rate limit reached. Waiting for 60 seconds...")
                        time.sleep(60)
                        if trials < 3:
                            trials += 1
                        else: 
                            responses.append("<MODIFIED_CODE> RATE_LIMIT_EXCEPTION\n\n")
                            break
                        
                    except openai.APIError:
                        print("Retrying...")
                        if trials < 3:
                            trials += 1
                        else: 
                            responses.append("<MODIFIED_CODE> API_ERROR\n\n")
                            break

                    except Exception as e:
                        print(f'Failure for prompt n. {index}. Trying again...')
                        if trials < 3:
                            trials += 1
                        else: 
                            responses.append("<MODIFIED_CODE> UNKNOWN_ERROR\n\n")
                            break

            self.responses = responses

            print(f'All requestes for {self.model} are completed.')
        
        else:
            exit(0)


class OutputManager:

    def __init__(self, requester: Requester) -> None:
        

        self.requester = requester
        self.responses = requester.responses
        self.final_answers = []

        self.error_ids = []
        

    def save_responses_as_txt(self):

        if not os.path.isdir(f"{RESPONSES_PATH}/{self.requester.model}/txt"):
            os.makedirs(f"{RESPONSES_PATH}/{self.requester.model}/txt", exist_ok=True)

        with open(f'{RESPONSES_PATH}/{self.requester.model}/txt/responses.txt', 'w') as file:

            for index, response in enumerate(self.responses):

                line = f'ID. {index}\n\n{response}\n\n'
                divider = "-----" * 5 + "\n\n"

                file.write(line+divider)


    def extract_content(self):        

        modified_codes, explanations = [], []

        for index, elem in enumerate(self.responses):

            elem = elem.replace("```java", "\n").replace("```xml", "\n").replace("```", "\n")
            elem = elem.replace("</MODIFIED_CODE>", "\n")

            modified_code_match = re.search(r'<MODIFIED_CODE>(.*?)<EXPLANATION>', elem, re.DOTALL)
            modified_code = modified_code_match.group(1).strip() if modified_code_match else ""

            explanation_match = re.search(r'<EXPLANATION>(.*)', elem, re.DOTALL)
            explanation = explanation_match.group(1).strip() if explanation_match else ""

            if modified_code_match:
                modified_codes.append(modified_code)
                explanations.append(explanation)
            else:
                self.error_ids.append(index)
                modified_codes.append(f'EXTRACTION_ERROR -- Original Output:\n{elem}')
                explanations.append(f'EXTRACTION_ERROR -- Original Output:\n{elem}')


        return modified_codes, explanations



    def save_bad_format_responses(self):

        if len(self.error_ids) > 0:

            malformed_dir = f"{RESPONSES_PATH}/{self.requester.model}/malformed/"
            os.makedirs(malformed_dir, exist_ok=True)

            output_file_path = f"{malformed_dir}/bad_format.txt"

            with open(output_file_path, "w") as file:
                for id in self.error_ids:
                    line = f"ID. {id}:\n\n{self.responses[int(id)]}\n\n"
                    divider = "-----" * 5 + "\n\n"
                    file.write(line + divider)


    def save_outputs_to_csv(self):

        modified_codes, explanations = self.extract_content()

        if not os.path.isdir(f"{PROMPTING_LLMS_PATH}/results/"):
            os.mkdir(f"{PROMPTING_LLMS_PATH}/results")

        results_csv = os.path.join(PROMPTING_LLMS_PATH, f"results/results_{self.requester.model}.csv")
        modified_codes_csv = os.path.join(PROMPTING_LLMS_PATH, f"results/llms_outputs.csv")

        if not os.path.isfile(results_csv) or not os.path.isfile(modified_codes_csv):

            df = pd.read_csv(self.requester.prompt_manager.codes_csv_path)

            common_df = pd.DataFrame({
                '_id': df['_id'].tolist(),
                'rule': df['rule'].tolist(),
                'language': df['language'].tolist(),
                'ground_truths': df['ground_truths'].tolist()
            })

            if not os.path.isfile(results_csv):
                common_df.to_csv(results_csv, index=False)

            if not os.path.isfile(modified_codes_csv):
                common_df.to_csv(modified_codes_csv, index=False)

        result_df = pd.read_csv(results_csv)
        result_df[f'complete_output'] = self.responses
        result_df[f'modified_codes'] = modified_codes
        result_df[f'explanations'] = explanations
        result_df.to_csv(results_csv, index=False)

        modified_codes_df = pd.read_csv(modified_codes_csv)
        modified_codes_df[f'{self.requester.model}_output'] = modified_codes
        modified_codes_df.to_csv(modified_codes_csv, index=False)  


    def save_outputs(self):

        """
        This function saves the LLMs outputs in different formats:
        - txt files for the complete output
        - csv files to better handle the results (see llm_outputs.csv)
        - malformed folder to save bad formatted outputs
        """

        print(f'Saving results ...')
        self.save_responses_as_txt()
        self.save_outputs_to_csv()
        self.save_bad_format_responses()

        print('Results saved.')

    
    def get_outputs_from_checkpoint(self):

        outputs, _ = utils.load_checkpoint(self.requester.checkpoint)
        self.responses = outputs

        self.save_outputs()



def get_outputs_from_csv(csv: str):

    """
    This function reads outputs from a csv and adds them to llm_outputs.csv in order to have them processed 
    and analysed.

    Parameters:
        - csv file with llm outputs
    """

    outputs = pd.read_csv(csv)

    model = outputs.columns[0]

    req = Requester(model, PromptManager())
    
    om = OutputManager(req)
    om.responses = outputs[model].tolist()

    om.save_outputs()



