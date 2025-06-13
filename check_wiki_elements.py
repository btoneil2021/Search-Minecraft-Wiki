import requests

url = "https://minecraft.wiki/w/Diamond"
response = requests.get(url)

print(response.text)
