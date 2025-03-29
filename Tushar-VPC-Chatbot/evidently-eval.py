import pandas as pd
from evidently.future.datasets import Dataset
from evidently.future.datasets import DataDefinition
from evidently.future.datasets import Descriptor
from evidently.future.descriptors import *
from evidently.future.report import Report
from evidently.future.presets import TextEvals
from evidently.future.metrics import *
from evidently.future.tests import *
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File
from evidently.ui.workspace.cloud import CloudWorkspace
from office365.graph_client import GraphClient
import sys
from dotenv import load_dotenv
import json
import os

load_dotenv()
EVIDENTLY_API_TOKEN = os.getenv("EVIDENTLY_API_TOKEN")
ws = CloudWorkspace(token=EVIDENTLY_API_TOKEN, url="https://app.evidently.cloud")

project = ws.get_project("0195b4cf-4354-724c-bccb-9e6cacb57f30")

eval_df = pd.read_csv("data/Langchain Test Prompts(VPC agent langchain).csv", encoding='latin1')
eval_df['context'] = "user should receive a full response giving them all elements of value proposition canvas"

eval_dataset = Dataset.from_pandas(pd.DataFrame(eval_df),
data_definition=DataDefinition(),
descriptors=[
    Sentiment("answer", alias="Sentiment"),
    TextLength("answer", alias="Length"),
    DeclineLLMEval("answer", alias="Denials"), 
    BiasLLMEval("answer", alias="Bias"),
    CompletenessLLMEval("answer", context="context", alias="Completeness")
])

eval_dataset = eval_dataset.as_dataframe()

# print(eval_dataset.head())
report = Report([
    TextEvals(),
    MinValue(column="Sentiment", tests=[gte(0)]),
    MaxValue(column="Length", tests=[lte(150)]),
    CategoryCount(column="Denials", category="DECLINE", tests=[eq(0)])
])
my_eval = report.run(eval_dataset, None)

ws.add_run(project.id, my_eval, include_data=True)
# print(json.dumps(report.run(eval_dataset, None).json(), indent=4))

