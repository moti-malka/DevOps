import json
import logging
import collections
from msrest.authentication import BasicAuthentication
from azure.devops.connection import Connection
from azure.devops.v5_1.work_item_tracking.models import Wiql
from azure.devops.v5_1.py_pi_api import JsonPatchOperation
import requests
import os
from dotenv import load_dotenv
import re

# Parse a .env file and then load all the variables found as environment variables.
load_dotenv()

# read azure devops properties from env.
ORG_NAME = os.environ['ORG_NAME']
PROJ_NAME = os.environ['PROJ_NAME']
TEAM_ID = os.environ['TEAM_ID']
PAT = os.environ['PAT']
AZUR_DEV_API = f'https://dev.azure.com/{ORG_NAME}'
ASSIGN_TO = os.environ['ASSIGN_TO']
MENTION = os.environ['MENTION']
ELK_URL = os.environ['ELK_URL']

logger = logging.getLogger('app')

logger.setLevel(logging.DEBUG)

# Function to get errors logs from elastic.
def start():
    """Function to get errors logs from elastic."""

    logger.info('get errors logs from elastic')

    # Create request client.
    get_logs_err_req = requests.Session()

    query = { "query": { "bool": { "must": [ { "match": { "level": "Error" } }, { "exists": { "field": "fields.ActionName" } } ], "filter": { "range": { "@timestamp": { "from": "now-1d", "to": "now" } } } } } }

    headers = {"Content-Type": "application/json"}

    # Make the request.
    get_logs_err_response = get_logs_err_req.get(ELK_URL, data=json.dumps(query), headers=headers)

    # Check if request success or not.
    if get_logs_err_response.ok:
        logger.info(f"Succesfully to get logs error from elasticsearch.")
        open_bugs(json.loads(get_logs_err_response.content)['hits'])
    else:
        logger.error(
            f"Failed to get logs error from elasticsearch: {get_logs_err_response.content}.")

# Function to create new bugs based on logs.
def open_bugs(logs_error):
    """Function to create new bugs based on logs.
       - logs_error: List of error"""

    logger.info(
        f"open_bugs is trigger, found {len(logs_error['hits'])} logs_error")

    # Set the current iteration path
    CURRENT_ITERATION_PATH = get_current_iteration()

    log_err_groups = collections.defaultdict(list)

    # group error by ActionName
    for log_obj in logs_error['hits']:
        log_err_groups[log_obj['_source']['fields']
                       ['ActionName']].append(log_obj)

    # Implementat a Basic Authentication
    azure_dev_cred = BasicAuthentication("user", PAT)

    # Create connection to azure devops.
    connection = Connection(base_url=AZUR_DEV_API, creds=azure_dev_cred)

    # Create client to track workitems.
    wit_track_client = connection.clients.get_work_item_tracking_client()

    for k, v in log_err_groups.items():

        # generate query to check if bug is already created.
        query = "SELECT [System.Title] FROM WorkItems WHERE [System.Title] = 'PROD || {0}' AND [System.State] <> 'Closed' AND [System.State] <> 'Resolved'".format(
            k)

        # Make the query.
        query_wiql = Wiql(
            query=query)

        # Get the workitems results.
        results = wit_track_client.query_by_wiql(query_wiql).work_items

        # Convert workitems results to list.
        work_items = list((wit_track_client.get_work_item(int(result.id))
                           for result in results))

        # Check workitems exists.
        if any(work_items):

            logger.info(f'Update counter for BUG with ID: {work_items[0].id}.')

            # Get workitem description.
            wi_body = work_items[0].fields['Microsoft.VSTS.TCM.ReproSteps']

            # Extract only relevant string from body.
            old_counter_msg = (wi_body).split(":")[0]

            # Extract current counter.
            old_number = int(re.search(r'\d+', old_counter_msg).group())

            # Add new number to current counter.
            new_number = old_number + len(v)

            # Set the new message.
            new_counter_msg = old_counter_msg.replace(
                str(old_number), str(new_number))
            wi_body = wi_body.replace(old_counter_msg, new_counter_msg)

            # Create the patch update
            patch_document = [
                JsonPatchOperation(
                    op="replace",
                    path="/fields/Microsoft.VSTS.TCM.ReproSteps",
                    value=wi_body
                )
            ]

            # Make the update request
            wit_track_client.update_work_item(patch_document, work_items[0].id)

            logger.info(
                f'Successfully to update error counter from {old_number} to {old_number + len(v)}.')

            # Continue to next log error.
            continue

        logger.info(f'Create new bug for ActionName: {k}.')

        # Create empty list for new bug.
        documents = []

        # add title field
        documents.append(JsonPatchOperation(
            from_=None, op='add', path="/fields/System.Title", value=f'PROD || {k}'))

        # add assignTo field
        documents.append(JsonPatchOperation(
            from_=None, op='add', path="/fields/System.AssignedTo", value=ASSIGN_TO))

        # add ReproSteps field
        documents.append(JsonPatchOperation(from_=None, op='add', path="/fields/Microsoft.VSTS.TCM.ReproSteps",
                         value=f"FOUND THIS ERROR {len(v)} TIMES: {v[0]['_source']}"))

        # add Tags
        documents.append(JsonPatchOperation(
            from_=None, op='add', path="/fields/System.Tags", value="Base On Logs"))

        # add IterationPath field
        documents.append(JsonPatchOperation(
            from_=None, op='add', path="/fields/System.IterationPath", value=CURRENT_ITERATION_PATH))

        response = wit_track_client.create_work_item(
            documents, PROJ_NAME, 'Bug')

        add_mention(response.id)

    logger.info(f"Successfully create bags based on logs.")

    return True

# Function to add mention on work items.
def add_mention(workItemId):
    """Function to add mention on work items."""

    logger.info('add mention on work items')

    # Create request client.
    add_mention_req = requests.Session()

    # Set request basic auth.
    add_mention_req.auth = ('user', PAT)

    data = {"text": f"<div><a href=\"#\" data-vss-mention=\"version:2.0,55cec498-9de4-468b-ae58-df96c65026e8\">{MENTION}</a>&nbsp;A new bug was found</div>"}

    headers = {"Content-Type": "application/json"}

    add_mention_req
    # Make the request.
    add_mention_req_response = add_mention_req.post(
        f'{AZUR_DEV_API}/{PROJ_NAME}/_apis/wit/workItems/{workItemId}/comments?api-version=6.0-preview.3', data=json.dumps(data), headers=headers)

    # Set request basic auth.
    if add_mention_req_response.ok:

        logger.info(f"Successfully add menation for user.")
    else:
        logger.error(
            f"Failed to add menation for user {add_mention_req_response.content}.")

# Function to get current iteration path.
def get_current_iteration():
    """Function to get the current iteration path."""

    logger.info('Get current iteration path')

    # Create request client.
    get_current_iter_req = requests.Session()

    # Set request basic auth.
    get_current_iter_req.auth = ('user', PAT)

    # Set request basic auth.
    get_current_iter_response = get_current_iter_req.get(
        f'{AZUR_DEV_API}/{PROJ_NAME}/{TEAM_ID}/_apis/work/teamsettings/iterations?api-version=6.0')

    # Set request basic auth.
    if get_current_iter_response.ok:

        iterations = json.loads(get_current_iter_response.content)['value']

        for iteration in iterations:
            if iteration['attributes']['timeFrame'] == 'current':

                logger.info(f"Found iteration path: {iteration['path']}")

                return iteration['path']

    logger.error(
        f"Failed to get iteration path {get_current_iter_response.content}.")
    return ""
