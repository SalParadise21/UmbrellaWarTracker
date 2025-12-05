"""Screenshot processing and OCR for stat extraction"""
import io
import re
from typing import Dict, Optional

# Optional imports for OCR functionality
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: pytesseract or Pillow not installed. Screenshot processing will be disabled.")

# Configure tesseract path if needed (uncomment and set if tesseract is not in PATH)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_stats_from_image(image_bytes: bytes) -> Optional[Dict[str, int]]:
    """
    Extract Foxhole stats from a screenshot using OCR
    Returns a dictionary with stat values or None if extraction fails
    """
    if not OCR_AVAILABLE:
        return None
    
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        # Parse the text for stats
        stats = {}
        
        # Common patterns for Foxhole stats
        patterns = {
            'enemy_player_damage': r'enemy\s*player\s*damage\s*:?\s*(\d+)',
            'friendly_player_damage': r'friendly\s*player\s*damage\s*:?\s*(\d+)',
            'enemy_structure_vehicle_damage': r'enemy\s*(?:structure|vehicle)\s*damage\s*:?\s*(\d+)',
            'friendly_structure_vehicle_damage': r'friendly\s*(?:structure|vehicle)\s*damage\s*:?\s*(\d+)',
            'friendly_construction': r'friendly\s*construction\s*:?\s*(\d+)',
            'friendly_repairing': r'friendly\s*repairing\s*:?\s*(\d+)',
            'friendly_healing': r'friendly\s*healing\s*:?\s*(\d+)',
            'friendly_revivals': r'friendly\s*revivals?\s*:?\s*(\d+)',
            'vehicles_captured_by_enemy': r'vehicles?\s*captured\s*by\s*enemy\s*:?\s*(\d+)',
            'vehicle_self_damage_neutral': r'vehicle\s*self\s*damage\s*\(?\s*neutral\s*\)?\s*:?\s*(\d+)',
            'vehicle_self_damage_colonial': r'vehicle\s*self\s*damage\s*\(?\s*colonial\s*\)?\s*:?\s*(\d+)',
            'vehicle_self_damage_warden': r'vehicle\s*self\s*damage\s*\(?\s*warden\s*\)?\s*:?\s*(\d+)',
            'materials_submitted': r'materials?\s*submitted\s*:?\s*(\d+)',
            'materials_gathered': r'materials?\s*gathered\s*:?\s*(\d+)',
            'supply_value_delivered': r'supply\s*value\s*delivered\s*:?\s*(\d+)',
        }
        
        # Try to find each stat
        for stat_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    stats[stat_name] = int(match.group(1))
                except (ValueError, IndexError):
                    pass
        
        return stats if stats else None
        
    except Exception as e:
        print(f"Error processing screenshot: {e}")
        return None


def validate_stats(stats: Dict[str, int]) -> bool:
    """Validate that stats are reasonable"""
    # Check for negative values
    if any(v < 0 for v in stats.values()):
        return False
    
    # Check for unreasonably large values (adjust as needed)
    max_value = 1000000
    if any(v > max_value for v in stats.values()):
        return False
    
    return True

