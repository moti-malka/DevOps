import requests
from http import HTTPStatus

print("Start clear chach")

cloudflare_api = 'https://api.cloudflare.com/client/v4/zones/<REPLACE_WITH_ZONE_ID>/purge_cache'

try:
    response = requests.post(
        url=cloudflare_api,
        headers = {
            "X-Auth-Email":"<REPLACE_WITH_YOUR_EMAIL>",
            "X-Auth-Key": "<REPLACE_WITH_API_KEY>"
        },
        data= '{"purge_everything": true}'
    )
    if response.status_code == HTTPStatus.OK:
        print(f"Successfully Purge everything from chach: {response.text}.")
    else:         
        raise ValueError(f"Failed to Purge from chach: {response.text}.")

except Exception as e:
    raise ValueError(f"Failed to Purge from chach: {e}.")
