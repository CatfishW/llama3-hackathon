"""Explore WebQSP data format."""

import json
import pprint

# Read first few samples from train_simple.json
print("="*70)
print("Reading WebQSP Training Data")
print("="*70)

with open('data/webqsp/train_simple.json', 'r', encoding='utf-8') as f:
    lines = f.readlines()[:5]  # First 5 samples

print(f"\nTotal lines read: {len(lines)}\n")

for i, line in enumerate(lines, 1):
    data = json.loads(line)
    print(f"Sample {i}:")
    print(f"  Question: {data.get('question', 'N/A')}")
    print(f"  ID: {data.get('id', 'N/A')}")
    
    if 'answers' in data:
        print(f"  Answers: {data['answers'][:3]}")  # First 3 answers
    
    if 'entities' in data:
        print(f"  Entities: {data['entities'][:3]}")  # First 3 entities
    
    if 'subgraph' in data:
        subgraph = data['subgraph']
        if 'tuples' in subgraph:
            print(f"  Subgraph tuples: {len(subgraph['tuples'])} triples")
            print(f"    Sample triple: {subgraph['tuples'][0] if subgraph['tuples'] else 'None'}")
    
    print()

# Read entities
print("\n" + "="*70)
print("Entities Sample")
print("="*70)
with open('data/webqsp/entities.txt', 'r', encoding='utf-8') as f:
    entities = [line.strip() for line in f.readlines()[:10]]
print(f"First 10 entities: {entities}")

# Read relations
print("\n" + "="*70)
print("Relations Sample")
print("="*70)
with open('data/webqsp/relations.txt', 'r', encoding='utf-8') as f:
    relations = [line.strip() for line in f.readlines()[:10]]
print(f"First 10 relations: {relations}")
