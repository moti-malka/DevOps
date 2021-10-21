##########################################################
#  Best Practices for Kubernetes Workload Configuration  #
##########################################################
import subprocess
import json

# class definition for polaris.
class ReportModel(object):
    namespace = str
    name = str
    kind = str
    message = str
    severity = str
    category = str

    
    def __init__(self, namespace, name, kind, message, severity, category):
        self.namespace = namespace
        self.name = name
        self.kind = kind
        self.message = message
        self.severity = severity
        self.category = category

# New epty list report.
reports = []

# Run polaris audit report.
audit = subprocess.run(['./polaris', 'audit'], stdout=subprocess.PIPE).stdout.decode('utf-8')

# Deserialize audit json as a python object.
audit_json = json.loads(audit)

# Start loop on all audit results.
for result in audit_json['Results']:
    if 'PodResult' in result and result['PodResult'] != None:
      for v in result['PodResult']['ContainerResults']:
          for container_key, container_val  in v['Results'].items():
                reports.append(ReportModel(namespace = result['Namespace'],
                                           name      = result['Name'],
                                           kind      = result['Kind'],
                                           message   = container_val['Message'],
                                           severity  = container_val['Severity'],
                                           category  = container_val['Category']))
    if len(result['Results']) > 0:
        for result_key, result_value in result['Results'].items():
            reports.append(ReportModel(namespace = result['Namespace'],
                                           name      = result['Name'],
                                           kind      = result['Kind'],
                                           message   = result_value['Message'],
                                           severity  = result_value['Severity'],
                                           category  = result_value['Category']))

# Save audit result as a json file.
with open('audit.json', 'w') as f:
    json.dump([ob.__dict__ for ob in reports], f, ensure_ascii=False, indent=4)
