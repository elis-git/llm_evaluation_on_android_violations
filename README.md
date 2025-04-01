# A Dataset for Evaluating LLMs Vulnerability Repair Performance in Android Applications

This repository contains a newly created dataset of Android faulty code extracted from real-world Android applications, coupled with their ground truth fixes. Three chat-based LLMs (GPT-4o, Gemini 1.5 Flash and Gemini in Android Studio) are tested on this new dataset to assess their performance in repairing them. The code used to compare LLMs repairs with ground truth is shared as well.

## Dataset Details

The dataset (see `dataset.csv`) contains 272 vulnerabilities, which are violations to the [Android Security Best Practices](https://developer.android.com/privacy-and-security/security-tips) in both Java classes and the Android Manifest file. There are a total of 176 violations written in Java and 96 violations written in XML, covering 18 different categories of security violations.

Each entry in the dataset includes the following information:

-   `id`                : an unique id identifying the vulnerability
-   `rule`              : the number corresponding to the violated best practice
-   `language`          : the language of the snippet (Java or XML)
-   `vulnerable_snippet`: the vulnerable code snippet
-   `ground_truths`     : the corresponding ground truth repair

Violations are detected using [SPECK](https://github.com/SPRITZ-Research-Group/SPECK).

**NOTE**: The dataset excludes any information about the original APKs, as detection results were not shared with developers. Additionally, the snippets focus solely on the relevant parts of the Java methods, with *"rest of the code"* comments marking the omitted sections.

#### SPECK modifications

The source code of SPECK is reported as well, containing a new script `detection/SPECK/additional/mapper.py` which performs a mapping between the faulty line in the decompiled file to the corresponding line in the original source code file and then extracts the the context (i.e., Java method or full component declaration) of the faulty line detected by SPECK.

## Prompting LLMs

Results from LLMs are obtained using the following script `repair/prompting_llms/helpers.py`. It includes:

- `PromptManager` to prepare all the prompts given the snippets and relative information
- `Requester` to send prompts via APIs 
- `OutputManager` to get and save results from LLMs

## Similarity Metrics 

Similarity metrics are used to compare the repair proposed by the three LLMs to the ground truth fix presented in the new dataset. 

- For **Java** repairs: [CodeBLEU](https://github.com/microsoft/CodeXGLUE/tree/main/Code-Code/code-to-code-trans)
- For **XML** repairs: Jaccard similarity, Levenshtein distance, cosine similarity 

The directory `repair/metrics` contains the scripts:

- `run_metrics.py` : it starts the post-processing phase for the snippets and computes all similarity scores (both for Java- and XML-related snippets).
- `utils_java.py` and `utils_xml.py` contain utility functions to support the specific needs of this project.

## Additional Information

The `repair/__init__.py` file starts the complete flow for repair (prompting and metrics evaluation).

A sample dataset is provided with the aim of making clearer the evaluation process to compute similarity scores (see `repair/prompting_llms/results/llm_outputs.py`) and it already contains llm outputs.

In addition, the metrics results for **llm_outputs.csv** are saved in:
- `repair/metrics/results_java` : it contains CodeBLEU similarity scores for each model
- `repair/metrics/results_xml`  : it contains Jaccard, Levenshtein, Cosine similarity scores for each model

---

## Examples Snippets from the Dataset

Below are two pairs of vulnerable-fixed code snippets taken from our dataset. These examples want to provide insight into the types of security issues the dataset captures and how they can be addressed.

### Example of Java-related Violation

The following vulnerable snippet violates *Rule 4: Use intents to defer permission*. This best practice recommends avoiding unnecessary permission requests by delegating actions to apps that already have the required permissions. You can read more [here](https://developer.android.com/privacy-and-security/security-best-practices#permissions-intents).

The corresponding fixed version demonstrates how to properly implement this best practice to enhance security.

#### Vulnerable Code  

```java
void freeLocationListeners() {
    // rest of the code
    for (int i = 0; i < locationListeners.length; i++) {
        locationManager.removeUpdates(locationListeners[i]);
        locationListeners[i] = null;
    }
    locationListeners = null;
    if (MyDebug.LOG) Log.d(TAG, "location listeners now freed");
}
```

#### Fixed Code
```java
void freeLocationListeners() {
    // rest of the code
    Intent locationIntent;
    for (int i = 0; i < locationListeners.length; i++) {
        locationIntent = new Intent();
        locationIntent.setComponentName("com.example.target", "com.example.target.LocationManagerActivity");
        locationIntent.setAction("ACTION_REMOVE_UPDATES");
        locationIntent.putExtra("provider", locationListeners[i]);  
        startActivity(locationIntent);
    }
    if (MyDebug.LOG) Log.d(TAG, "location listeners now freed");
}
```

### Example of XML-related Violation

The following snippet violates *Rule 23: Restrict Broadcast Access*, the best practice of restricting exported broadcast receivers. When android:exported="true" is set without a permission, any app can send broadcasts to this receiver, posing a security risk. You can read more [here](https://developer.android.com/privacy-and-security/security-tips#broadcast-receivers).

The corresponding fixed version demonstrates how to properly implement this best practice to enhance security.

#### Vulnerable Code  

```xml
<receiver
    android:name="app_package.core.widget.appwidgets.AppWidgetMD"
    android:exported="true"
    android:label="@string/app_widget_md_name">
    <intent-filter>
        <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
    </intent-filter>
    <meta-data
        android:name="android.appwidget.provider"
        android:resource="@xml/app_widget_md_info" />
</receiver>
```

#### Fixed Code
```xml
<receiver
    android:name="app_package.core.widget.appwidgets.AppWidgetMD"
    android:exported="true"
    android:label="@string/app_widget_md_name"
    android:permission="custom_permission" <!--choose your permission here--> >
    <intent-filter>
        <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
    </intent-filter>
    <meta-data
        android:name="android.appwidget.provider"
        android:resource="@xml/app_widget_md_info" />
</receiver>
```
