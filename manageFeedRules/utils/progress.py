from tqdm import tqdm
from typing import Optional


class ProgressTracker:
    """Abstracted progress reporting using tqdm"""
    
    def __init__(self):
        self.pbar: Optional[tqdm] = None
    
    def start(self, total_items: int, description: str = "Processing"):
        """Initialize progress bar"""
        self.pbar = tqdm(
            total=total_items,
            desc=description,
            unit="item",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
        )
    
    def update(self, increment: int = 1, message: str = None):
        """Update progress bar"""
        if self.pbar:
            if message:
                self.pbar.set_postfix_str(message)
            self.pbar.update(increment)
    
    def set_description(self, description: str):
        """Update the description"""
        if self.pbar:
            self.pbar.set_description(description)
    
    def finish(self, message: str = "Complete"):
        """Close progress bar"""
        if self.pbar:
            self.pbar.set_postfix_str(message)
            self.pbar.close()
            self.pbar = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pbar:
            self.pbar.close()