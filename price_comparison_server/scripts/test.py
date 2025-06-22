import os
import json
import re
from collections import defaultdict
from typing import Dict, List, Set

def analyze_store_ids_in_files(parsing_folder: str) -> Dict:
    """
    Analyze store IDs in parsing files to understand formatting patterns
    """
    analysis = {
        'by_chain': defaultdict(lambda: {
            'store_ids': set(),
            'formats': defaultdict(int),
            'lengths': defaultdict(int),
            'samples': []
        })
    }
    
    # Walk through parsing folder
    for root, dirs, files in os.walk(parsing_folder):
        for file in files:
            if file.endswith(('.json', '.csv', '.xml')):  # Adjust extensions as needed
                filepath = os.path.join(root, file)
                
                # Try to identify chain from path or filename
                chain_name = identify_chain(filepath)
                if not chain_name:
                    continue
                
                # Extract store IDs from file
                store_ids = extract_store_ids(filepath)
                
                for store_id in store_ids:
                    analysis['by_chain'][chain_name]['store_ids'].add(store_id)
                    
                    # Analyze format
                    if re.match(r'^0+\d+$', store_id):
                        analysis['by_chain'][chain_name]['formats']['leading_zeros'] += 1
                    elif re.match(r'^\d+$', store_id):
                        analysis['by_chain'][chain_name]['formats']['numeric_no_zeros'] += 1
                    else:
                        analysis['by_chain'][chain_name]['formats']['other'] += 1
                    
                    # Track lengths
                    analysis['by_chain'][chain_name]['lengths'][len(store_id)] += 1
                    
                    # Keep samples
                    if len(analysis['by_chain'][chain_name]['samples']) < 10:
                        analysis['by_chain'][chain_name]['samples'].append(store_id)
    
    return analysis

def identify_chain(filepath: str) -> str:
    """
    Identify chain name from file path or name
    """
    # Common patterns - adjust based on your folder structure
    patterns = {
        'shufersal': ['shufersal', 'shuf'],
        'victory': ['victory', 'vict'],
        # Add more chains as needed
    }
    
    filepath_lower = filepath.lower()
    for chain, keywords in patterns.items():
        if any(keyword in filepath_lower for keyword in keywords):
            return chain
    
    return None

def extract_store_ids(filepath: str) -> Set[str]:
    """
    Extract store IDs from a file - implement based on your file formats
    """
    store_ids = set()
    
    try:
        if filepath.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Adjust based on your JSON structure
                # Example: look for 'store_id', 'branch_id', 'location_id' fields
                store_ids = extract_from_json(data)
        
        elif filepath.endswith('.csv'):
            import csv
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Adjust column names based on your CSV structure
                    if 'store_id' in row:
                        store_ids.add(row['store_id'])
        
        # Add more formats as needed
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    
    return store_ids

def extract_from_json(data, store_ids=None) -> Set[str]:
    """
    Recursively extract store IDs from JSON data
    """
    if store_ids is None:
        store_ids = set()
    
    if isinstance(data, dict):
        # Common field names for store IDs
        id_fields = ['store_id', 'branch_id', 'location_id', 'store_code']
        for field in id_fields:
            if field in data and data[field]:
                store_ids.add(str(data[field]))
        
        # Recurse into nested structures
        for value in data.values():
            extract_from_json(value, store_ids)
    
    elif isinstance(data, list):
        for item in data:
            extract_from_json(item, store_ids)
    
    return store_ids

def print_analysis(analysis: Dict):
    """
    Print analysis results in a readable format
    """
    print("Store ID Analysis Results")
    print("=" * 50)
    
    for chain, data in analysis['by_chain'].items():
        print(f"\nChain: {chain}")
        print(f"  Total unique store IDs: {len(data['store_ids'])}")
        
        print(f"  Formats found:")
        for format_type, count in data['formats'].items():
            print(f"    - {format_type}: {count}")
        
        print(f"  ID lengths:")
        for length, count in sorted(data['lengths'].items()):
            print(f"    - Length {length}: {count} occurrences")
        
        print(f"  Sample IDs: {', '.join(data['samples'][:5])}")
        
        # Check for potential issues
        if len(data['lengths']) > 1:
            print(f"  ⚠️  WARNING: Multiple ID lengths found!")
        
        if data['formats'].get('leading_zeros', 0) > 0 and data['formats'].get('numeric_no_zeros', 0) > 0:
            print(f"  ⚠️  WARNING: Mixed formats (with and without leading zeros)!")

def check_database_consistency(db_connection, analysis: Dict):
    """
    Compare parsed data with database to find inconsistencies
    """
    cursor = db_connection.cursor()
    
    for chain, data in analysis['by_chain'].items():
        # Get store IDs from database
        cursor.execute("""
            SELECT DISTINCT b.store_id 
            FROM branches b 
            JOIN chains c ON b.chain_id = c.chain_id 
            WHERE c.name = %s
        """, (chain,))
        
        db_store_ids = {row[0] for row in cursor.fetchall()}
        parsed_store_ids = data['store_ids']
        
        # Find mismatches
        only_in_parsed = parsed_store_ids - db_store_ids
        only_in_db = db_store_ids - parsed_store_ids
        
        if only_in_parsed or only_in_db:
            print(f"\nInconsistencies for {chain}:")
            if only_in_parsed:
                print(f"  In parsed files but not in DB: {list(only_in_parsed)[:5]}")
            if only_in_db:
                print(f"  In DB but not in parsed files: {list(only_in_db)[:5]}")

# Usage example
if __name__ == "__main__":
    # Run analysis
    parsing_folder = "./parsing"  # Adjust to your folder path
    analysis = analyze_store_ids_in_files(parsing_folder)
    print_analysis(analysis)
    
    # If you have DB connection, also check consistency
    # db_conn = create_db_connection()  # Your DB connection
    # check_database_consistency(db_conn, analysis)