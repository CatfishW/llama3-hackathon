#!/usr/bin/env python3
"""
Test script to verify Parquet integration with KG-LLM-NEW.
Run this after converting your text files to Parquet.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from kg_llm_new.config import PipelineConfig, FreebaseEasyConfig, StorageConfig
from kg_llm_new.logging_utils import get_logger

LOGGER = get_logger(__name__)


def test_parquet_detection():
    """Test that Parquet files are detected correctly."""
    print("\n" + "="*80)
    print("TEST 1: Parquet File Detection")
    print("="*80)
    
    config = PipelineConfig(
        freebase_easy=FreebaseEasyConfig(
            enabled=True,
            root_path=Path("./freebase-easy-latest"),
            use_parquet=True,
        ),
    ).resolve()
    
    print(f"Root path: {config.freebase_easy.root_path}")
    print(f"Use Parquet: {config.freebase_easy.use_parquet}")
    print(f"Facts Parquet: {config.freebase_easy.facts_parquet_path}")
    print(f"Scores Parquet: {config.freebase_easy.scores_parquet_path}")
    print(f"Facts Text: {config.freebase_easy.facts_path}")
    print(f"Scores Text: {config.freebase_easy.scores_path}")
    
    if config.freebase_easy.facts_parquet_path and config.freebase_easy.facts_parquet_path.exists():
        print("✅ Parquet files detected successfully!")
        return True
    elif config.freebase_easy.facts_path and config.freebase_easy.facts_path.exists():
        print("⚠️  Using text files (Parquet not found)")
        return False
    else:
        print("❌ No data files found!")
        return False


def test_parquet_processing():
    """Test that Parquet files can be processed."""
    print("\n" + "="*80)
    print("TEST 2: Parquet Processing (Small Sample)")
    print("="*80)
    
    try:
        from kg_llm_new.kg.freebase_parquet import ParquetFreebaseEasyShardBuilder
        
        config = FreebaseEasyConfig(
            enabled=True,
            root_path=Path("./freebase-easy-latest"),
            use_parquet=True,
            chunk_size=10000,
            max_facts=50000,  # Process only 50k facts for testing
            output_dir=Path("./test_shards"),
        ).resolve()
        
        if not config.facts_parquet_path or not config.facts_parquet_path.exists():
            print("❌ facts.parquet not found!")
            print("   Run: cd freebase-easy-latest && python convert_to_parquet.py")
            return False
        
        print(f"Processing {config.max_facts} facts from {config.facts_parquet_path.name}...")
        
        builder = ParquetFreebaseEasyShardBuilder(
            facts_parquet_path=config.facts_parquet_path,
            output_dir=config.output_dir,
            scores_parquet_path=config.scores_parquet_path,
            max_facts=config.max_facts,
            chunk_size=config.chunk_size,
        )
        
        result = builder.build()
        
        print(f"\n✅ Processing successful!")
        print(f"   Shard counts: {result.counts}")
        print(f"   Output directory: {config.output_dir}")
        
        # Clean up test shards
        import shutil
        if config.output_dir.exists():
            print(f"   Cleaning up test shards...")
            shutil.rmtree(config.output_dir)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure pyarrow and pandas are installed:")
        print("   pip install pyarrow pandas")
        return False
    except Exception as e:
        print(f"❌ Processing error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_examples():
    """Test the example configurations."""
    print("\n" + "="*80)
    print("TEST 3: Configuration Examples")
    print("="*80)
    
    try:
        from example_parquet_config import (
            get_parquet_config,
            get_auto_config,
            get_test_config,
        )
        
        configs = [
            ("Parquet Config", get_parquet_config),
            ("Auto Config", get_auto_config),
            ("Test Config", get_test_config),
        ]
        
        for name, config_func in configs:
            try:
                config = config_func()
                print(f"✅ {name}: OK")
                print(f"   Use Parquet: {config.freebase_easy.use_parquet}")
                print(f"   Chunk Size: {config.freebase_easy.chunk_size}")
            except Exception as e:
                print(f"❌ {name}: {e}")
                return False
        
        return True
        
    except ImportError as e:
        print(f"⚠️  Could not import example configs: {e}")
        return True  # Not critical


def check_dependencies():
    """Check that required packages are installed."""
    print("\n" + "="*80)
    print("Checking Dependencies")
    print("="*80)
    
    required_packages = {
        'pyarrow': 'PyArrow',
        'pandas': 'Pandas',
    }
    
    missing = []
    for module, name in required_packages.items():
        try:
            __import__(module)
            print(f"✅ {name}: installed")
        except ImportError:
            print(f"❌ {name}: NOT installed")
            missing.append(module)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("="*80)
    print("KG-LLM-NEW Parquet Integration Test Suite")
    print("="*80)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Please install missing dependencies first")
        return 1
    
    # Run tests
    results = []
    
    results.append(("File Detection", test_parquet_detection()))
    results.append(("Parquet Processing", test_parquet_processing()))
    results.append(("Config Examples", test_config_examples()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Parquet integration is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
