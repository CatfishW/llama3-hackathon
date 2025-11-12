# Real-Time Accuracy & Checkpointing Guide

## Overview

The updated `test_webqsp_eperm.py` now includes real-time accuracy tracking and checkpointing capabilities for long-running tests. This allows you to:

- **Track accuracy in real-time** as samples are processed
- **Save checkpoints** at regular intervals during testing
- **Resume from checkpoints** if the test is interrupted
- **Monitor progress** with visual indicators and time estimates

## New Classes

### 1. `CheckpointManager`

Manages checkpoint creation and loading for test resilience.

#### Key Methods:

- **`save_checkpoint(results, checkpoint_name=None, metadata=None)`**
  - Saves results to a checkpoint file
  - Automatically names checkpoints with timestamps if not provided
  - Returns path to saved checkpoint

- **`load_checkpoint(checkpoint_path)`**
  - Loads results from a checkpoint file
  - Returns tuple of (results, metadata)

- **`get_latest_checkpoint()`**
  - Returns path to most recent checkpoint
  - Useful for quick resumption

- **`list_checkpoints()`**
  - Lists all available checkpoints
  - Sorted by creation time (newest first)

#### Example:

```python
# Create checkpoint manager
manager = CheckpointManager()

# Save checkpoint
path = manager.save_checkpoint(
    results=current_results,
    checkpoint_name="checkpoint_500.json",
    metadata={'accuracy': 0.75}
)

# Load checkpoint
results, metadata = manager.load_checkpoint(path)

# Get latest checkpoint
latest = manager.get_latest_checkpoint()

# List all checkpoints
all_checkpoints = manager.list_checkpoints()
```

### 2. `RealTimeAccuracyTracker`

Tracks and displays real-time metrics during test execution.

#### Key Methods:

- **`add_result(result)`**
  - Add a result to the tracking list
  - Called after each sample is processed

- **`get_stats()`**
  - Returns current statistics dictionary including:
    - `total`: Total samples processed
    - `correct`: Number of correct predictions
    - `accuracy`: Current accuracy percentage
    - `avg_confidence`: Average confidence score
    - `avg_time`: Average time per sample
    - `elapsed_time`: Total elapsed time

- **`print_progress(sample_num, total_samples, current_result=None)`**
  - Displays formatted progress bar and statistics
  - Shows:
    - Progress percentage and visual bar
    - Current accuracy with running count
    - Average confidence and time metrics
    - Elapsed time and ETA
    - Current sample result

- **`checkpoint_results(checkpoint_interval=None)`**
  - Saves checkpoint if interval threshold is met
  - Automatically called by test function
  - Returns True if checkpoint was saved

- **`get_checkpoint_manager()`**
  - Returns the associated CheckpointManager instance

#### Example:

```python
# Create tracker
tracker = RealTimeAccuracyTracker()

# Add results as they come in
for i, qa_item in enumerate(qa_dataset):
    result = process_sample(qa_item)
    tracker.add_result(result)
    
    # Display progress every sample
    tracker.print_progress(i + 1, len(qa_dataset), result)
    
    # Save checkpoint every 100 samples
    tracker.checkpoint_results(checkpoint_interval=100)

# Get final stats
stats = tracker.get_stats()
print(f"Final Accuracy: {stats['accuracy']:.1f}%")
```

## Using Real-Time Accuracy & Checkpointing

### Basic Usage

Run tests with real-time accuracy tracking and checkpointing:

```python
from test_webqsp_eperm import test_eperm_with_webqsp

results, tracker = test_eperm_with_webqsp(
    num_samples=20000,
    max_kg_size=100,
    checkpoint_interval=100  # Save checkpoint every 100 samples
)
```

### Output Example

During execution, you'll see real-time progress like this:

```
[████████░░░░░░░░░░░░░░░░░░░░]  26.7% (5000/20000)
  Accuracy: 72.5% (3625/5000)
  Avg Confidence: 0.856
  Avg Time/Sample: 0.425s
  Elapsed: 00:35:42 | ETA: 01:20:18
  Current: ✓ Padme Amidala

[CHECKPOINT] Saved 5000 results to checkpoint_5000.json
```

