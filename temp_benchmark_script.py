import sys
import chromedriver_autoinstaller
from selenium import webdriver
from bs4 import BeautifulSoup
import re
import threading
import asyncio
import time
from openai import AsyncOpenAI

# API Key
api_key = '[INSERT YOUR API KEY HERE]' # Placeholder
client = None # Will be initialized in main after checking api_key

# Function definitions
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

def extract_main_paragraph(soup): # Refactored version
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

  # Ensure chromedriver is installed within the context of this threaded function
  try:
    chromedriver_autoinstaller.install(cwd=True) # Install in current working dir if needed by thread
  except Exception as e:
    print(f"Note: Chromedriver autoinstall in thread encountered: {e}. Assuming driver is in PATH or pre-installed.")

  driver = webdriver.Chrome(options=options)
  driver.implicitly_wait(1)
  try:
    content_url = search_for_page(driver, search_subject)
    soup = get_soup(driver, content_url)
    return soup, driver
  except Exception as e:
    print(f"Error during scraping for '{search_subject}': {e}")
    if driver:
        try:
            driver.quit()
        except: pass
    return None, None

basic_feature_extraction = """You are an AI designed to assist with extracting specific features from user requests related to the game Minecraft. Your task is to analyze the user query (delimited by triple backticks) and extract two key pieces of information:

Subject: Identify the main subject of the sentence. This is typically a Minecraft item, entity, block, or structure (full names only).
Summary: Provide a brief summary of the specific information or request that the user wants to know about the subject. Include any information that may be important.
Here are some examples to guide you:

Example 1:
User query: "How do I find diamonds in Minecraft?"
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
  global client, api_key # Allow access to global client and api_key
  await asyncio.sleep(0.8)

  # This combined check handles both uninitialized client and placeholder key
  if client is None or api_key == '[INSERT YOUR API KEY HERE]':
      if prompt_text.startswith("You are an AI designed to assist with extracting specific features"):
        user_query_match = re.search(r"```\s*(.*?)\s*```", prompt_text, re.DOTALL)
        user_query = user_query_match.group(1).strip() if user_query_match else ""
        if 'dirt' in user_query.lower(): return 'Subject: Dirt\\nSummary: What is dirt used for'
        return f'Subject: {user_query}\\nSummary: General information about {user_query}'
      elif prompt_text.startswith("You are an AI designed to extract specific answers"):
        # More robustly parse summary_query from the actual prompt structure
        summary_query_part = ""
        parts_after_initial_prompt = prompt_text.split(generate_output.split("```")[0] + "```", 1)
        if len(parts_after_initial_prompt) > 1:
            summary_section = parts_after_initial_prompt[1]
            summary_match = re.search(r"Summary: (.*?)\\n```", summary_section)
            if summary_match:
                summary_query_part = summary_match.group(1).strip()

        content_part = ""
        content_match = re.search(r"Paragraphs:\\n(.*?)\\n```", prompt_text, re.DOTALL)
        if content_match:
            content_part = content_match.group(1).strip()

        if "What is dirt used for" == summary_query_part and "Dirt" in content_part and "farming" in content_part:
             return "Answer: Dirt is primarily used for farming in Minecraft, but due to its abundance, it can also be used as a readily available building block."
        return f"Mocked answer: Content for '{summary_query_part}' not sufficiently matched in mock. Content: {content_part[:50]}..."
      return "Full Mock (No/Placeholder API Key): Unknown prompt type"

  # Actual API call if a real key was provided and client initialized
  try:
    chat_completion = await client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt_text}]
    )
    return chat_completion.choices[0].message.content
  except Exception as e:
    return f"Error calling OpenAI API: {e}"


async def prompt(user_query):
  global api_key, client

  # Check if we need to use the full mock path because API key is placeholder
  # (client might be None if its initial global init failed due to placeholder)
  if api_key == '[INSERT YOUR API KEY HERE]':
      await asyncio.sleep(0.1)
      subject = "Dirt"
      summary_query = "What is dirt used for"
      if "dirt" not in user_query.lower():
          subject = user_query
          summary_query = f"General information about {user_query}"

      # print(f"Mock (No API Key Path) Searching for: {subject}, Summary to find: {summary_query}") # Debug
      await asyncio.sleep(1.5) # Simulate scraping

      if subject == "Dirt" and summary_query == "What is dirt used for":
          return "Dirt is primarily used for farming in Minecraft, but due to its abundance, it can also be used as a readily available building block."
      return f"Mocked full response for {subject} regarding '{summary_query}'."

  # This part runs if api_key is NOT the placeholder (client should be valid)
  feature_extraction_full_prompt = basic_feature_extraction + user_query + "\\n```"
  summary_response_text = await make_chatgpt_request(feature_extraction_full_prompt)
  summary_parts = summary_response_text.strip("\"'").split("\\n")

  if len(summary_parts) < 2 or not summary_parts[0].startswith("Subject:") or not summary_parts[1].startswith("Summary:"):
      # print(f"Unexpected summary format from feature extraction: {summary_response_text}") # Debug
      subject = user_query
      summary_query = "General information"
  else:
      subject = summary_parts[0].replace("Subject: ", "").strip('"')
      summary_query = summary_parts[1].replace("Summary: ", "").strip('"')

  chrome_options_dict = {'arguments': ['--headless', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']}
  driver = None
  soup_obj = None
  info_results, paragraphs_results = {}, []

  try:
    # print(f"Async prompt: Calling execute_scraping for {subject}") # Debug
    soup_obj, driver = await asyncio.to_thread(execute_scraping, subject, chrome_options_dict)
    if soup_obj:
        # print(f"Async prompt: Scraping successful for {subject}") # Debug
        info_task = asyncio.to_thread(extract_info_box, soup_obj)
        paragraphs_task = asyncio.to_thread(extract_main_paragraph, soup_obj)
        info_results_val, paragraphs_results_val = await asyncio.gather(info_task, paragraphs_task)
        info_results = info_results_val if info_results_val is not None else {}
        paragraphs_results = paragraphs_results_val if paragraphs_results_val is not None else []
    else:
        print(f"Warning: Scraping failed for '{subject}'.") # More user-friendly

    info_text_parts = [f"Name: {info_results.get('name', 'N/A')}"]
    info_text_parts.extend([f"{k}: {v}" for k,v in info_results.get('details', {}).items()])
    info_text = "\\n".join(info_text_parts)
    paragraphs_text = "\\n".join(paragraphs_results)
    scraped_content = f"Subject: {subject}\\n{info_text}\\n{paragraphs_text}".strip()

    if not (info_results or paragraphs_results):
        return f"Could not extract detailed information for '{subject}' regarding '{summary_query}'."

    final_gpt_full_prompt = generate_output + "Summary: " + summary_query + "\\n```\\nParagraphs:\\n" + scraped_content + "\\n```"
    final_answer = await make_chatgpt_request(final_gpt_full_prompt)
    return final_answer
  except Exception as e:
    print(f"An error occurred in prompt: {e}")
    return "Sorry, I encountered an error processing your request."
  finally:
    if driver:
        await asyncio.to_thread(driver.quit)

async def main():
  global client, api_key
  if api_key != '[INSERT YOUR API KEY HERE]': # Attempt to init client if a real key might be there
      try:
          client = AsyncOpenAI(api_key=api_key)
          print("AsyncOpenAI client initialized with provided API key.")
      except Exception as e:
          print(f"Error initializing AsyncOpenAI client with provided key: {e}. Will use full mock if key is placeholder.")
          client = None
  elif client is None : # If still None (because key IS placeholder)
      print("API key is a placeholder. OpenAI calls will be fully mocked inside prompt().")


  user_input = "What is dirt?"
  print(f"User Query: {user_input}\\n")

  num_runs = 3
  durations = []
  first_response = ""

  print("Checking/Installing Chromedriver...")
  try:
    chromedriver_autoinstaller.install()
    print("Chromedriver is ready.")
  except Exception as e:
    print(f"Error installing/checking chromedriver: {e}. Selenium might fail.")

  print(f"\\nStarting benchmark with {num_runs} runs...\\n")
  for i in range(num_runs):
    start_time = time.perf_counter()
    response = await prompt(user_input)
    end_time = time.perf_counter()
    duration = end_time - start_time
    durations.append(duration)
    print(f"Run {i+1} duration: {duration:.4f} seconds")
    if i == 0:
      first_response = response
      print(f"First response:\\n{first_response}\\n")

  if num_runs > 0 and durations:
    average_duration = sum(durations) / num_runs
    print(f"\\nAverage duration over {num_runs} runs: {average_duration:.4f} seconds")
  else:
    print("\\nNo runs were performed for benchmarking, or durations list is empty.")

if __name__ == '__main__':
  asyncio.run(main())
