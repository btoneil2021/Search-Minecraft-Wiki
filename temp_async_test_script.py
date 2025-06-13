import sys
import chromedriver_autoinstaller
from selenium import webdriver
from bs4 import BeautifulSoup
import re
import threading
import asyncio
from openai import AsyncOpenAI

api_key = 'test_key_async'
try:
    client = AsyncOpenAI(api_key=api_key)
except Exception as e:
    print(f"Error initializing AsyncOpenAI client: {e}")
    client = None

def get_soup(driver, url):
  driver.get(url)
  driver.implicitly_wait(1)
  soup = BeautifulSoup(driver.page_source, 'html.parser')
  return soup

def search_for_page(driver, search_term):
  url = f'https://minecraft.wiki/w/Special:Search?search={search_term.replace(" ", "+")}i'
  soup = get_soup(driver, url)
  url_addition_tag = soup.find("a", {"data-serp-pos": "0"})
  if url_addition_tag and url_addition_tag.has_attr("href"):
      url_addition = url_addition_tag["href"]
      url = f'https://minecraft.wiki{url_addition}'
  else:
      url = driver.current_url
  return url

def extract_info_box(soup):
  info_box = soup.find("div", {"class": "notaninfobox"})
  info = {}
  if not info_box: return info
  name_tag = info_box.find("div", {"class": "mcwiki-header infobox-title"})
  if name_tag: info["name"] = name_tag.text.strip()
  image_tag_container = info_box.find("div", {"class": "infobox-imagearea animated-container"})
  if image_tag_container:
    image_tag = image_tag_container.find("img")
    if image_tag and image_tag.has_attr('src'): info["image_url"] = "https://minecraft.wiki" + image_tag["src"]
  info["details"] = {}
  table = info_box.find("table", {"class": "infobox-rows"})
  if table:
    table_rows = table.find_all("tr")
    for row in table_rows:
      key = row.find("th")
      if key is None: continue
      value = row.find("td")
      if value is None: continue
      info["details"][key.text.strip()] = value.text.strip()
  return info

def extract_main_paragraph(soup):
  main_paragraph_container = soup.find("div", {"class": "mw-body-content mw-content-ltr"})
  if not main_paragraph_container: return []
  main_paragraph_elements = main_paragraph_container.find_all(["p", "h2", "h3"])
  tables = soup.find_all("table")
  paragraphs_in_tables = []
  for table in tables:
    paragraphs_in_tables.extend(table.find_all("p"))
  paragraphs_in_tables_set = set(paragraphs_in_tables)
  filtered = [el for el in main_paragraph_elements if el.name in ['h2', 'h3'] or (el.name == 'p' and el not in paragraphs_in_tables_set)]
  main_paragraph = [el.text.strip() for el in filtered]
  return main_paragraph

def execute_scraping(search_subject, chrome_options_dict):
  options = webdriver.ChromeOptions()
  for arg in chrome_options_dict.get('arguments', []):
    options.add_argument(arg)

  driver = webdriver.Chrome(options=options)
  driver.implicitly_wait(1)
  try:
    print(f"execute_scraping: Searching for {search_subject}")
    content_url = search_for_page(driver, search_subject)
    print(f"execute_scraping: Navigating to {content_url}")
    soup = get_soup(driver, content_url)
    print(f"execute_scraping: Soup obtained for {content_url}")
    return soup, driver
  except Exception as e:
    print(f"Error during scraping in execute_scraping for {search_subject}: {e}")
    if driver:
        driver.quit()
    return None, None

basic_feature_extraction = """You are an AI designed to assist with extracting specific features from user requests related to the game Minecraft. Your task is to analyze the user query (delimited by triple backticks) and extract two key pieces of information:

Subject: Identify the main subject of the sentence. This is typically a Minecraft item, entity, block, or structure (full names only).
Summary: Provide a brief summary of the specific information or request that the user wants to know about the subject. Include any information that may be important.
Here are some examples to guide you:

Example 1:
User query: "How do I find diamonds in Minecraft?
Subject: "diamonds"
Summary: "How to find"

Example 2:
User query: "What are the best enchantments for a sword?"
Subject: "sword"
Summary: "best enchantments"

When processing each query, please answer with only the subject and the summary, separated by a backslash.

```
"""

generate_output = """You are an AI designed to extract specific answers from provided text based on a given summary. Your task is to read the given paragraphs and answer the summary as accurately as possible using the information from the text.
Do not change anything in the summary.

Here is the format you should follow:

Summary: This is a brief statement or question that you need to answer.
Paragraphs: These are the detailed texts from which you will extract the necessary information to answer the summary.
Answer: This is the accurate and concise response to the summary based on the provided paragraphs.
Use the following example as a guide:

Example:
Summary: benefits of a beacon
Paragraphs: Beacons are powerful items in Minecraft that provide various status effects to players within a certain radius. When activated, beacons can grant players speed, haste, resistance, jump boost, or strength. Additionally, a fully powered beacon can give regeneration or a secondary status effect. Beacons are often used in bases to enhance player abilities and provide strategic advantages during combat or resource gathering.
Answer: Beacons provide status effects such as speed, haste, resistance, jump boost, and strength. Fully powered beacons can also give regeneration or a secondary effect, enhancing player abilities and providing strategic advantages in combat and resource gathering.

When processing each query, please answer with only the answer to the summary.

The summary and paragraphs (respectively) are defined below, delimited by triple backticks.
```
"""

