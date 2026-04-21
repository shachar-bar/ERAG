#!/opt/homebrew/bin/python3.12
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util
import torch
import os
import re
import sys
import db

Data_Dir="Data" # The location of the data files
Knowledge_File = "knowledge_base.txt" # The knowledge file, containing all the web scraping contents

def simple_rag_from_file(file_path, query):
    """
    Implements a basic RAG system using a local text file.

    Args:
        file_path (str): The path to the text file containing the knowledge base.
        query (str): The user's question.

    Returns:
        str: The generated answer based on the retrieved context.
    """

    # Define the model's processing device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    # Define the model's save and cache directories
    save_dir = "/saved_models"
    cache_dir="/cache"
    
    # Ensure the following env. variables are set:
    os.environ['HF_HOME'] = cache_dir
    os.environ['HF_DATASETS_CACHE'] = cache_dir

    # 1. Load the knowledge base from the file
    with open(file_path, 'r', encoding='utf-8') as f:
        knowledge_base_text = f.read()
        print(f"Knowledge Base contents:\n{knowledge_base_text}")
    chunks = [chunk.strip() for chunk in re.split(r'(?<=[.!?]) +',knowledge_base_text) if chunk.strip()]

    model = SentenceTransformer('msmarco-bert-base-dot-v5',cache_folder=cache_dir,device=device) # The most efficient sentence embeddings model
    
    model.save(save_dir)
    chunk_embeddings = model.encode(chunks, convert_to_tensor=True)
    query_embedding = model.encode(query, convert_to_tensor=True)

    cosine_scores = util.cos_sim(query_embedding, chunk_embeddings)[0]
    top_chunk_index = torch.argmax(cosine_scores).item()
    retrieved_context = chunks[top_chunk_index]
    
    qa_pipeline = pipeline("question-answering", model="distilbert-base-cased-distilled-squad",save_pretrained=save_dir,device=device) 
     
    # Construct the prompt for the LLM
    # The retrieved context is provided to the LLM to guide its answer.
    result = qa_pipeline(question=query, context=retrieved_context)
    
    return result['answer']

if __name__ == "__main__":
    
    ERAG = os.environ.get("ERAG",'1')
    if ERAG == '1':
        Data_Dir=Data_Dir+'_ERAG'
    else:
        Data_Dir=Data_Dir+"_RAG"
    Contents=""
    with open(Knowledge_File, "w", encoding="utf-8") as f:
        for F in db.List(Data_Dir):
            (URL,SITE,AUTHOR,PUBLISHED,CONTENTS)=db.Parse_File(Data_Dir+'/'+F)
            Contents=''.join(CONTENTS[1:-1])
            Contents_lines=Contents.replace("'","")
            Contents_lines=Contents_lines.replace('"','')
            f.write(f"{Contents_lines}")
    f.close()

    user_query = os.getenv('Query', 'Why did the gold reach new highs in September 2025?')
    
    answer = simple_rag_from_file(Knowledge_File, user_query)
    print("===============================================================================")
    print(f"Query: {user_query}")
    print(f"Answer: {answer}")