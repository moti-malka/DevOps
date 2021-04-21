# Set the user and pass for auth.
$user = "APIUSER"
$token = "<REPLACE_WITH_YOUR_PAT>";

# Set the bse url
$basu_uri = "https://dev.azure.com/<organization>/<project>/_apis"

$headers = @{Authorization = 'Basic ' + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$($token)")) } 

# list of all the groups that want to find where they are used
$task_groups = @("<TASK_GROUP_ID>")

# Loop over all tasks group
foreach($taskg in $task_groups){
   
    # Get all build definitions.
    $definitions = Invoke-WebRequest -Uri "$($basu_uri)/build/definitions?api-version=6.1-preview.6" -Headers $headers -Method Get;
    $definitions = ($definitions.Content | ConvertFrom-Json ).value;

    # Loop over all definitions.
    foreach($def in $definitions){
    
        # Get definition data by id.
        $defData = Invoke-WebRequest -Uri "$($basu_uri)/build/definitions/$($def.id)?api-version=6.1-preview.6" -Headers $headers -Method Get;
        $defData = $defData.Content | ConvertFrom-Json;

        $isUsingTaskGroup = $defData.process.phases[0].steps | Where-Object {$_.task.id -eq $taskg}

        if($null -ne $isUsingTaskGroup ){
            
            "The build: $($def.name) is using in task group: $($isUsingTaskGroup.displayName)"
        }
    }
}
