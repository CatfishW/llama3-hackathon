"""Quick WebQSP test script - run single question with detailed output."""

from webqsp_loader import WebQSPLoader
from eperm_system import EPERMSystem


def quick_test():
    """Quick test with first WebQSP sample."""
    print("="*70)
    print("Quick WebQSP Test")
    print("="*70)
    
    # Load first sample
    loader = WebQSPLoader()
    qa_dataset = loader.create_qa_dataset(
        "data/webqsp/train_simple.json",
        num_samples=1,
        max_kg_size=200
    )
    
    qa = qa_dataset[0]
    
    print(f"\nQuestion: {qa['question']}")
    print(f"Gold Answer: {', '.join(qa['answers'])}")
    print(f"KG: {qa['kg_stats']['num_entities']} entities, {qa['kg_stats']['num_relations']} relations")
    
    # Run EPERM
    print("\nProcessing with EPERM...")
    system = EPERMSystem()
    system.kg = qa['kg']
    
    evidence = system.path_finder.find_evidence_paths(qa['question'], qa['kg'])
    answer = system.answer_predictor.predict(qa['question'], evidence, qa['kg'])
    
    print(f"\n{'='*70}")
    print(f"Answer: {answer.answer}")
    print(f"Confidence: {answer.confidence:.2f}")
    print(f"{'='*70}")


if __name__ == "__main__":
    quick_test()