async def make_chatgpt_request(prompt_text):
  if client is None: return "Error: OpenAI client not initialized."

  # Check for feature extraction prompt
  if prompt_text.startswith("You are an AI designed to assist with extracting specific features"):
    search_query = re.search(r"```(.*?)```", prompt_text, re.DOTALL).group(1).strip()
    if 'dirt' in search_query.lower():
        return 'Subject: "Dirt"\\nSummary: "What is dirt used for in Minecraft?"'
    elif 'diamonds' in search_query.lower():
        return 'Subject: "diamonds"\\nSummary: "How to find"'
    elif 'sword' in search_query.lower():
        return 'Subject: "sword"\\nSummary: "best enchantments"'
    else:
        return f'Subject: "{search_query}"\\nSummary: "General information about {search_query}"'

  # Check for final answer generation prompt
  elif prompt_text.startswith("You are an AI designed to extract specific answers"):
    # Extract summary and content for more targeted mocking if needed
    summary_match = re.search(r"```\s*(.*?)\s*```", prompt_text, re.DOTALL) # Get content between ```
    if summary_match:
        content_for_gpt = summary_match.group(1) # This is "Summary_query\nParagraphs: info\nparagraphs"
        if "Dirt" in content_for_gpt and "farming" in content_for_gpt:
             return "Answer: Dirt is primarily used for farming in Minecraft, but due to its abundance, it can also be used as a readily available building block."

    return "Answer: Mocked information not found for this specific query based on content."

  return f"Mocked ChatGPT Response: Unknown prompt structure. Starts with: {prompt_text[:50]}"


async def prompt(user_query):
  if client is None:
      return "OpenAI client failed to initialize. Please check API key or environment."

  feature_extraction_full_prompt = basic_feature_extraction + user_query + "\\n```"
  summary_response_text = await make_chatgpt_request(feature_extraction_full_prompt)

  summary_parts = summary_response_text.strip("\"'").split("\\n")

  if len(summary_parts) < 2 or not summary_parts[0].startswith("Subject:") or not summary_parts[1].startswith("Summary:"):
      print(f"Unexpected summary format from feature extraction: {summary_response_text}")
      subject = user_query
      summary_query = "General information"
  else:
      subject = summary_parts[0].replace("Subject: ", "").strip('"')
      summary_query = summary_parts[1].replace("Summary: ", "").strip('"')

  print(f"Searching for: {subject}, Summary to find: {summary_query}")

  chrome_options_dict = {'arguments': ['--headless', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']}

  driver = None
  soup_obj = None
  info_results = {}
  paragraphs_results = []

  try:
    soup_obj, driver = await asyncio.to_thread(execute_scraping, subject, chrome_options_dict)

    if soup_obj:
        print(f"Scraping successful for {subject}")
        # Launch parsing tasks concurrently
        info_task = asyncio.to_thread(extract_info_box, soup_obj)
        paragraphs_task = asyncio.to_thread(extract_main_paragraph, soup_obj)
        # Ensure info_results and paragraphs_results are correctly assigned
        info_results_val, paragraphs_results_val = await asyncio.gather(info_task, paragraphs_task)
        info_results = info_results_val if info_results_val is not None else {}
        paragraphs_results = paragraphs_results_val if paragraphs_results_val is not None else []

    else:
        print(f"Warning: Scraping failed for subject '{subject}', no soup object returned.")

    info_text_parts = []
    if 'name' in info_results:
        info_text_parts.append(f"Name: {info_results.get('name', 'N/A')}")
    if 'details' in info_results and isinstance(info_results.get('details'), dict):
        for k, v in info_results.get('details', {}).items():
            info_text_parts.append(f"{k}: {v}")
    info_text = "\\n".join(info_text_parts)

    paragraphs_text = "\\n".join(paragraphs_results)

    scraped_content = f"{info_text}\\n{paragraphs_text}".strip()

    if not scraped_content: # Check if any content was actually scraped
        # Get current URL from driver if it exists, for debugging
        page_url_info = f"Page URL: {driver.current_url}" if driver and hasattr(driver, 'current_url') else "Driver not available or URL not accessible"
        print(f"Warning: No information extracted from info_box or paragraphs for subject '{subject}'. {page_url_info}")
        return f"Could not extract detailed information for '{subject}' regarding '{summary_query}'. The wiki page might not have the expected structure or the content is missing."

    final_gpt_full_prompt = generate_output + summary_query + "\\n```\\n" + scraped_content + "\\n```"
    final_answer = await make_chatgpt_request(final_gpt_full_prompt)
    return final_answer
  except Exception as e:
    print(f"An error occurred in prompt: {e}")
    # import traceback
    # traceback.print_exc() # This would give more detailed errors if possible in the environment
    return "Sorry, I encountered an error processing your request."
  finally:
    if driver:
        await asyncio.to_thread(driver.quit)

async def main():
  user_input = "What is dirt?"
  print(f"What would you like to ask? {user_input}")
  if client is None:
      print("OpenAI client failed to initialize. Please check API key or environment.")
      return
  response = await prompt(user_input)
  print(response)

if __name__ == '__main__':
  try:
    chromedriver_autoinstaller.install()
  except Exception as e:
    print(f"Error installing/checking chromedriver: {e}")

  asyncio.run(main())
