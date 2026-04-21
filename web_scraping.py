#!/opt/homebrew/bin/python3.12

import json
from ddgr_scraping import Search_Engine_Query
import pdfplumber
import sys
import os
import db
import requests
from bs4 import BeautifulSoup
from sys import stderr

import json
import re
from datetime import datetime,timezone # To convert timestamp to human readable date and time

DEBUG=1 # 0 = no debug info
timeout_seconds=30 # Timeout for get response

##############################
# Clean old files
##############################
def Clean_old_files(MetaFile,HitsFile,OutFile):
    RemoveFiles=[MetaFile,HitsFile,OutFile]
    for File in RemoveFiles:
        if os.path.exists(File):
            print(f"Removing: {File}")
            os.remove(File)

##########################
# Process a PDF file
##########################
def PDF_process (url):
    local_file="downloaded_file.pdf"

    contents=[]
    try:
        response=requests.get(url,stream=True)
        response.raise_for_status()

        with open (local_file,'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        f.close()

        print(f"File {local_file} downloaded successfully")

        with pdfplumber.open(local_file) as pdf:
            for page in pdf.pages:
                text=page.extract_text()
                contents.append(text)
                
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e} ")
    return contents

##########################
# Web_Scraping
# The web scraping code
##########################
def Web_Scraping(ERAG,OutFile,HitsFile,Query,Search_Engine,Existing_urls,Excluded_sites):
    print (f"Output file: {OutFile}")
    print (f"Hits file: {HitsFile}")
    print (f"Meta indormation file: {MetaFile}")

    if ERAG == 1:
        f=open(OutFile, 'a')
    else:
        f=open(OutFile, 'w')
    options = Options()

    driver_search = webdriver.Chrome(options=options)

    driver_search.get(Query)
    print("Page title:", driver_search.title)

    link_elements = driver_search.find_elements(By.XPATH,"//a[@href]")
    links=[element.get_attribute('href') for element in link_elements]
    urls=list(set(links))
    for del_url in Excluded_sites:
        links = [item for item in urls if del_url not in item and item.count('/') > 3 ]

    print (f'Links: {links}')
    for url in links:
        root,extension = os.path.splitext(url)
        if extension.lower() == 'pdf':
            print(f"This url is a PDF file: {url}")
            try:
                p=PDF_process(url)
                print(p)
                for elem in p:
                    f.write(elem)
            except:
                print("There was an error processing this PDF file. Continuing.")
                pass
            continue
        try:                    
            driver_url = webdriver.Chrome(options=options)
            driver_url.set_page_load_timeout(15)
            driver_url.get(url)

            body_elements = driver_url.find_elements(By.TAG_NAME, 'p')
    
            for p in body_elements:
                print(p.text)
                f.write(p.text)
            driver_url.quit()

        except:
            driver_url.quit()
            pass

        driver_search.quit()
    f.close()

    if ERAG == 1:
        Hits=open(HitsFile, 'a')
    else:
        Hits=open(HitsFile, 'w')
    for link in links:
        link=link+"\n"
        Hits.write(link)
    Hits.close()

    if ERAG == 1:
        SoT_Matching_Urls=[]
        SoT_Dict={}
        for link in links:
            for SoT in SoTs.split():
                if SoT in link:
                    SoT_Matching_Urls.append(link)
                    if (SoT in SoT_Dict):
                        SoT_Dict[SoT]+=1
                    else:
                        SoT_Dict[SoT]=1

    return links

#########################
# contents_scrap
#########################
def contents_scrap(url):

    options = webdriver.ChromeOptions()

    contents=[]
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        body_elements = driver.find_elements(By.TAG_NAME, 'p')

        for p in body_elements:
            if p.text != '': # Discard empty paragraphs
                contents.append(p.text)
    except Exception as e:
        print(f"Error fetching the contents, due to: {e}")
    
    finally:
        driver.quit()

    return contents

