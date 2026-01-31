def probability_to_color(probability, alpha=1.0):
    """
    Maps a probability value (0.0-1.0) to a color on a blue-red scale.
    Blue represents high probability (1.0)
    Red represents low probability (0.0)
    
    Args:
        probability (float): Probability value between 0.0 and 1.0
        alpha (float, optional): Alpha/opacity value between 0.0 and 1.0. Defaults to 1.0.
    
    Returns:
        str: RGBA color string (format: 'rgba(r, g, b, a)')
    """
    # Ensure probability is in valid range
    probability = max(0, min(1, probability))
    
    # Red component (high when probability is low)
    red = int(255 * (1 - probability))
    
    # Blue component (high when probability is high)
    blue = int(255 * probability)
    
    # Green component (kept at 0 for a cleaner red-blue gradient)
    green = 0
    
    # Return rgba string
    return f"rgba({red}, {green}, {blue}, {alpha})"
