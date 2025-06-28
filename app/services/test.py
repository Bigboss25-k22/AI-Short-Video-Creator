# import requests
# import xmltodict
# import json

# url = "https://trends.google.com.vn/trending/rss?geo=VN"
# response = requests.get(url)
# data = xmltodict.parse(response.content)

# for item in data["rss"]["channel"]["item"]:
#     print(item["title"])

import requests
url = ('https://newsapi.org/v2/top-headlines?'
       'country=us&'
       'apiKey=9a819f64bb7d4aab9a7603fc41284cc1')
response = requests.get(url)
print(response.json())