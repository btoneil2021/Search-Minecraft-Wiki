from bs4 import BeautifulSoup

# The modified extract_main_paragraph function
def extract_main_paragraph(soup):
  main_paragraph_container = soup.find("div", {"class": "mw-body-content mw-content-ltr"})
  if not main_paragraph_container:
    return []

  main_paragraph_elements = main_paragraph_container.find_all(["p", "h2", "h3"])

  tables = soup.find_all("table")
  paragraphs_in_tables = []
  for table in tables:
    paragraphs_in_tables.extend(table.find_all("p"))

  paragraphs_in_tables_set = set(paragraphs_in_tables)

  # Clearer logic for filtering, ensuring h2/h3 are always included
  filtered = [el for el in main_paragraph_elements if el.name in ['h2', 'h3'] or (el.name == 'p' and el not in paragraphs_in_tables_set)]
  main_paragraph = [el.text.strip() for el in filtered]
  return main_paragraph

# Test cases
def run_tests():
    # Test 1: Basic case - paragraphs, h2, h3, and table
    html_doc1 = """
    <html><body>
      <div class="mw-body-content mw-content-ltr">
        <p>This is the first paragraph.</p>
        <h2>Section 1</h2>
        <p>This is a paragraph under section 1.</p>
        <table><tr><td><p>This paragraph is inside a table and should be excluded.</p></td></tr></table>
        <h3>Subsection 1.1</h3>
        <p>Another paragraph.</p>
        <div><p>Nested p outside table, should be included.</p></div>
      </div>
    </body></html>
    """
    soup1 = BeautifulSoup(html_doc1, 'html.parser')
    result1 = extract_main_paragraph(soup1)
    expected1 = ["This is the first paragraph.", "Section 1", "This is a paragraph under section 1.", "Subsection 1.1", "Another paragraph.", "Nested p outside table, should be included."]
    assert result1 == expected1, f"Test 1 Failed: Expected {expected1}, got {result1}"
    print("Test 1 Passed")

    # Test 2: No main content div
    html_doc2 = "<html><body><p>No main content div here.</p></body></html>"
    soup2 = BeautifulSoup(html_doc2, 'html.parser')
    result2 = extract_main_paragraph(soup2)
    expected2 = []
    assert result2 == expected2, f"Test 2 Failed: Expected {expected2}, got {result2}"
    print("Test 2 Passed")

    # Test 3: Empty soup / no relevant tags
    html_doc3 = "<html><body><div class='mw-body-content mw-content-ltr'></div></body></html>"
    soup3 = BeautifulSoup(html_doc3, 'html.parser')
    result3 = extract_main_paragraph(soup3)
    expected3 = []
    assert result3 == expected3, f"Test 3 Failed: Expected {expected3}, got {result3}"
    print("Test 3 Passed")

    # Test 4: Paragraphs only, no tables or headers
    html_doc4 = """
    <html><body>
      <div class="mw-body-content mw-content-ltr">
        <p>Para 1</p>
        <p>Para 2</p>
      </div>
    </body></html>
    """
    soup4 = BeautifulSoup(html_doc4, 'html.parser')
    result4 = extract_main_paragraph(soup4)
    expected4 = ["Para 1", "Para 2"]
    assert result4 == expected4, f"Test 4 Failed: Expected {expected4}, got {result4}"
    print("Test 4 Passed")

    # Test 5: Headers only
    html_doc5 = """
    <html><body>
      <div class="mw-body-content mw-content-ltr">
        <h2>Header 2</h2>
        <h3>Header 3</h3>
      </div>
    </body></html>
    """
    soup5 = BeautifulSoup(html_doc5, 'html.parser')
    result5 = extract_main_paragraph(soup5)
    expected5 = ["Header 2", "Header 3"]
    assert result5 == expected5, f"Test 5 Failed: Expected {expected5}, got {result5}"
    print("Test 5 Passed")

    # Test 6: Table with no paragraphs inside
    html_doc6 = """
    <html><body>
      <div class="mw-body-content mw-content-ltr">
        <p>Outer paragraph.</p>
        <table><tr><td>Just some text, not in a p tag.</td></tr></table>
        <p>Another outer paragraph.</p>
      </div>
    </body></html>
    """
    soup6 = BeautifulSoup(html_doc6, 'html.parser')
    result6 = extract_main_paragraph(soup6)
    expected6 = ["Outer paragraph.", "Another outer paragraph."]
    assert result6 == expected6, f"Test 6 Failed: Expected {expected6}, got {result6}"
    print("Test 6 Passed")

    # Test 7: H2 and H3 inside a div that is sibling to a table (should still be included)
    html_doc7 = """
    <html><body>
      <div class="mw-body-content mw-content-ltr">
        <p>Intro</p>
        <div>
            <h2>Important Heading</h2>
            <p>Content under heading</p>
        </div>
        <table><tr><td><p>Table P</p></td></tr></table>
        <h3>Less Important Heading</h3>
      </div>
    </body></html>
    """
    soup7 = BeautifulSoup(html_doc7, 'html.parser')
    result7 = extract_main_paragraph(soup7)
    expected7 = ["Intro", "Important Heading", "Content under heading", "Less Important Heading"]
    assert result7 == expected7, f"Test 7 Failed: Expected {expected7}, got {result7}"
    print("Test 7 Passed")

    print("All tests passed!")

if __name__ == "__main__":
    run_tests()