###########################
# Content_Scraping
# The content scraping code
###########################
def Content_Scraping(MetaFile,URLs):
    with open(MetaFile, 'w') as f:
        for url in URLs:
            author=""
            published_date=""
            contents=""
    
            # Get the base site URL
            site_idx=url.find("://")
            ###### PDF url processing
            root,extension = os.path.splitext(url)
            if extension.lower() == '.pdf':
                print(f"This url is a PDF file: {url}")
                try:
                    p=PDF_process(url)
                    contents='\n',join(p)
                    print(contents)
                except:
                    print("There was an error processing this PDF file. Continuing.")
                    pass
                print (f"Contents: {contents}\n")
                db.Write(url,site_url,author,published_date,contents)
                continue
    
            try:
                response = requests.get(url, timeout=timeout_seconds)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching the URL: {e}")
                continue
            except requests.exceptions.Timeout:
                print(f"Request timed out for {url} after {timeout_seconds} seconds.")
                continue
        
            soup = BeautifulSoup(response.content,'html.parser',from_encoding="iso-8859-1")

            if author=="":
                author_element = soup.find('span', class_='author-name') 
                if author_element:
                    author = author_element.text.strip()
                else:
                    pass
        
            try:
                data = json.loads(soup.select_one('[type="application/ld+json"]').contents[0])
                if (author == ""):
                    author=(data["author"][0])['name']
                if published_date == "":
                    published_date=(data["datePublished"])
            except:
                pass

            if author=="" or published_date=="":
                try:
                    (new_author,new_published_date)=selenium_scrap(ERAG,url)
                except:
                    new_author=new_published_date=""
                if author == "":
                    author=new_author
                if published_date == "":
                    published_date=new_published_date
                if author != "" and published_date != "":
                    contents=contents_scrap(url) # get textual contexts of the website
                    Entry="Site: "+site_url+"\nAuthor: "+author+"\nPublication date: "+published_date+"\n"
                    f.write(Entry)
                    continue
        
            try:
                response = requests.get(url)
                response.raise_for_status() 
            except requests.exceptions.RequestException as e:
                print(f"Error fetching the URL: {e}\n")
                pass

            soup = BeautifulSoup(response.text, 'html.parser')
            tags_and_contents = []
            for tag in soup.find_all(True): 
                tag_name = tag.name
                tag_content = tag.get_text(strip=True) 
            
                tags_and_contents.append({
                    'tag_name': tag_name,
                    'content': tag_content
                })

                data = tags_and_contents
            
                if data and (author=="" or published_date==""):
                    for item in data:
                        if author=="" and ("article_author" in item['content'] or "author" in item['content']):
                            try:
                                script_tag=(item['content']).split(',')
                                author_idx = [i for i, elem in enumerate(script_tag) if re.search('article_author', elem)]
                                if author_idx == []:
                                    author_idx = [i for i, elem in enumerate(script_tag) if re.search('author', elem)]
                                    author=script_tag[author_idx[0]].split(':')[3]
                                else:
                                    author=script_tag[author_idx[0]].split(':')[1]
                            
                                if author_idx == [] and author=="":
                                    author_idx = [i for i, elem in enumerate(script_tag) if re.search('creator', elem)]
                                    name=[i for i, elem in enumerate(script_tag[author_idx[0]]) if re.search('name', elem)]
                                    author=(script_tag[author_idx[0]].split(':'))[1]
                                author=author.replace('\\', '')
                                author=author.replace('"', '')
                            except:
                                pass

                        if (published_date == "") and ("publication_date" in item['content'] or "published_date" in item['content'] or "datePublished" in item['content']):
                            try:
                                publication_idx = [i for i, elem in enumerate(script_tag) if re.search('publication_date', elem)]
                                if publication_idx == []:
                                    publication_idx = [i for i, elem in enumerate(script_tag) if re.search('datePublished', elem)]
                                publication_date_list=(script_tag[publication_idx[0]].split(':'))[1:]
                                publication_date=":".join(publication_date_list)
                            except:
                                pass

            contents=contents_scrap(url)
            db.Write(url,site_url,author,published_date,contents)
            Entry="Site: "+site_url+"\nAuthor: "+author+"\nPublication date: "+published_date+"\n"
            f.write(Entry)   
    f.close()

###########################
# Main
###########################
if __name__ == "__main__":
    QUERY = os.getenv('Query', 'Why did the gold reach new highs in September 2025?')

    Query=QUERY.replace(' ','+')

    SEARCH_ENGINE="https://duckduckgo.com"
    SEARCH_CMD="?q="
    
    HITS=20 # Number of hits by default - this is overrided by a default of 10 even through serpapi

    SoTs="cnn.com news.com.au" # Example to pre-selected SoTs
    SoTs=SoTs.replace(' ','+')

    Excluded_sites=["wikipedia.org", "youtube.com", "facebook.com", "instagram.com", "duckduckgo.com","play.google.com","app.apple.com"]

    # Remove old files from the Data_[E]RAG directory
    db.Initialise_DB()
    # Using the ERAG environment variable - issuing an ERAG process
    ERAG = os.environ.get("ERAG",'1')
    if ERAG == '1':
        print ("Using Extended RAG (ERAG)")
        print (f"Environment ERAG={ERAG}")
        
        OutFile = os.getenv('OutFile', 'web_scraping_ERAG_output.txt')
        with open(OutFile,'w') as O:
            O.close()
        HitsFile = os.getenv('HitsFile', 'web_scraping_ERAG_hits.txt')
        with open(HitsFile,'w') as H:
            H.close()
        MetaFile = os.getenv('MetaFile', 'web_scraping_ERAG_meta.txt')

        Clean_old_files(MetaFile,HitsFile,OutFile)

        print (f"List of SoTs: {SoTs}")
        print (f"List of excluded sites: {Excluded_sites}")

        Permutations_File="query_permutations.txt"
        if db.Check_Path(Permutations_File):
            with open(Permutations_File,'r') as P:
                p_line = P.readline()
                p_line=p_line.strip()
                All_Links=[]
                Unique_urls=[]
                while p_line:
                    Query = p_line.strip()
                    QUERY=Query
                    Query = Query.replace(' ','+')
                    Web_Query=SEARCH_ENGINE+'/'+SEARCH_CMD+Query
                    if DEBUG == 1 : print(f"Search query: {Web_Query}")
                    links=Search_Engine_Query("www.google.com/search?q=",Query)
                    print(f"Recieving the following URLs: {links}")
                    All_Links=All_Links+links
                    Unique_urls=list(set(All_Links))
                    p_line = P.readline()
            P.close()
            Content_Scraping(MetaFile,Unique_urls)
    else:
        print ("Using regular RAG")
        OutFile = os.getenv('OutFile', 'web_scraping_RAG_output.txt')
        HitsFile = os.getenv('HitsFile', 'web_scraping_RAG_hits.txt')
        MetaFile = os.getenv('MetaFile', 'web_scraping_RAG_meta.txt')
        Clean_old_files(MetaFile,HitsFile,OutFile)
        
        Web_Query=SEARCH_ENGINE+'/'+SEARCH_CMD+Query
        QUERY = os.getenv('Query', 'Why did the gold reach new highs in September 2025?')
        links=Search_Engine_Query("www.google.com/search?q=",Query) # Using DDGR shell tool from DuckDuckGo.com
        if DEBUG == 1: print (f'=======================\nReturned links: {links}\n=========================')
        Content_Scraping(MetaFile,links)