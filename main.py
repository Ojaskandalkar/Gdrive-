import os
import json
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

import sheets_helper

# Load environment variables
load_dotenv()

# Setup logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_agent_response(user_input, sheet_data):
    """
    Sends the user input and current sheet data to Gemini.
    Forces Gemini to return a STRICT JSON object representing the action to take.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY not found in .env")
        return None

    client = genai.Client(api_key=api_key)
    
    # System prompt giving Gemini context, data, and strict JSON schemas
    prompt = f"""
    You are an AI Agent translating natural language requests into JSON actions for a Google Sheet.
    
    Current Sheet Data:
    {json.dumps(sheet_data)}
    
    User Request: "{user_input}"
    
    Return a STRICT JSON object representing the action to perform based on the User Request.
    Ensure output is pure JSON. No markdown blocks, no code fences.
    
    Allowed Actions and JSON Formats:
    1. Show records: {{"action": "show_records"}}
    2. Find record: {{"action": "find_record", "field": "<Column Name>", "value": "<Search Value>"}}
    3. Add record: {{"action": "add_record", "record": {{"ID": "...", "Name": "...", "Status": "...", "Date": "...", "Remarks": "..."}}}}
    4. Update record: {{"action": "update_record", "filter": {{"<Column Name>": "<Value>"}}, "updates": {{"<Column Name>": "<New Value>"}}}}
    5. Summarize records: {{"action": "summarize_records"}}
    """
    
    try:
        # Enforce JSON output using response_mime_type configuration
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        # Parse and return the JSON
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from Gemini response: {e}")
        return None
    except Exception as e:
        logging.error(f"Error communicating with Gemini SDK: {e}")
        return None

def execute_action(action_json):
    """
    Takes the structured JSON action from Gemini and executes the corresponding
    function in sheets_helper.py.
    """
    if not action_json:
        print("No valid action was determined from your request.")
        return

    action = action_json.get("action")
    
    if action == "show_records":
        records = sheets_helper.read_all_records()
        print("\n--- All Records ---")
        for r in records:
            print(r)
            
    elif action == "find_record":
        field = action_json.get("field")
        value = action_json.get("value")
        results = sheets_helper.find_record(field, value)
        print(f"\n--- Search Results for {field} = {value} ---")
        for r in results:
            print(r)
            
    elif action == "add_record":
        record = action_json.get("record")
        success = sheets_helper.add_record(record)
        if success:
            print("\nRecord added successfully!")
        else:
            print("\nFailed to add record. Check logs.")
            
    elif action == "update_record":
        filter_dict = action_json.get("filter")
        updates_dict = action_json.get("updates")
        success = sheets_helper.update_record(filter_dict, updates_dict)
        if success:
            print("\nRecord updated successfully!")
        else:
            print("\nFailed to update record. Record may not exist.")
            
    elif action == "summarize_records":
        summary = sheets_helper.summarize_records()
        print("\n--- Summary ---")
        print(summary)
        
    else:
        print(f"\nUnknown action requested by AI: {action}")

def main():
    print("========================================")
    print(" Welcome to the Sheets AI Agent!")
    print(" Type 'exit' or 'quit' to close.")
    print("========================================")
    
    while True:
        try:
            user_input = input("\nEnter your request: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            # Step 1: Read latest context from Google Sheets
            sheet_data = sheets_helper.read_all_records()
            
            # Step 2: Ask Gemini what to do based on the context and user prompt
            action_json = get_agent_response(user_input, sheet_data)
            
            if action_json:
                print(f"\n[AI Action Decision]: {json.dumps(action_json)}")
                
            # Step 3: Execute the decided action in Python
            execute_action(action_json)
            
        except Exception as e:
            logging.error(f"An unexpected error occurred during execution: {e}")

if __name__ == "__main__":
    main()