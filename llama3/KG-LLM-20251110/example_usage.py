"""Example usage of EPERM system."""

from eperm_system import EPERMSystem


def main():
    """Run example EPERM queries."""
    
    # Initialize system
    print("Initializing EPERM system...")
    system = EPERMSystem()
    
    # Load knowledge graph
    print("Loading knowledge graph...")
    system.load_knowledge_graph("data/sample_kg.json")
    
    # Interactive Q&A
    print("\n" + "="*70)
    print("EPERM Interactive Question Answering")
    print("="*70)
    print("\nExample questions:")
    print("  - Who founded Microsoft?")
    print("  - Where is Apple headquartered?")
    print("  - What products did Microsoft develop?")
    print("  - Who attended Harvard University?")
    print("\nType 'quit' to exit\n")
    
    while True:
        question = input("Question: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if not question:
            continue
        
        try:
            answer = system.answer_question(question)
            
            print(f"\n{'='*70}")
            print(f"Answer: {answer.answer}")
            print(f"Confidence: {answer.confidence:.2f}")
            
            if answer.supporting_paths:
                print(f"\nTop evidence paths:")
                for i, path in enumerate(answer.supporting_paths[:3], 1):
                    print(f"  {i}. [Score: {path.score:.2f}] {path.to_text(system.kg)}")
            
            print(f"\nReasoning: {answer.reasoning}")
            print(f"{'='*70}\n")
            
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
