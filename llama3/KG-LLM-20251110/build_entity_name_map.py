"""Build comprehensive entity name mapping from WebQSP dataset.

This script extracts all kb_id -> text mappings from the WebQSP dataset
(train_simple.json, dev_simple.json, test_simple.json) and creates a
comprehensive mapping file for use in knowledge graph text conversion.
"""

import json
from typing import Dict
from pathlib import Path


def extract_entity_mappings(json_file: str) -> Dict[str, str]:
    """
    Extract kb_id -> text mappings from a WebQSP JSON file.
    
    Args:
        json_file: Path to WebQSP JSONL file
        
    Returns:
        Dictionary mapping kb_id to text
    """
    mappings = {}
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    sample = json.loads(line.strip())
                    
                    # Extract from answers
                    for ans in sample.get('answers', []):
                        if ans and isinstance(ans, dict):
                            kb_id = ans.get('kb_id')
                            text = ans.get('text')
                            
                            if kb_id and text:
                                # Keep first occurrence or longer text if duplicate
                                if kb_id not in mappings or len(text) > len(mappings[kb_id]):
                                    mappings[kb_id] = text
                                    
                except json.JSONDecodeError as e:
                    print(f"Warning: Error parsing line {line_num} in {json_file}: {e}")
                    continue
                    
    except FileNotFoundError:
        print(f"Warning: File not found: {json_file}")
    except Exception as e:
        print(f"Error reading {json_file}: {e}")
    
    return mappings


def build_comprehensive_mapping(data_dir: str = "data/webqsp") -> Dict[str, str]:
    """
    Build comprehensive entity name mapping from all WebQSP files.
    
    Args:
        data_dir: Directory containing WebQSP files
        
    Returns:
        Complete dictionary mapping kb_id to text
    """
    print("Building comprehensive entity name mapping...")
    print("=" * 70)
    
    data_path = Path(data_dir)
    all_mappings = {}
    
    # Files to process
    files = [
        'train_simple.json',
        'dev_simple.json', 
        'test_simple.json'
    ]
    
    for filename in files:
        filepath = data_path / filename
        print(f"\nProcessing {filename}...")
        
        if not filepath.exists():
            print(f"  ⚠ File not found: {filepath}")
            continue
            
        mappings = extract_entity_mappings(str(filepath))
        
        # Merge mappings (keeping longer text if duplicate)
        for kb_id, text in mappings.items():
            if kb_id not in all_mappings or len(text) > len(all_mappings[kb_id]):
                all_mappings[kb_id] = text
        
        print(f"  ✓ Extracted {len(mappings)} unique mappings")
        print(f"  ✓ Total unique mappings so far: {len(all_mappings)}")
    
    print("\n" + "=" * 70)
    print(f"✓ Complete! Total unique kb_id -> text mappings: {len(all_mappings)}")
    
    return all_mappings


def save_mapping(mappings: Dict[str, str], output_file: str):
    """
    Save entity name mapping to JSON file.
    
    Args:
        mappings: Dictionary of kb_id -> text mappings
        output_file: Output JSON file path
    """
    print(f"\nSaving mappings to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Saved {len(mappings)} mappings to {output_file}")


def load_entity_name_map(mapping_file: str = "data/webqsp/entity_name_map.json") -> Dict[str, str]:
    """
    Load entity name mapping from JSON file.
    
    Args:
        mapping_file: Path to mapping JSON file
        
    Returns:
        Dictionary mapping kb_id to text
    """
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Mapping file not found: {mapping_file}")
        return {}
    except Exception as e:
        print(f"Error loading mapping file: {e}")
        return {}


def display_sample_mappings(mappings: Dict[str, str], num_samples: int = 20):
    """Display sample mappings for verification."""
    print(f"\nSample mappings (first {num_samples}):")
    print("-" * 70)
    
    for i, (kb_id, text) in enumerate(list(mappings.items())[:num_samples]):
        print(f"  {kb_id:15s} -> {text}")
    
    if len(mappings) > num_samples:
        print(f"  ... and {len(mappings) - num_samples} more")


def main():
    """Main function to build entity name mapping."""
    print("\n" + "=" * 70)
    print("WebQSP Entity Name Mapping Builder")
    print("=" * 70)
    
    # Build comprehensive mapping
    mappings = build_comprehensive_mapping("data/webqsp")
    
    if not mappings:
        print("\n⚠ No mappings found! Please check that WebQSP data files exist.")
        return
    
    # Save to file
    output_file = "data/webqsp/entity_name_map.json"
    save_mapping(mappings, output_file)
    
    # Display sample mappings
    display_sample_mappings(mappings, num_samples=20)
    
    # Statistics
    print("\n" + "=" * 70)
    print("Mapping Statistics:")
    print("-" * 70)
    print(f"  Total unique entities: {len(mappings)}")
    print(f"  Average text length: {sum(len(t) for t in mappings.values()) / len(mappings):.1f} characters")
    print(f"  Shortest text: {min(mappings.values(), key=len)}")
    print(f"  Longest text: {max(mappings.values(), key=len)}")
    print("=" * 70)
    
    print("\n✓ Entity name mapping file created successfully!")
    print(f"  Location: {output_file}")
    print("\nTo use in KnowledgeGraph:")
    print("  from build_entity_name_map import load_entity_name_map")
    print("  print(kg.to_text())")


if __name__ == "__main__":
    main()
