# An Investigation of LLMs for Android Vulnerability Repair 

This repository contains a newly dataset of Android vulnerabilities extracted from real-world Android applications, coupled with their ground truth fixes. Three chat-based LLMs (GPT-4o, Gemini 1.5 Flash and Gemini in Android Studio) are tested on this new dataset to assess their performance in repairing such vulnerabilities. The code used to compare LLMs repairs with ground truth is shared as well.

## Dataset Details

The dataset contains 272 vulnerabilities, which are violations to the [Android Security Best Practices](https://developer.android.com/privacy-and-security/security-tips) in both Java classes and the Android Manifest file. There are a total of 176 violations written in Java and 96 violations written in XML, covering 18 different categories of vulnerabilities.

Each entry in the dataset includes the following information:

-   `id`                : an unique id identifying the vulnerability
-   `rule`              : the number corresponding to the violated best practice
-   `language`          : the language of the snippet (Java or XML)
-   `vulnerable_snippet`: the vulnerable code snippet
-   `ground_truths`     : the corresponding ground truth repair

Vulnerabilities are detected using [SPECK](https://github.com/SPRITZ-Research-Group/SPECK).

#### SPECK modifications

The source code of SPECK is reported as well, containing a new script `detection/SPECK/additional/mapper.py` which performs a mapping between the faulty line in the decompiled file to the corresponding line in the original source code file and then extracts the the context (i.e, Java method or full component declaration) of the faulty line detected by SPECK.

## Prompting LLMs

Results from LLMs are obtained using the following script `repair/prompting_llms/helpers.py`. It includes:

- `PromptManager` to prepare all the prompts given the snippets and relative information
- `Requester` to send prompts via APIs if possible (GPT-4o and Gemini 1.5 Flash)
- `OutputManager` to get and save results from LLMs

## Similarity Metrics 

Similarity metrics are used to compare the repair proposed by the three LLMs to the ground truth fix presented in the new dataset. 

- For **Java** repairs: [CodeBLEU](https://github.com/microsoft/CodeXGLUE/tree/main/Code-Code/code-to-code-trans)
- For **XML** repairs: Jaccard similarity, Levenshtein distance, cosine similarity 

The directory `repair/metrics` contains the scripts:

- `run_metrics.py` : it starts the post-processing phase for the snippets and computes all similarity scores (both for Java- and XML-related snippets).
- `utils_java.py` and `utils_xml.py` contain utility functions to support the specific needs of this project.

## Additional Information

The `repair/__init__.py` file starts the whole implementation for repair (prompting and metrics evaluation).

A sample dataset is provided with the aim of making clearer the evaluation process to compute similarity scores(see `repair/prompting_llms/results/llm_outputs.py`) and it already contains llm outputs.

In addition, the metrics results for **llm_outputs.csv** are saved in:
- `repair/metrics/results_java` : it contains CodeBLEU similarity scores 
- `repair/metrics/results_xml`  : it contains Jaccard, Levenshtein, Cosine similarity scores 