### Resuming from Checkpoint

If your test is interrupted, resume from the last checkpoint:

```python
results, tracker = test_eperm_with_webqsp(
    num_samples=20000,
    max_kg_size=100,
    checkpoint_interval=100,
    resume_from_checkpoint='test_results/checkpoints/checkpoint_5000.json'
)
```

The test will:
1. Load previous results from checkpoint
2. Continue from where it left off
3. Save new checkpoints as it progresses

### Accessing Checkpoints

Get information about saved checkpoints:

```python
checkpoint_mgr = tracker.get_checkpoint_manager()

# Get latest checkpoint
latest = checkpoint_mgr.get_latest_checkpoint()

# List all checkpoints
all_checkpoints = checkpoint_mgr.list_checkpoints()

# Load a specific checkpoint
results, metadata = checkpoint_mgr.load_checkpoint(latest)
```

## Checkpoint Storage

Checkpoints are saved in: `test_results/checkpoints/`

Checkpoint files are named with the format:
```
checkpoint_<num_results>_<timestamp>.json
```

Example:
- `checkpoint_100_20251111_143022.json`
- `checkpoint_200_20251111_143045.json`
- `checkpoint_5000_20251111_150230.json`

Each checkpoint contains:
- `timestamp`: When the checkpoint was saved
- `num_results`: Number of results in checkpoint
- `results`: List of all test results
- `metadata`: Optional metadata (accuracy, sample count, etc.)

## Real-Time Accuracy Metrics

The tracker displays the following metrics in real-time:

### Progress Bar
```
[████████░░░░░░░░░░░░░░░░░░░░]  26.7% (5000/20000)
```
Visual representation of test completion percentage.

### Accuracy
```
Accuracy: 72.5% (3625/5000)
```
Current accuracy as percentage and absolute count.

### Confidence
```
Avg Confidence: 0.856
```
Average confidence score of all predictions so far.

### Time Per Sample
```
Avg Time/Sample: 0.425s
```
Average time required to process each sample.

### Time Estimates
```
Elapsed: 00:35:42 | ETA: 01:20:18
```
- Elapsed: Total time spent so far
- ETA: Estimated time to completion

### Current Result
```
Current: ✓ Padme Amidala
```
Result of the most recently processed sample (✓ = correct, ✗ = incorrect).

## Advanced Usage

### Custom Checkpoint Intervals

Save checkpoints at different frequencies based on your needs:

```python
# Checkpoint every 50 samples (more frequent, more I/O)
test_eperm_with_webqsp(num_samples=20000, checkpoint_interval=50)

# Checkpoint every 500 samples (less frequent, less I/O)
test_eperm_with_webqsp(num_samples=20000, checkpoint_interval=500)

# No checkpointing (set to None)
test_eperm_with_webqsp(num_samples=20000, checkpoint_interval=None)
```

### Analyzing Checkpoints

After a test run, you can analyze intermediate checkpoints:

```python
from test_webqsp_eperm import CheckpointManager, summarize_test_results

manager = CheckpointManager()
checkpoints = manager.list_checkpoints()

# Analyze each checkpoint
for checkpoint_name in checkpoints:
    path = f"test_results/checkpoints/{checkpoint_name}"
    results, metadata = manager.load_checkpoint(path)
    
    print(f"\n{checkpoint_name}:")
    print(f"  Samples: {len(results)}")
    accuracy = sum(1 for r in results if r['correct']) / len(results) * 100
    print(f"  Accuracy: {accuracy:.1f}%")
```

### Manual Checkpointing

You can also manually save checkpoints at any time:

```python
tracker = RealTimeAccuracyTracker()

# ... process some samples ...

# Manually save checkpoint
mgr = tracker.get_checkpoint_manager()
path = mgr.save_checkpoint(
    tracker.results,
    checkpoint_name="manual_checkpoint_1000.json",
    metadata={'note': 'Manually saved after 1000 samples'}
)
print(f"Saved to: {path}")
```

