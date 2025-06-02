def validate_threshold(threshold: str) -> float:
    """Validate and convert threshold input"""
    try:
        value = float(threshold)
        if value < 0 or value > 100:
            raise ValueError("Threshold must be between 0 and 100")
        if value < 50:
            print("⚠️  Warning: Threshold below 50% is not recommended for safety")
            confirm = input("Are you sure you want to continue? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes']:
                raise ValueError("Operation cancelled by user")
        return value
    except ValueError as e:
        if "could not convert" in str(e):
            raise ValueError("Threshold must be a valid number")
        raise


def confirm_action(message: str, default: bool = False) -> bool:
    """Get user confirmation for actions"""
    suffix = " (Y/n): " if default else " (y/N): "
    response = input(message + suffix).strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def validate_output_prefix(prefix: str) -> str:
    """Validate output file prefix"""
    if not prefix:
        raise ValueError("Output prefix cannot be empty")
    
    # Remove invalid filename characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        prefix = prefix.replace(char, '_')
    
    return prefix