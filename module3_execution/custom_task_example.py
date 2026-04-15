"""
Example of registering custom tasks with file attachments.
This can be called from your GUI when users define custom tasks.
"""

from tasks import register_custom_task, validate_file_attachments
from typing import Dict, Callable, List


def example_ml_training_task(payload: Dict, progress_cb: Callable) -> Dict:
    """Example ML training task that uses dataset files."""
    dataset_files = payload.get("dataset_files", [])
    model_type = payload.get("model_type", "linear")
    epochs = payload.get("epochs", 10)
    
    # Simulate training with file processing
    for epoch in range(1, epochs + 1):
        # Simulate processing files and training
        progress_cb(epoch / epochs)
    
    return {
        "model_type": model_type,
        "epochs_completed": epochs,
        "accuracy": 0.95,
        "dataset_count": len(dataset_files)
    }


def validate_ml_training(payload: Dict):
    """Validate ML training task payload."""
    if "dataset_files" in payload:
        validate_file_attachments(payload["dataset_files"])
    if "model_type" not in payload:
        raise ValueError("model_type is required")


def aggregate_ml_results(results: List[Dict]) -> Dict:
    """Aggregate ML training results."""
    avg_accuracy = sum(r.get("accuracy", 0) for r in results) / len(results) if results else 0
    return {
        "task": "ml_training",
        "average_accuracy": avg_accuracy,
        "total_models": len(results)
    }


# Register the custom task
register_custom_task(
    task_name="ml_training",
    executor=example_ml_training_task,
    aggregator=aggregate_ml_results,
    description="Train ML models with dataset files",
    validator=validate_ml_training
)
