import requests

from lxml import etree

def get_user_uuid(nextcloud_url, username, password):
    api_url = f"{nextcloud_url}/ocs/v1.php/cloud/user"
    headers = {"OCS-APIRequest": "true"}

    response = requests.get(api_url, auth=(username, password), headers=headers)

    if response.status_code == 200:
        try:
            # Parse the XML response
            root = etree.fromstring(response.content)
            user_id = root.xpath('//ocs/data/id/text()')

            if user_id:
                return user_id[0]
            else:
                print("UUID not found in response.")
                return None
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return None
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Example usage:
nc_url = "https://myrga.nsupdate.info"
username = "xxx"
password = "yyy"
user_uuid = get_user_uuid(nc_url, username, password)
print("User UUID:", user_uuid)