## Best Practices

### 1. **Choose Appropriate Checkpoint Intervals**
   - Start with every 100-200 samples
   - Adjust based on sample processing time
   - Balance between safety and I/O overhead

### 2. **Monitor Accuracy Trends**
   - Watch for sudden drops in accuracy (possible data issues)
   - Check if confidence decreases with accuracy
   - Use real-time metrics to spot problems early

### 3. **Resume Strategically**
   - Always resume from the latest checkpoint
   - Verify accuracy hasn't degraded before resuming
   - Keep important checkpoints for comparison

### 4. **Organize Checkpoints**
   - Periodically archive old checkpoints
   - Name important checkpoints descriptively
   - Document test parameters with each checkpoint

### 5. **Handle Interruptions**
   - Use keyboard interrupt (Ctrl+C) to gracefully stop
   - The script will print checkpoint information for resumption
   - Always resume to avoid losing progress

## Example Workflow

### Initial Test Run

```python
from test_webqsp_eperm import test_eperm_with_webqsp

# Start testing with checkpointing
results, tracker = test_eperm_with_webqsp(
    num_samples=20000,
    max_kg_size=100,
    checkpoint_interval=100
)
```

### If Interrupted (Ctrl+C)

```
Tests interrupted by user
Progress has been saved in checkpoints - you can resume later
```

### Resume Later

```python
# Get the latest checkpoint
latest = tracker.get_checkpoint_manager().get_latest_checkpoint()

# Resume from there
results, tracker = test_eperm_with_webqsp(
    num_samples=20000,
    max_kg_size=100,
    checkpoint_interval=100,
    resume_from_checkpoint=latest
)
```

### Analyze Results

```python
from test_webqsp_eperm import analyze_matching_results, summarize_test_results

# Quick analysis
analyze_matching_results(results, show_mismatches=True)

# Comprehensive summary
summary = summarize_test_results(results, output_file="test_results/final_summary.json")
```

## Troubleshooting

### Checkpoint Not Saving

**Problem**: Checkpoints aren't being created
- **Solution**: Ensure `checkpoint_interval` is set to a number, not None
- **Solution**: Verify `test_results/checkpoints/` directory exists (created automatically)

### Resume Shows Old Accuracy

**Problem**: Resumed test shows accuracy from checkpoint, not continuing
- **Solution**: This is normal - the test resumes from the checkpoint count
- **Solution**: Accuracy will update as new samples are added

### Out of Memory with Large Checkpoints

**Problem**: Memory usage grows significantly with many samples
- **Solution**: Save checkpoints more frequently (smaller files)
- **Solution**: Archive old checkpoints and start fresh periodically
- **Solution**: Reduce `num_samples` for smaller test runs

### Corrupted Checkpoint

**Problem**: Error loading checkpoint file
- **Solution**: Try the previous checkpoint from the list
- **Solution**: Restore from backup if available
- **Solution**: Start a fresh test run

## Performance Considerations

### Impact of Checkpointing

- **I/O overhead**: ~5-10ms per checkpoint save
- **Negligible with interval >= 100 samples**: Less than 1% overhead
- **Storage**: ~50-100KB per 1000 samples

### Optimizing Performance

1. **Adjust checkpoint interval**
   ```python
   # Balance between safety and speed
   checkpoint_interval=200  # Every 200 samples
   ```

2. **Use faster KG size**
   ```python
   # Smaller KG = faster processing
   test_eperm_with_webqsp(max_kg_size=50)
   ```

3. **Reduce sample verbosity** (optional)
   - Modify the code to print progress less frequently

## Summary

The new real-time accuracy and checkpointing system provides:

✓ **Real-time progress tracking** with visual indicators
✓ **Automatic checkpointing** at regular intervals
✓ **Resumable tests** from checkpoints
✓ **Detailed statistics** during execution
✓ **Graceful interruption** with progress saved

This makes it practical to run long tests (thousands or millions of samples) with confidence that progress is saved and can be resumed at any time.
